from pathlib import Path
from uuid import uuid4

import asyncio
from concurrent.futures import ThreadPoolExecutor

from fastapi import APIRouter, BackgroundTasks, Body, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.dependencies import get_current_user, get_db
from app.db.session import SessionLocal
from app.models.emotion_analysis import EmotionAnalysis
from app.models.music_file import MusicFile
from app.models.user import User
from app.schemas.emotion import EmotionAnalysisResponse, EmotionSummaryResponse, EmotionTaskCreateResponse
from app.schemas.tasks import TaskCreateResponse, TaskDetail, TaskStatus, TaskType
from app.services import emotion_service, llm, tasks
from app.services.oss_storage import OSSStorage, build_oss_key, encode_oss_path
from app.services.url_resolver import resolve_music_url

router = APIRouter()

# Use a dedicated executor for heavy emotion inference so it won't starve the default threadpool
# that also serves sync DB handlers and other endpoints.
_EMOTION_EXECUTOR = ThreadPoolExecutor(max_workers=1)


@router.post(
    "/analyze",
    response_model=EmotionAnalysisResponse,
    summary="Upload audio and run emotion analysis",
)
async def analyze_emotion(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> EmotionAnalysisResponse:
  print(f"[emotion/analyze] Received file: {file.filename}, content_type: {file.content_type}")
  
  # Save file to disk
  upload_root = Path(settings.MEDIA_ROOT)
  upload_root.mkdir(parents=True, exist_ok=True)
  ext = Path(file.filename).suffix
  filename = f"{uuid4()}{ext}"
  filepath = upload_root / filename
  try:
    content = await file.read()
    print(f"[emotion/analyze] File size: {len(content)} bytes")
  except Exception as exc:  # pragma: no cover - simple IO guard
    print(f"[emotion/analyze] File read failed: {exc}")
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="File read failed") from exc

  with open(filepath, "wb") as f:
    f.write(content)
  print(f"[emotion/analyze] File saved to: {filepath}")

  # 上传到 OSS（存档），并记录存储路径
  stored_path = str(filepath)
  if settings.OSS_ENABLED:
    try:
      key = build_oss_key(
          category="music",
          source="upload",
          user_id=current_user.id,
          original_filename=file.filename,
      )
      OSSStorage().put_bytes(key, content, content_type=file.content_type)
      stored_path = encode_oss_path(key)
      print(f"[emotion/analyze] Uploaded to OSS key={key}")
    except Exception as exc:
      print(f"[emotion/analyze] Upload to OSS failed, keep local path: {exc}")

  # Create music file record
  music_file = MusicFile(
      user_id=current_user.id,
      file_name=file.filename or filename,
      storage_path=stored_path,
      size_bytes=len(content),
      file_type=file.content_type,
  )
  db.add(music_file)
  db.flush()

  # Run real emotion analysis via local model
  print(f"[emotion/analyze] Starting emotion analysis for: {filepath}")
  try:
    analysis_result = emotion_service.analyze_music(str(filepath))
    print(f"[emotion/analyze] Analysis completed successfully")
  except FileNotFoundError as e:
    error_msg = f"模型文件未找到: {str(e)}"
    print(f"[emotion/analyze] ERROR: {error_msg}")
    raise HTTPException(
      status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
      detail=error_msg
    ) from e
  except Exception as e:
    import traceback
    error_detail = f"情绪分析失败: {str(e)}\n{traceback.format_exc()}"
    print(f"[emotion/analyze] ERROR: {error_detail}")
    raise HTTPException(
      status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
      detail=f"情绪分析失败: {str(e)}"
    ) from e
  
  overall_dist = analysis_result.get("overall_distribution") or {}
  main_emotion = analysis_result.get("quadrant", {}).get("dominant_label_en") or "unknown"
  confidence = float(max(overall_dist.values())) if overall_dist else 0.0
  overall_arousal = analysis_result.get("quadrant", {}).get("arousal")
  raw_result = analysis_result

  # 生成摘要（若未配置 LLM 则返回占位）
  try:
    summary = await llm.summarize_emotion(raw_result)
  except Exception:
    summary = "（占位）整体情绪分析已完成，但未启用 LLM 总结。"
  if not summary:
    summary = "（占位）整体情绪分析已完成"

  # 持久化摘要进 raw_result，便于历史接口取用
  if isinstance(raw_result, dict):
    raw_result["summary"] = summary
    if isinstance(raw_result.get("extra"), dict):
      raw_result["extra"]["summary"] = summary
    else:
      raw_result["extra"] = {"summary": summary}

  # 保存摘要到文件，填充 report_path（可空）
  report_path_str = None
  try:
    report_dir = upload_root / "reports"
    report_dir.mkdir(parents=True, exist_ok=True)
    report_filename = f"{Path(filename).stem}_summary.txt"
    report_path = report_dir / report_filename
    report_path.write_text(summary, encoding="utf-8")
    report_path_str = str(report_path)
  except Exception:
    report_path_str = None

  analysis = EmotionAnalysis(
      music_file_id=music_file.id,
      user_id=current_user.id,
      main_emotion=main_emotion,
      emotion_intensity=confidence,
      arousal_level=float(overall_arousal) if overall_arousal is not None else None,
      raw_result=raw_result,
      report_path=report_path_str,
  )
  db.add(analysis)

  current_user.emotion_detection_count = (current_user.emotion_detection_count or 0) + 1
  db.add(current_user)

  db.commit()
  db.refresh(analysis)
  db.refresh(music_file)

  print("summary = %s",summary)
  return EmotionAnalysisResponse(
      analysis_id=analysis.id,
      music_file_id=music_file.id,
      emotion=analysis.main_emotion or "",
      confidence=float(analysis.emotion_intensity) if analysis.emotion_intensity is not None else 0.0,
      extra=analysis.raw_result,
      summary=summary,
      created_at=analysis.created_at,
  )


