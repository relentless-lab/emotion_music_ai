from pathlib import Path
from uuid import uuid4
from datetime import datetime

import asyncio
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, BackgroundTasks, Form
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.dependencies import get_current_user, get_db
from app.models.music_file import MusicFile
from app.models.user import User
from app.models.work import Work, WorkStatus, WorkVisibility
from app.schemas.music import EmotionAnalysisResult, MusicGenerateRequest, MusicGenerateResult
from app.schemas.tasks import TaskCreateResponse, TaskDetail, TaskStatus, TaskType
from app.schemas.work import WorkCreateRequest, WorkResponse
from app.services import generation_service, tasks
from app.services import image_service
from app.services import llm as llm_service
from app.services.oss_storage import (
    OSSStorage,
    build_oss_key,
    encode_oss_path,
    normalize_oss_like_url,
    resolve_storage_path_to_url,
)
from app.services.url_resolver import resolve_music_url, resolve_cover_url
from app.services.file_cleanup import delete_file_best_effort
from app.db.session import SessionLocal
from app.services.storage_service import save_audio_bytes
from app.songgen.songgen_remote import get_songgen_prompt_audio_client

router = APIRouter()


def _is_public_published(status: str | WorkStatus, visibility: str | WorkVisibility) -> bool:
  status_value = status.value if isinstance(status, WorkStatus) else str(status)
  visibility_value = visibility.value if isinstance(visibility, WorkVisibility) else str(visibility)
  return status_value == WorkStatus.published.value and visibility_value == WorkVisibility.public.value


