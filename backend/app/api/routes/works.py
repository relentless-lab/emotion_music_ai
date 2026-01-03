from pathlib import Path
from uuid import uuid4
from datetime import datetime

from fastapi import APIRouter, Body, Depends, HTTPException, File, UploadFile, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.dependencies import get_current_user, get_current_user_optional, get_db
from app.models.like_record import LikeRecord
from app.models.music_file import MusicFile
from app.models.user import User
from app.models.work import Work, WorkStatus, WorkVisibility
from app.models.work_play_log import WorkPlayLog
from app.schemas.social import SimpleMessage
from app.schemas.work import WorkAuthor, WorkCreateRequest, WorkPublicResponse, WorkResponse, WorkUpdateRequest
from app.schemas.work import WorkPlayRequest
from app.services.oss_storage import (
    OSSStorage,
    build_oss_key,
    decode_oss_path,
    encode_oss_path,
    normalize_oss_like_url,
)
from app.services.url_resolver import resolve_cover_url, resolve_music_url

router = APIRouter()


def _resolve_audio_url(music_file: MusicFile | None) -> str | None:
  return resolve_music_url(music_file)


def _to_response(work: Work, music_file: MusicFile | None = None) -> WorkResponse:
  music_file = music_file or work.music_file
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
      audio_url=_resolve_audio_url(music_file),
      created_at=work.created_at,
      updated_at=work.updated_at,
      published_at=work.published_at,
  )


def _to_public_work(
    work: Work,
    music_file: MusicFile | None = None,
    liked: bool = False,
) -> WorkPublicResponse:
  base = _to_response(work, music_file)
  author = work.user
  author_payload = WorkAuthor(
      id=author.id,
      username=author.username,
      avatar=author.avatar,
      followers=author.followers_count,
      following=author.following_count,
  )
  return WorkPublicResponse(**base.model_dump(), author=author_payload, liked=liked)