def _background_analyze_emotion(task_id: str, user_id: int, music_file_id: int, local_path: str) -> None:
  """Run emotion analysis in background and complete TaskRecord."""
  db = SessionLocal()
  try:
    try:
      tasks.set_status(db, task_id, TaskStatus.processing)
    except Exception:
      pass

    # Reduce CPU starvation while running heavy inference (does not change model logic/output).
    try:
      import torch  # local import to avoid import-time overhead when not used
      torch.set_num_threads(1)
      torch.set_num_interop_threads(1)
    except Exception:
      pass

    analysis_result = emotion_service.analyze_music(local_path)
    raw_result = analysis_result if isinstance(analysis_result, dict) else {"result": analysis_result}

    overall_dist = raw_result.get("overall_distribution") or {}
    main_emotion = raw_result.get("quadrant", {}).get("dominant_label_en") or "unknown"
    confidence = float(max(overall_dist.values())) if overall_dist else 0.0
    overall_arousal = raw_result.get("quadrant", {}).get("arousal")

    # 生成摘要（若未配置 LLM 则返回占位）
    try:
      summary = asyncio.run(llm.summarize_emotion(raw_result))
    except Exception:
      summary = "（占位）整体情绪分析已完成"
    if not summary:
      summary = "（占位）整体情绪分析已完成"

    # 持久化摘要进 raw_result，便于历史接口取用
    if isinstance(raw_result, dict):
      raw_result["summary"] = summary
      if isinstance(raw_result.get("extra"), dict):
        raw_result["extra"]["summary"] = summary
      else:
        raw_result["extra"] = {"summary": summary}

    # 保存摘要到文件，填充 report_path（可空）
    report_path_str = None
    try:
      upload_root = Path(settings.MEDIA_ROOT)
      report_dir = upload_root / "reports"
      report_dir.mkdir(parents=True, exist_ok=True)
      report_filename = f"{Path(local_path).stem}_summary.txt"
      report_path = report_dir / report_filename
      report_path.write_text(summary, encoding="utf-8")
      report_path_str = str(report_path)
    except Exception:
      report_path_str = None

    analysis = EmotionAnalysis(
        music_file_id=music_file_id,
        user_id=user_id,
        main_emotion=main_emotion,
        emotion_intensity=confidence,
        arousal_level=float(overall_arousal) if overall_arousal is not None else None,
        raw_result=raw_result,
        report_path=report_path_str,
    )
    db.add(analysis)
    db.commit()
    db.refresh(analysis)

    # 任务结果：尽量与 /emotion/analyze 的返回字段对齐（注意 JSON 不能存 datetime）
    result = {
        "analysis_id": analysis.id,
        "music_file_id": music_file_id,
        "emotion": analysis.main_emotion or "",
        "confidence": float(analysis.emotion_intensity) if analysis.emotion_intensity is not None else 0.0,
        "extra": raw_result,
        "summary": summary,
    }
    tasks.complete_task(db, task_id, result=result)
  except Exception as exc:
    tasks.fail_task(db, task_id, str(exc))
  finally:
    db.close()