@router.post(
    "/generate-file",
    response_model=MusicGenerateResult,
    summary="Generate music via MusicGen and return file URL",
)
async def generate_music_file(
    payload: MusicGenerateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MusicGenerateResult:
  model_name = payload.model or ("songgen_full_new" if settings.SONGGEN_REMOTE_URL else "musicgen_pretrained")
  if model_name not in {"musicgen_pretrained", "musicgen_finetune", "songgen_full_new"}:
    raise HTTPException(status_code=400, detail="不支持的模型")

  # 默认时长改为更“完整”的段落长度（用户侧不再强依赖手动选择时长）
  duration = payload.duration_seconds or 120
  try:
    gen_result = generation_service.generate_music_file(
        prompt_zh=payload.prompt,
        duration_sec=float(duration),
        model_name=model_name,  # type: ignore[arg-type]
        instrumental=bool(getattr(payload, "instrumental", True)),
        lyrics=getattr(payload, "lyrics", None),
        style=payload.style,
    )
  except Exception as exc:
    raise HTTPException(status_code=500, detail=f"生成失败: {exc}") from exc

  # 上传到 OSS（按 generated 分类）
  stored_path = gen_result.rel_path
  audio_abs = Path(gen_result.rel_path)
  if not audio_abs.is_absolute():
    audio_abs = Path.cwd() / audio_abs
  if settings.OSS_ENABLED:
    try:
      key = build_oss_key(
          category="music",
          source="generated",
          user_id=current_user.id,
          original_filename=gen_result.filename,
          ext=Path(gen_result.filename).suffix,
      )
      OSSStorage().put_file(key, str(audio_abs), content_type="audio/wav")
      stored_path = encode_oss_path(key)
      print(f"[music/generate-file] Uploaded to OSS key={key}")
      if getattr(settings, "DELETE_LOCAL_AUDIO_AFTER_OSS_UPLOAD", False):
        ok = delete_file_best_effort(audio_abs)
        if ok:
          print(f"[music/generate-file] Deleted local audio cache: {audio_abs}")
    except Exception as exc:
      print(f"[music/generate-file] Upload to OSS failed, keep local path: {exc}")

  audio_url = resolve_storage_path_to_url(stored_path) or f"/{gen_result.rel_path}"

  # 自动生成封面（并按配置上传到 OSS），失败不影响音乐生成
  cover_url: str | None = None
  try:
    cover_prompt = await llm_service.build_album_cover_prompt(payload.prompt)
    cover_path = await image_service.generate_album_cover_image(
        cover_prompt, user_id=current_user.id
    )
    cover_url = resolve_cover_url(cover_path)
  except Exception as exc:
    import traceback
    print(f"[music/generate-file] cover generation failed: {exc}\n{traceback.format_exc()}")
    cover_url = None

  # 生成成功计数
  current_user.total_generations = (current_user.total_generations or 0) + 1
  db.add(current_user)
  db.commit()
  db.refresh(current_user)

  return MusicGenerateResult(
      audio_url=audio_url,
      cover_url=cover_url,
      format="wav",
      duration_seconds=int(gen_result.duration_sec),
      prompt=payload.prompt,
      notes=f"model={gen_result.model_name}",
  )


def _background_imitate_with_prompt_audio(
    task_id: str,
    *,
    user_id: int,
    prompt: str,
    duration_sec: int,
    instrumental: bool,
    lyrics: str | None,
    style: str | None,
    prompt_audio_filename: str,
    prompt_audio_bytes: bytes,
    prompt_audio_content_type: str | None,
) -> None:
  """
  后台仿写任务：
  - 不写入 music_files（用户说“不需要像情绪识别一样需要保存”）
  - 生成完成后返回一个可播放 URL（本地 static/audio 或 OSS URL）
  """
  db = SessionLocal()
  try:
    try:
      tasks.set_status(db, task_id, TaskStatus.processing)
    except Exception:
      pass

    client = get_songgen_prompt_audio_client()
    job_id = client.submit_with_prompt_audio(
        prompt=prompt or "",
        style=style,
        duration_sec=int(duration_sec),
        fmt="wav",
        seed=None,
        separate=False,
        instrumental=bool(instrumental),
        vocal_only=False,
        lyrics=lyrics,
        prompt_audio_filename=prompt_audio_filename,
        prompt_audio_bytes=prompt_audio_bytes,
        prompt_audio_content_type=prompt_audio_content_type,
        auto_prompt_audio_type=None,
        timeout_seconds=int(settings.SONGGEN_REQUEST_TIMEOUT_SECONDS),
    )

    result = client.poll_until_done(
        job_id,
        timeout_seconds=int(settings.SONGGEN_TOTAL_TIMEOUT_SECONDS),
        poll_interval_seconds=float(settings.SONGGEN_POLL_INTERVAL_SECONDS),
    )
    if result.status != "succeeded":
      raise RuntimeError(result.error or f"songgen failed (job_id={job_id})")

    audio_bytes = client.download_audio(job_id, timeout_seconds=int(settings.SONGGEN_REQUEST_TIMEOUT_SECONDS))
    filename = save_audio_bytes(audio_bytes, prefix="songgen_imitate", ext="wav")
    rel_path = f"static/audio/{filename}"

    stored_path = rel_path
    if settings.OSS_ENABLED:
      try:
        key = build_oss_key(
            category="music",
            source="imitated",
            user_id=user_id,
            original_filename=filename,
            ext=".wav",
        )
        audio_abs = Path(rel_path)
        if not audio_abs.is_absolute():
          audio_abs = Path.cwd() / audio_abs
        OSSStorage().put_file(key, str(audio_abs), content_type="audio/wav")
        stored_path = encode_oss_path(key)
        if getattr(settings, "DELETE_LOCAL_AUDIO_AFTER_OSS_UPLOAD", False):
          delete_file_best_effort(audio_abs)
      except Exception as exc:
        print(f"[music/imitate-task] Upload to OSS failed, keep local path: {exc}")

    audio_url = resolve_storage_path_to_url(stored_path) or f"/{rel_path}"

    # best-effort title
    try:
      title = asyncio.run(llm_service.build_music_title(prompt or "音乐仿写"))
    except Exception:
      title = (prompt or "").strip()[:12] or "音乐仿写"

    tasks.complete_task(
        db,
        task_id,
        result={
            "id": f"imitate-{task_id}",
            "music_file_id": None,
            "title": title,
            "artist": "AI Imitator",
            "url": audio_url,
            "duration": int(duration_sec),
            "cover": None,
            "reply": "音乐仿写已完成，请试听。",
            "can_save": False,
        },
    )
  except Exception as exc:
    try:
      tasks.fail_task(db, task_id, str(exc))
    except Exception:
      pass
  finally:
    db.close()


@router.post(
    "/imitate-task",
    response_model=TaskCreateResponse,
    summary="音乐仿写（with prompt audio）：上传参考音频并异步生成",
)
async def imitate_music_task(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(..., description="参考音频文件（只取前 10 秒）"),
    prompt: str = Form("", description="可选：附加文字指令（如 伤心 钢琴 电影感）"),
    duration_seconds: int = Form(120, ge=1, le=600),
    instrumental: bool = Form(True),
    lyrics: str | None = Form(None),
    style: str | None = Form(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TaskCreateResponse:
  # 读取文件到内存（prompt audio 通常较小；如需更大文件支持可改为落盘临时文件再转发）
  try:
    prompt_audio_bytes = await file.read()
  except Exception as exc:
    raise HTTPException(status_code=400, detail=f"读取上传文件失败: {exc}") from exc

  # Create async task record (reuse TaskType.generate_music to avoid DB enum migration)
  record = tasks.create_task(
      db,
      user_id=current_user.id,
      task_type=TaskType.generate_music,
      input_payload={
          "mode": "imitate",
          "prompt": prompt,
          "duration_seconds": int(duration_seconds),
          "instrumental": bool(instrumental),
          "lyrics": lyrics,
          "style": style,
          "ref_filename": file.filename,
          "ref_content_type": file.content_type,
          "ref_size": len(prompt_audio_bytes),
      },
      auto_complete=False,
  )
  try:
    tasks.set_status(db, record.id, TaskStatus.processing)
  except Exception:
    pass

  background_tasks.add_task(
      _background_imitate_with_prompt_audio,
      record.id,
      user_id=current_user.id,
      prompt=prompt,
      duration_sec=int(duration_seconds),
      instrumental=bool(instrumental),
      lyrics=(lyrics or "").strip() or None,
      style=(style or "").strip() or None,
      prompt_audio_filename=file.filename or "prompt_audio.wav",
      prompt_audio_bytes=prompt_audio_bytes,
      prompt_audio_content_type=file.content_type,
  )

  return TaskCreateResponse(task_id=record.id, status=record.status)


@router.post(
    "/generate-cover",
    summary="Generate only the album cover image",
)
async def generate_cover_only(
    payload: MusicGenerateRequest,
    current_user: User = Depends(get_current_user),
) -> dict:
    """仅生成封面，用于提升前端响应速度（Suno 体验）"""
    try:
        # 1. LLM 生成 Prompt
        cover_prompt = await llm_service.build_album_cover_prompt(payload.prompt)
        # 2. 生成图片
        cover_path = await image_service.generate_album_cover_image(
            cover_prompt, user_id=current_user.id
        )
        cover_url = resolve_cover_url(cover_path)
        return {"cover_url": cover_url}
    except Exception as exc:
        print(f"[music/generate-cover] failed: {exc}")
        return {"cover_url": None}


@router.post(
    "/generate",
    response_model=TaskCreateResponse,
    summary="Submit a music generation request",
)
async def request_music_generation(
    payload: MusicGenerateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TaskCreateResponse:
  # 每次生成请求计数
  current_user.total_generations = (current_user.total_generations or 0) + 1
  db.add(current_user)

  record = tasks.create_task(
      db,
      user_id=current_user.id,
      task_type=TaskType.generate_music,
      input_payload=payload.model_dump(),
      auto_complete=True,
      result=MusicGenerateResult(
          audio_url="https://example.com/generated/demo.mp3",
          format="mp3",
          duration_seconds=payload.duration_seconds or 30,
          prompt=payload.prompt,
          notes="Demo result placeholder. Replace with real generation output.",
      ).model_dump(),
  )
  return TaskCreateResponse(task_id=record.id, status=record.status)


@router.get(
    "/generate/{task_id}",
    response_model=TaskDetail,
    summary="Check music generation status",
)
async def get_music_generation(task_id: str, db: Session = Depends(get_db)) -> TaskDetail:
  record = tasks.get_task(db, task_id, expected_type=TaskType.generate_music)
  if not record:
    raise HTTPException(status_code=404, detail="Task not found")
  # 防止“僵尸任务”无限 processing（例如长任务期间 DB 断连导致 background 未能写回状态）
  try:
    status_value = record.status.value if hasattr(record.status, "value") else str(record.status)
    if status_value == TaskStatus.processing.value:
      stale_after = int(getattr(settings, "SONGGEN_TOTAL_TIMEOUT_SECONDS", 15 * 60)) + 300
      updated_at = getattr(record, "updated_at", None)
      if updated_at and (datetime.utcnow() - updated_at).total_seconds() > stale_after:
        tasks.fail_task(db, task_id, "任务超时未更新（可能后端重启或数据库断连）。请重新生成。")
        record = tasks.get_task(db, task_id, expected_type=TaskType.generate_music) or record
  except Exception:
    # best-effort only; never break polling endpoint
    pass
  return tasks.to_task_detail(record)


@router.post(
    "/analyze",
    response_model=TaskCreateResponse,
    summary="Submit audio for emotion analysis",
)
async def request_emotion_analysis(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TaskCreateResponse:
  # 保存文件到本地
  upload_root = Path(settings.MEDIA_ROOT)
  upload_root.mkdir(parents=True, exist_ok=True)
  ext = Path(file.filename).suffix
  filename = f"{uuid4()}{ext}"
  filepath = upload_root / filename
  with open(filepath, "wb") as f:
    content = await file.read()
    f.write(content)

  # 情绪分析计数
  current_user.emotion_detection_count = (current_user.emotion_detection_count or 0) + 1
  db.add(current_user)

  record = tasks.create_task(
      db,
      user_id=current_user.id,
      task_type=TaskType.analyze_emotion,
      input_payload={"filename": file.filename, "stored_path": str(filepath), "content_type": file.content_type},
      auto_complete=True,
      result=EmotionAnalysisResult(
          emotion="calm",
          confidence=0.87,
          extra={"note": "Demo response. Replace with real model output."},
      ).model_dump(),
  )
  return TaskCreateResponse(task_id=record.id, status=record.status)


@router.get(
    "/analyze/{task_id}",
    response_model=TaskDetail,
    summary="Check emotion analysis status",
)
async def get_emotion_analysis(task_id: str, db: Session = Depends(get_db)) -> TaskDetail:
  record = tasks.get_task(db, task_id, expected_type=TaskType.analyze_emotion)
  if not record:
    raise HTTPException(status_code=404, detail="Task not found")
  return tasks.to_task_detail(record)


@router.get(
    "/history",
    response_model=list[TaskDetail],
    summary="List recent tasks",
)
async def list_tasks(
    status: TaskStatus | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[TaskDetail]:
  records = tasks.list_tasks(db, user_id=current_user.id, status=status)
  return [tasks.to_task_detail(r) for r in records]


@router.post(
    "/save-work",
    response_model=WorkResponse,
    summary="保存已生成的音乐到作品（mywork）",
)
async def save_work(
    payload: WorkCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> WorkResponse:
  music_file = (
      db.query(MusicFile)
      .filter(MusicFile.id == payload.music_file_id, MusicFile.user_id == current_user.id)
      .first()
  )
  if not music_file:
    raise HTTPException(status_code=404, detail="音乐文件不存在或无权限")

  desired_status = payload.status or WorkStatus.draft.value
  if desired_status not in {WorkStatus.draft.value, WorkStatus.published.value}:
    desired_status = WorkStatus.draft.value
  desired_visibility = payload.visibility or WorkVisibility.public.value
  if desired_visibility not in {
      WorkVisibility.public.value,
      WorkVisibility.unlisted.value,
      WorkVisibility.private.value,
  }:
    desired_visibility = WorkVisibility.public.value

  # 若已有绑定作品则直接返回，避免重复创建
  existing = (
      db.query(Work)
      .filter(Work.music_file_id == music_file.id, Work.user_id == current_user.id)
      .first()
  )
  if existing:
    return WorkResponse(
        id=existing.id,
        music_file_id=existing.music_file_id,
        name=existing.title,
        title=existing.title,
        description=existing.description,
        tags=existing.tags,
        status=existing.status.value if isinstance(existing.status, WorkStatus) else str(existing.status),
        visibility=existing.visibility.value
        if isinstance(existing.visibility, WorkVisibility)
        else str(existing.visibility),
        mood=existing.mood,
        cover_url=resolve_cover_url(existing.cover_url),
        like_count=existing.like_count,
        play_count=existing.play_count,
        audio_url=resolve_music_url(music_file),
        created_at=existing.created_at,
        updated_at=existing.updated_at,
        published_at=existing.published_at,
    )

  work = Work(
      user_id=current_user.id,
      music_file_id=music_file.id,
      title=payload.title or Path(music_file.file_name).stem,
      description=payload.description,
      tags=payload.tags,
      status=WorkStatus(desired_status),
      visibility=WorkVisibility(desired_visibility),
      mood=payload.mood,
      cover_url=normalize_oss_like_url(payload.cover_url),
  )
  db.add(work)

  # 计数更新，仅统计公开且已发布的作品
  if _is_public_published(work.status, work.visibility):
    current_user.total_works = (current_user.total_works or 0) + 1
    db.add(current_user)

  db.commit()
  db.refresh(work)

  return WorkResponse(
      id=work.id,
      music_file_id=work.music_file_id,
      name=work.title,
      title=work.title,
      description=work.description,
      tags=work.tags,
      status=work.status.value if isinstance(work.status, WorkStatus) else str(work.status),
      visibility=work.visibility.value if isinstance(work.visibility, WorkVisibility) else str(work.visibility),
      mood=work.mood,
      cover_url=resolve_cover_url(work.cover_url),
      like_count=work.like_count,
      play_count=work.play_count,
      audio_url=resolve_music_url(music_file),
      created_at=work.created_at,
      updated_at=work.updated_at,
      published_at=work.published_at,
  )