@router.get("", response_model=list[WorkResponse], summary="List my works")
async def list_works(
    status: str | None = None,
    visibility: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[WorkResponse]:
  query = db.query(Work).filter(Work.user_id == current_user.id)
  if status in {WorkStatus.draft.value, WorkStatus.published.value}:
    query = query.filter(Work.status == WorkStatus(status))
  if visibility in {WorkVisibility.public.value, WorkVisibility.unlisted.value, WorkVisibility.private.value}:
    query = query.filter(Work.visibility == WorkVisibility(visibility))

  works = query.order_by(Work.created_at.desc()).all()
  music_file_map = {
      mf.id: mf
      for mf in db.query(MusicFile).filter(MusicFile.id.in_([w.music_file_id for w in works])).all()
  }
  return [_to_response(w, music_file_map.get(w.music_file_id)) for w in works]


def _is_public_published(work: Work) -> bool:
  status_value = work.status.value if isinstance(work.status, WorkStatus) else str(work.status)
  visibility_value = work.visibility.value if isinstance(work.visibility, WorkVisibility) else str(work.visibility)
  return status_value == WorkStatus.published.value and visibility_value == WorkVisibility.public.value


def _create_work_for_user(
    db: Session,
    current_user: User,
    payload: WorkCreateRequest,
) -> Work:
  music_file_id = payload.music_file_id or payload.id
  if not music_file_id:
    raise HTTPException(status_code=422, detail="music_file_id 不能为空")

  music_file = (
      db.query(MusicFile)
      .filter(MusicFile.id == music_file_id, MusicFile.user_id == current_user.id)
      .first()
  )
  if not music_file:
    raise HTTPException(status_code=404, detail="音乐文件不存在或无权限")

  existing = (
      db.query(Work)
      .filter(Work.music_file_id == music_file.id, Work.user_id == current_user.id)
      .first()
  )
  if existing:
    # 如果已存在，但新请求提供了 mood 或 description，则更新它们（支持从对话中补全需求信息）
    # 增加对 "无" 或 "生成的音乐" 这种占位符的检查
    if payload.mood and (not existing.mood or existing.mood in ("无", "生成的音乐")):
      existing.mood = payload.mood
    if payload.description and (not existing.description or existing.description in ("无", "生成的音乐")):
      existing.description = payload.description
    if payload.title and existing.title == music_file.file_name:
      existing.title = payload.title
    db.commit()
    db.refresh(existing)
    return existing

  status_value = payload.status or WorkStatus.draft.value
  if status_value not in {WorkStatus.draft.value, WorkStatus.published.value}:
    status_value = WorkStatus.draft.value
  visibility_value = payload.visibility or WorkVisibility.public.value
  if visibility_value not in {WorkVisibility.public.value, WorkVisibility.unlisted.value, WorkVisibility.private.value}:
    visibility_value = WorkVisibility.public.value
  cover_value = normalize_oss_like_url(payload.cover_url)

  work = Work(
      user_id=current_user.id,
      music_file_id=music_file.id,
      title=payload.title or music_file.file_name,
      description=payload.description,
      tags=payload.tags,
      status=WorkStatus(status_value),
      visibility=WorkVisibility(visibility_value),
      mood=payload.mood,
      cover_url=cover_value,
  )
  db.add(work)

  if _is_public_published(work):
    current_user.total_works = (current_user.total_works or 0) + 1
    db.add(current_user)

  db.commit()
  db.refresh(work)
  return work


@router.post("", response_model=WorkResponse, summary="Create a work from a generated music file")
async def create_work(
    payload: WorkCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> WorkResponse:
  work = _create_work_for_user(db, current_user, payload)
  return _to_response(work, db.query(MusicFile).filter(MusicFile.id == work.music_file_id).first())


@router.post("/quick-save", response_model=WorkResponse, summary="Quick save a music file to my works")
async def quick_save_work(
    payload: WorkCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> WorkResponse:
  """
  前端只需传 music_file_id，即可快速保存到作品。
  其他字段（title/description/tags/status）可选。
  """
  work = _create_work_for_user(db, current_user, payload)
  return _to_response(work, db.query(MusicFile).filter(MusicFile.id == work.music_file_id).first())


@router.put("/{work_id}", response_model=WorkResponse, summary="Update a work")
async def update_work(
    work_id: int,
    payload: WorkUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> WorkResponse:
  work = (
      db.query(Work)
      .filter(Work.id == work_id, Work.user_id == current_user.id)
      .first()
  )
  if not work:
    raise HTTPException(status_code=404, detail="作品不存在或无权限")

  was_public_published = _is_public_published(work)

  if payload.title is not None:
    work.title = payload.title
  if payload.description is not None:
    work.description = payload.description
  if payload.tags is not None:
    work.tags = payload.tags
  if payload.status is not None:
    if payload.status in {WorkStatus.draft.value, WorkStatus.published.value}:
      work.status = WorkStatus(payload.status)
  if payload.visibility is not None:
    if payload.visibility in {
        WorkVisibility.public.value,
        WorkVisibility.unlisted.value,
        WorkVisibility.private.value,
    }:
      work.visibility = WorkVisibility(payload.visibility)
  if payload.mood is not None:
    work.mood = payload.mood
  if payload.cover_url is not None:
    work.cover_url = normalize_oss_like_url(payload.cover_url)

  db.add(work)

  is_public_published = _is_public_published(work)
  if was_public_published != is_public_published:
    delta = 1 if is_public_published else -1
    current_total = current_user.total_works or 0
    current_user.total_works = max(current_total + delta, 0)
    db.add(current_user)

  db.commit()
  db.refresh(work)

  return _to_response(work)


@router.delete("/{work_id}", summary="Delete a work", status_code=204)
async def delete_work(
    work_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
  import os
  
  work = (
      db.query(Work)
      .filter(Work.id == work_id, Work.user_id == current_user.id)
      .first()
  )
  if not work:
    raise HTTPException(status_code=404, detail="作品不存在或无权限")

  was_public_published = _is_public_published(work)

  # 删除封面文件
  if work.cover_url:
    try:
      oss_key = decode_oss_path(work.cover_url)
      if oss_key and settings.OSS_ENABLED:
        OSSStorage().delete(oss_key)
      else:
        # cover_url 格式如 "/static/covers/xxx.png" 或 "static/covers/xxx.png"
        cover_path = work.cover_url.lstrip("/")
        if cover_path.startswith("static/covers/"):
          # 只提取文件名，防止路径穿越
          filename = Path(cover_path).name
          covers_dir = Path(settings.STATIC_ROOT) / "covers"
          full_cover_path = covers_dir / filename
          # 安全检查：确保解析后的路径在 covers 目录下
          if full_cover_path.exists() and full_cover_path.is_file():
            resolved_path = full_cover_path.resolve()
            resolved_dir = covers_dir.resolve()
            if str(resolved_path).startswith(str(resolved_dir)):
              os.remove(full_cover_path)
    except Exception as e:
      # 删除文件失败不影响数据库删除，只记录日志
      print(f"[delete_work] Failed to delete cover file: {e}")

  # 删除音频文件（通过 music_file）
  music_file = db.query(MusicFile).filter(MusicFile.id == work.music_file_id).first()
  if music_file:
    try:
      oss_key = decode_oss_path(music_file.storage_path)
      if oss_key and settings.OSS_ENABLED:
        OSSStorage().delete(oss_key)
      else:
        # 音频文件存储在 static/audio/ 目录下
        audio_filename = music_file.file_name
        if audio_filename:
          # 只使用文件名，防止路径穿越
          filename = Path(audio_filename).name
          audio_dir = Path(settings.STATIC_ROOT) / "audio"
          audio_path = audio_dir / filename
          # 安全检查：确保解析后的路径在 audio 目录下
          if audio_path.exists() and audio_path.is_file():
            resolved_path = audio_path.resolve()
            resolved_dir = audio_dir.resolve()
            if str(resolved_path).startswith(str(resolved_dir)):
              os.remove(audio_path)
    except Exception as e:
      # 删除文件失败不影响数据库删除，只记录日志
      print(f"[delete_work] Failed to delete audio file: {e}")

  db.delete(work)

  if was_public_published:
    current_user.total_works = max((current_user.total_works or 0) - 1, 0)
    db.add(current_user)

  db.commit()


@router.get(
    "/public/{work_id}",
    response_model=WorkPublicResponse,
    summary="Public work detail (no auth required)",
)
async def get_public_work(
    work_id: int,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_current_user_optional),
) -> WorkPublicResponse:
  work = db.query(Work).filter(Work.id == work_id).first()
  if not work or not _is_public_published(work):
    raise HTTPException(status_code=404, detail="作品不存在或未公开")

  liked = False
  if current_user:
    liked = (
        db.query(LikeRecord)
        .filter(LikeRecord.user_id == current_user.id, LikeRecord.work_id == work.id)
        .first()
        is not None
    )

  music_file = db.query(MusicFile).filter(MusicFile.id == work.music_file_id).first()
  return _to_public_work(work, music_file, liked=liked)


@router.post(
    "/{work_id}/play",
    response_model=SimpleMessage,
    summary="Record a play for a public work (no auth required)",
)
async def record_work_play(
    work_id: int,
    payload: WorkPlayRequest | None = Body(default=None),
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_current_user_optional),
) -> SimpleMessage:
  """
  Write a play log (for trending window queries) and increment `works.play_count`.

  This endpoint is anonymous-friendly so public pages can track plays without forcing a login.
  """
  work = db.query(Work).filter(Work.id == work_id).first()
  if not work or not _is_public_published(work):
    raise HTTPException(status_code=404, detail="作品不存在或未公开")

  source = (payload.source if payload else None) or None
  if source and len(source) > 50:
    source = source[:50]

  db.add(
      WorkPlayLog(
          user_id=current_user.id if current_user else None,
          work_id=work_id,
          played_at=datetime.utcnow(),
          source=source,
      )
  )

  work.play_count = (work.play_count or 0) + 1
  db.add(work)

  # Update author's aggregate counters (best-effort)
  author = work.user
  if author:
    author.plays_received = (author.plays_received or 0) + 1
    db.add(author)

  db.commit()
  return SimpleMessage(message="ok")


@router.get(
    "/public/by-user/{user_id}",
    response_model=list[WorkPublicResponse],
    summary="List public works for a user",
)
async def list_public_works_by_user(
    user_id: int,
    limit: int = 20,
    offset: int = 0,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_current_user_optional),
) -> list[WorkPublicResponse]:
  safe_limit = min(max(limit, 1), 50)
  works = (
      db.query(Work)
      .filter(
          Work.user_id == user_id,
          Work.status == WorkStatus.published,
          Work.visibility == WorkVisibility.public,
      )
      .order_by(Work.created_at.desc())
      .offset(offset)
      .limit(safe_limit)
      .all()
  )
  music_file_map = {
      mf.id: mf
      for mf in db.query(MusicFile).filter(MusicFile.id.in_([w.music_file_id for w in works])).all()
  }

  liked_ids: set[int] = set()
  if current_user and works:
    liked_rows = (
        db.query(LikeRecord.work_id)
        .filter(
            LikeRecord.user_id == current_user.id,
            LikeRecord.work_id.in_([w.id for w in works]),
        )
        .all()
    )
    liked_ids = {row[0] for row in liked_rows}

  return [
      _to_public_work(w, music_file_map.get(w.music_file_id), liked=w.id in liked_ids)
      for w in works
  ]


@router.post(
    "/upload-cover",
    summary="Upload a cover image for a work",
)
async def upload_cover(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
) -> dict:
  if not file.content_type or not file.content_type.startswith("image/"):
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="请上传图片文件")

  suffix = Path(file.filename or "").suffix or ".png"
  content = await file.read()

  # 优先 OSS
  if settings.OSS_ENABLED:
    try:
      key = build_oss_key(
          category="picture",
          source="upload",
          user_id=current_user.id,
          original_filename=file.filename,
          ext=suffix,
      )
      OSSStorage().put_bytes(key, content, content_type=file.content_type)
      cover_path = encode_oss_path(key)
      cover_url = OSSStorage().get_url(key)
      return {"cover_url": cover_url, "cover_path": cover_path}
    except Exception as exc:
      print(f"[upload_cover] Upload to OSS failed, fallback local: {exc}")

  # 本地兜底
  covers_dir = Path(settings.STATIC_ROOT) / "covers"
  covers_dir.mkdir(parents=True, exist_ok=True)
  filename = f"{uuid4()}{suffix}"
  dest = covers_dir / filename
  dest.write_bytes(content)
  return {"cover_url": f"/static/covers/{filename}"}