def _submit_emotion_job(task_id: str, user_id: int, music_file_id: int, local_path: str) -> None:
  """
  Submit heavy work to a dedicated executor to avoid blocking the shared threadpool.
  This function itself is lightweight and safe to run as a Starlette BackgroundTask.
  """
  _EMOTION_EXECUTOR.submit(_background_analyze_emotion, task_id, user_id, music_file_id, local_path)


@router.post(
    "/analyze-task",
    response_model=EmotionTaskCreateResponse,
    summary="Upload audio and run emotion analysis (async task)",
)
async def analyze_emotion_task(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> EmotionTaskCreateResponse:
  if not file.content_type or not file.content_type.startswith("audio/"):
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="请选择音频文件")

  # Save file to disk
  upload_root = Path(settings.MEDIA_ROOT)
  upload_root.mkdir(parents=True, exist_ok=True)
  ext = Path(file.filename).suffix
  filename = f"{uuid4()}{ext}"
  filepath = upload_root / filename
  content = await file.read()
  filepath.write_bytes(content)

  # 上传到 OSS（存档），并记录存储路径
  stored_path = str(filepath)
  if settings.OSS_ENABLED:
    try:
      key = build_oss_key(
          category="music",
          source="upload",
          user_id=current_user.id,
          original_filename=file.filename,
      )
      OSSStorage().put_bytes(key, content, content_type=file.content_type)
      stored_path = encode_oss_path(key)
    except Exception as exc:
      print(f"[emotion/analyze-task] Upload to OSS failed, keep local path: {exc}")

  # Create music file record
  music_file = MusicFile(
      user_id=current_user.id,
      file_name=file.filename or filename,
      storage_path=stored_path,
      size_bytes=len(content),
      file_type=file.content_type,
  )
  db.add(music_file)
  db.flush()

  # 情绪分析计数
  current_user.emotion_detection_count = (current_user.emotion_detection_count or 0) + 1
  db.add(current_user)

  # Create async task
  task = tasks.create_task(
      db,
      user_id=current_user.id,
      task_type=TaskType.analyze_emotion,
      input_payload={
          "music_file_id": music_file.id,
          "filename": file.filename,
          "content_type": file.content_type,
          "stored_path": stored_path,
          "local_path": str(filepath),
      },
      auto_complete=False,
  )

  # Mark as processing early
  try:
    tasks.set_status(db, task.id, TaskStatus.processing)
  except Exception:
    pass

  background_tasks.add_task(_submit_emotion_job, task.id, current_user.id, music_file.id, str(filepath))

  # Commit music_file + user count changes
  db.commit()
  db.refresh(music_file)

  return EmotionTaskCreateResponse(
      task_id=task.id,
      status=TaskStatus.processing,
      music_file_id=music_file.id,
      audio_url=resolve_music_url(music_file),
  )


@router.get(
    "/analyze-task/{task_id}",
    response_model=TaskDetail,
    summary="Check emotion analysis task status",
)
async def get_emotion_analysis_task(task_id: str, db: Session = Depends(get_db)) -> TaskDetail:
  record = tasks.get_task(db, task_id, expected_type=TaskType.analyze_emotion)
  if not record:
    raise HTTPException(status_code=404, detail="Task not found")
  return tasks.to_task_detail(record)


@router.post(
    "/summary",
    response_model=EmotionSummaryResponse,
    summary="Generate AI summary for an emotion analysis result",
)
async def generate_emotion_summary(
    analysis: dict = Body(..., description="Emotion analysis JSON (from /emotion/analyze)"),
) -> EmotionSummaryResponse:
  """
  使用 LLM 根据情绪分析结果生成简短中文总结。
  如果未配置 OPENAI_API_KEY，则返回占位总结。
  """
  summary = await llm.summarize_emotion(analysis)
  if not summary:
    raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="生成总结失败")
  return EmotionSummaryResponse(summary=summary)
