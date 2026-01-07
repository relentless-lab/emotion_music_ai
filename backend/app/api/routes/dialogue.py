from datetime import datetime
import asyncio
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError, OperationalError, PendingRollbackError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.dependencies import get_current_user, get_db
from app.db.session import SessionLocal
from app.models.dialogue import Dialogue
from app.models.dialogue_message import DialogueMessage
from app.models.music_file import MusicFile
from app.models.user import User
from app.schemas.dialogue import DialogueMessageRequest, DialogueMessageResponse, DialogueMusicResponse, CoverGenerateResponse, DialogueTaskCreateResponse
from app.schemas.tasks import TaskType, TaskStatus
from app.services import generation_service
from app.services import llm as llm_service
from app.services import image_service
from app.services import tasks as task_service
from app.services.oss_storage import OSSStorage, build_oss_key, encode_oss_path, normalize_oss_like_url
from app.services.url_resolver import resolve_music_url, resolve_cover_url
from app.services.file_cleanup import delete_file_best_effort

router = APIRouter()


def _ensure_db_connection(db: Session) -> None:
  """
  Ping the database before doing writes; if the connection was dropped during
  the long music generation step, this will force SQLAlchemy to reconnect.
  """
  try:
    db.execute(text("SELECT 1"))
  except (OperationalError, PendingRollbackError):
    db.rollback()
    db.execute(text("SELECT 1"))


@router.post(
    "/chat-generate",
    response_model=DialogueMessageResponse,
    summary="Send a dialogue message and get AI reply",
)
async def chat(
    payload: DialogueMessageRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DialogueMessageResponse:
  if payload.dialogue_id:
    dialogue = (
        db.query(Dialogue)
        .filter(Dialogue.id == payload.dialogue_id, Dialogue.user_id == current_user.id)
        .first()
    )
    if not dialogue:
      raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="未找到对话")
    if not dialogue.active:
      raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="对话已关闭")
  else:
    title = payload.title or payload.message[:50]
    dialogue = Dialogue(user_id=current_user.id, title=title or "新的对话")
    db.add(dialogue)
    db.flush()

  existing_count = (
      db.query(DialogueMessage).filter(DialogueMessage.dialogue_id == dialogue.id).count()
  )
  reply_text = "ai功能尚未实现"
  message = DialogueMessage(
      dialogue_id=dialogue.id,
      user_input_text=payload.message,
      system_reply_text=reply_text,
      message_order=existing_count + 1,
  )

  dialogue.message_count = existing_count + 1
  dialogue.updated_at = datetime.utcnow()
  if not dialogue.title:
    dialogue.title = payload.message[:50]

  db.add(message)
  db.add(dialogue)
  db.commit()
  db.refresh(dialogue)
  db.refresh(message)

  return DialogueMessageResponse(
      dialogue_id=dialogue.id,
      message_id=message.id,
      user_input=message.user_input_text or "",
      reply=message.system_reply_text or "",
      message_order=message.message_order,
      dialogue_title=dialogue.title,
      created_at=message.created_at,
  )


@router.post(
    "/generate-cover",
    response_model=CoverGenerateResponse,
    summary="Generate a music cover based on prompt",
)
async def generate_cover(
    payload: DialogueMessageRequest,
    current_user: User = Depends(get_current_user),
) -> CoverGenerateResponse:
    """仅生成专辑封面，用于前端提前展示。"""
    try:
        cover_prompt = await llm_service.build_album_cover_prompt(payload.message)
        cover_path = await image_service.generate_album_cover_image(
            cover_prompt, user_id=current_user.id
        )
        cover_url = resolve_cover_url(cover_path)
        if not cover_url:
            raise HTTPException(status_code=500, detail="生成封面失败")
        return CoverGenerateResponse(cover_url=cover_url, prompt=payload.message)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"生成封面失败: {exc}")


def _background_chat_and_generate(
    task_id: str,
    payload: DialogueMessageRequest,
    user_id: int,
    dialogue_id: int,
    message_id: int | None,
):
    """Background task to handle long-running music generation."""
    db = SessionLocal()
    try:
        print(f"[dialogue/background] start task_id={task_id} dialogue_id={dialogue_id} user_id={user_id}")
        # Mark processing (best-effort)
        try:
            task_service.set_status(db, task_id, TaskStatus.processing)
        except Exception:
            pass

        # Re-fetch objects in this session
        current_user = db.query(User).filter(User.id == user_id).first()
        dialogue = db.query(Dialogue).filter(Dialogue.id == dialogue_id).first()
        placeholder_message = None
        if message_id:
            placeholder_message = (
                db.query(DialogueMessage)
                .filter(DialogueMessage.id == message_id, DialogueMessage.dialogue_id == dialogue_id)
                .first()
            )
        
        if not current_user or not dialogue:
            task_service.fail_task(db, task_id, "User or Dialogue not found")
            return
        if message_id and not placeholder_message:
            task_service.fail_task(db, task_id, "DialogueMessage not found")
            return

        reply_text = f"收到你的描述：{payload.message}。我为你生成了一段对应氛围的音乐，请试听。"
        # 默认时长改为更“完整”的段落长度（用户侧不再强依赖手动选择时长）
        duration = float(payload.duration_seconds) if payload.duration_seconds else 120.0

        # Generate a nicer title (Suno-like) and persist to dialogue title if missing.
        try:
            generated_title = asyncio.run(llm_service.build_music_title(payload.message))
        except Exception:
            generated_title = (payload.message or "").strip()[:12] or "AI 生成作品"

        if generated_title:
            try:
                # Only overwrite when empty / generic
                if not dialogue.title or dialogue.title.strip() in {"新的对话", "音乐创作对话"}:
                    dialogue.title = generated_title
                    db.add(dialogue)
            except Exception:
                pass

        # 1. Generate music
        gen_result = generation_service.generate_music_file(
            prompt_zh=payload.message,
            duration_sec=duration,
            model_name="songgen_full_new" if settings.SONGGEN_REMOTE_URL else "musicgen_pretrained",
            instrumental=bool(getattr(payload, "instrumental", True)),
            lyrics=getattr(payload, "lyrics", None),
            style=getattr(payload, "style", None),
        )

        # 2. Upload to OSS
        audio_abs = Path(gen_result.rel_path)
        if not audio_abs.is_absolute():
            audio_abs = Path.cwd() / audio_abs
        stored_path = str(audio_abs)
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
                # 可选：上传成功后清理本地缓存文件
                if getattr(settings, "DELETE_LOCAL_AUDIO_AFTER_OSS_UPLOAD", False):
                    ok = delete_file_best_effort(audio_abs)
                    if ok:
                        print(f"[dialogue/background] Deleted local audio cache: {audio_abs}")
            except Exception as exc:
                print(f"[dialogue/background] Upload failed: {exc}")

        # 3. Cover handling
        cover_rel_path = None
        if payload.cover_url:
            cover_rel_path = normalize_oss_like_url(payload.cover_url)
        else:
            try:
                cover_prompt = asyncio.run(llm_service.build_album_cover_prompt(payload.message))
                cover_path = asyncio.run(image_service.generate_album_cover_image(cover_prompt, user_id=current_user.id))
                cover_rel_path = cover_path
            except Exception as exc:
                print(f"[dialogue/background] Cover failed: {exc}")

        # 4. Save to DB
        # 生成/上传/封面阶段耗时很久，DB 连接可能被 MySQL 断开，这里先 ping 一下以便自动重连
        try:
            _ensure_db_connection(db)
        except Exception:
            # best-effort; if still broken, we'll handle on commit/fail below
            pass

        music_file = MusicFile(
            user_id=current_user.id,
            dialogue=dialogue,
            file_name=gen_result.filename,
            storage_path=stored_path,
            size_bytes=audio_abs.stat().st_size if audio_abs.exists() else None,
            file_type="audio/wav",
            source_type="generated",
            duration_seconds=int(gen_result.duration_sec),
            cover_image_path=cover_rel_path,
        )
        db.add(music_file)

        # Prefer updating the placeholder message created at task submission time.
        # This ensures History can show "生成中..." immediately instead of being empty.
        if placeholder_message is None:
            existing_count = db.query(DialogueMessage).filter(DialogueMessage.dialogue_id == dialogue.id).count()
            message = DialogueMessage(
                dialogue=dialogue,
                user_input_text=payload.message,
                system_reply_text=reply_text,
                message_order=existing_count + 1,
            )
        else:
            message = placeholder_message
            message.user_input_text = payload.message
            message.system_reply_text = reply_text

        message.music_file = music_file
        db.add(message)

        dialogue.updated_at = datetime.utcnow()
        current_user.total_generations = (current_user.total_generations or 0) + 1
        # Ensure message_count not decreased
        try:
            dialogue.message_count = max(int(dialogue.message_count or 0), int(message.message_order or 0))
        except Exception:
            pass
        
        try:
            db.commit()
        except (OperationalError, PendingRollbackError) as exc:
            # Retry once after forcing reconnect.
            try:
                db.rollback()
            except Exception:
                pass
            try:
                _ensure_db_connection(db)
                db.commit()
            except Exception:
                raise exc
        
        # 5. Complete task with result for frontend to poll
        result = {
            "id": music_file.id,
            "music_file_id": music_file.id,
            "title": generated_title or dialogue.title or (payload.message or "")[:12] or "AI 生成作品",
            "artist": "AI Composer",
            "url": resolve_music_url(music_file),
            "duration": music_file.duration_seconds,
            "cover": resolve_cover_url(music_file.cover_image_path),
            "dialogue_id": dialogue.id,
            "message_id": message.id,
            "reply": reply_text
        }
        try:
            # Best-effort reconnect before updating task row too
            _ensure_db_connection(db)
        except Exception:
            pass
        task_service.complete_task(db, task_id, result=result)
        print(f"[dialogue/background] completed task_id={task_id} music_file_id={music_file.id}")

    except Exception as exc:
        print(f"[dialogue/background] Critical error: {exc}")
        # Best-effort: update placeholder message so History doesn't look empty.
        try:
            if message_id:
                try:
                    _ensure_db_connection(db)
                except Exception:
                    pass
                msg = (
                    db.query(DialogueMessage)
                    .filter(DialogueMessage.id == message_id, DialogueMessage.dialogue_id == dialogue_id)
                    .first()
                )
                if msg:
                    msg.system_reply_text = f"生成失败：{exc}"
                    db.add(msg)
                    db.commit()
        except Exception:
            try:
                db.rollback()
            except Exception:
                pass
        # Best-effort: task 标记失败（即使当前连接已断开，也尝试用新连接写回）
        try:
            try:
                _ensure_db_connection(db)
            except Exception:
                pass
            task_service.fail_task(db, task_id, str(exc))
        except Exception:
            try:
                db.close()
            except Exception:
                pass
            db2 = SessionLocal()
            try:
                task_service.fail_task(db2, task_id, str(exc))
            finally:
                db2.close()
    finally:
        db.close()


@router.post("/chat-task", response_model=DialogueTaskCreateResponse)
async def chat_async(
    payload: DialogueMessageRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Async version of chat_and_generate that returns a taskId immediately."""
    if payload.dialogue_id:
        dialogue = db.query(Dialogue).filter(Dialogue.id == payload.dialogue_id, Dialogue.user_id == current_user.id).first()
        if not dialogue:
            raise HTTPException(status_code=404, detail="未找到对话")
    else:
        # Do NOT default title to user prompt; we'll generate a nicer title later (Suno-like).
        dialogue = Dialogue(user_id=current_user.id, title=payload.title or None)
        db.add(dialogue)
        db.commit()
        db.refresh(dialogue)

    existing_count = db.query(DialogueMessage).filter(DialogueMessage.dialogue_id == dialogue.id).count()

    # Create async task
    task = task_service.create_task(
        db,
        user_id=current_user.id,
        task_type=TaskType.generate_music,
        input_payload=payload.model_dump(),
        auto_complete=False
    )

    # Mark as processing early so polling UI can show correct status
    try:
        task_service.set_status(db, task.id, TaskStatus.processing)
    except Exception:
        pass

    # Create a placeholder dialogue message immediately so History is not empty while generating.
    placeholder = DialogueMessage(
        dialogue_id=dialogue.id,
        user_input_text=payload.message,
        system_reply_text="正在为您精心编排旋律，请稍候...",
        message_order=existing_count + 1,
    )
    try:
        dialogue.message_count = max(int(dialogue.message_count or 0), existing_count + 1)
    except Exception:
        dialogue.message_count = existing_count + 1
    dialogue.updated_at = datetime.utcnow()
    db.add(placeholder)
    db.add(dialogue)
    db.commit()
    db.refresh(placeholder)

    # Dispatch background task
    background_tasks.add_task(
        _background_chat_and_generate,
        task.id, payload, current_user.id, dialogue.id, placeholder.id
    )

    return DialogueTaskCreateResponse(
        task_id=task.id,
        status=task.status,
        dialogue_id=dialogue.id
    )


@router.post(
    "/chat",
    response_model=DialogueMusicResponse,
    summary="Chat and generate music from the user message",
)
async def chat_and_generate(
  payload: DialogueMessageRequest,
  db: Session = Depends(get_db),
  current_user: User = Depends(get_current_user),
) -> DialogueMusicResponse:
  """用户发一段话，回复一段话并生成音乐文件返回 URL，同时保存音乐记录。"""
  # 先确保对话记录已持久化，避免长时间生成过程中连接断开导致外键丢失
  if payload.dialogue_id:
    dialogue = (
        db.query(Dialogue)
        .filter(Dialogue.id == payload.dialogue_id, Dialogue.user_id == current_user.id)
        .first()
    )
    if not dialogue:
      raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="未找到对话")
    if not dialogue.active:
      raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="对话已关闭")
  else:
    title = payload.title or payload.message[:50]
    dialogue = Dialogue(user_id=current_user.id, title=title or "新的对话")
    db.add(dialogue)
    db.commit()
    db.refresh(dialogue)

  existing_count = (
      db.query(DialogueMessage).filter(DialogueMessage.dialogue_id == dialogue.id).count()
  )

  # 简单回复逻辑，可后续替换为真实 LLM
  reply_text = f"收到你的描述：{payload.message}。我为你生成了一段对应氛围的音乐，请试听。"

  # 默认时长改为更“完整”的段落长度（用户侧不再强依赖手动选择时长）
  duration = float(payload.duration_seconds) if payload.duration_seconds else 120.0

  # 1. 先生成音乐
  try:
    gen_result = generation_service.generate_music_file(
        prompt_zh=payload.message,
        duration_sec=duration,
        model_name="songgen_full_new" if settings.SONGGEN_REMOTE_URL else "musicgen_pretrained",
        instrumental=bool(getattr(payload, "instrumental", True)),
        lyrics=getattr(payload, "lyrics", None),
        style=getattr(payload, "style", None),
    )
  except Exception as exc:
    raise HTTPException(status_code=500, detail=f"生成音乐失败: {exc}") from exc

  # 上传生成音频到 OSS（generated）
  audio_abs = Path(gen_result.rel_path)
  if not audio_abs.is_absolute():
    audio_abs = Path.cwd() / audio_abs
  stored_path = str(audio_abs)
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
      print(f"[dialogue/chat] Uploaded generated audio to OSS key={key}")
      if getattr(settings, "DELETE_LOCAL_AUDIO_AFTER_OSS_UPLOAD", False):
        ok = delete_file_best_effort(audio_abs)
        if ok:
          print(f"[dialogue/chat] Deleted local audio cache: {audio_abs}")
    except Exception as exc:
      print(f"[dialogue/chat] Upload generated audio to OSS failed, keep local: {exc}")

  # 2. 封面处理：如果前端传了 cover_url，则直接用；否则生成
  cover_rel_path: str | None = None
  if payload.cover_url:
      # 尝试从传来的 URL 还原回相对路径或 OSS 路径
      cover_rel_path = normalize_oss_like_url(payload.cover_url)
  else:
      try:
        cover_prompt = await llm_service.build_album_cover_prompt(payload.message)
        cover_path = await image_service.generate_album_cover_image(
            cover_prompt, user_id=current_user.id
        )
        if cover_path:
          cover_rel_path = cover_path
      except Exception as exc:
        import traceback
        print(f"[dialogue/chat] cover generation failed: {exc}\n{traceback.format_exc()}")
        cover_rel_path = None

  # 生成步骤耗时较长，MySQL 连接可能被远端关闭，这里先 ping 一下以便自动重连
  _ensure_db_connection(db)

  try:
    # 生成耗时较长：对话可能被其它请求删除/关闭；这里重新校验一次，避免外键失败
    dialogue_id = int(dialogue.id)
    dialogue = (
        db.query(Dialogue)
        .filter(Dialogue.id == dialogue_id, Dialogue.user_id == current_user.id)
        .first()
    )
    if not dialogue:
      raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="对话不存在或已被删除，请重新开始对话")
    if not dialogue.active:
      raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="对话已关闭")

    # 保存音乐文件记录
    audio_path = audio_abs
    size_bytes = audio_path.stat().st_size if audio_path.exists() else None

    music_file = MusicFile(
        user_id=current_user.id,
        dialogue=dialogue,
        file_name=gen_result.filename,
        storage_path=stored_path,
        size_bytes=size_bytes,
        file_type="audio/wav",
        source_type="generated",
        duration_seconds=int(gen_result.duration_sec),
        cover_image_path=cover_rel_path,
    )
    db.add(music_file)

    message = DialogueMessage(
        dialogue=dialogue,
        music_file=music_file,
        user_input_text=payload.message,
        system_reply_text=reply_text,
        message_order=existing_count + 1,
    )

    dialogue.message_count = existing_count + 1
    dialogue.updated_at = datetime.utcnow()
    if not dialogue.title:
      dialogue.title = payload.message[:50]

    current_user.total_generations = (current_user.total_generations or 0) + 1

    db.add(message)
    db.add(dialogue)
    db.add(current_user)
    # Flush once to allocate IDs (useful for response payload) before commit.
    db.flush()
    db.commit()
    db.refresh(dialogue)
    db.refresh(message)
    db.refresh(music_file)
  except IntegrityError as exc:
    db.rollback()
    # Common MySQL FK error: parent dialogue missing (1452).
    if "foreign key constraint fails" in str(exc).lower() and "music_files" in str(exc).lower():
      raise HTTPException(
          status_code=status.HTTP_409_CONFLICT,
          detail="写入失败：对话记录不存在（可能已被删除或数据库不一致）。请刷新后重试或新建对话。",
      ) from exc
    raise
  except Exception:
    db.rollback()
    raise

  music_url = resolve_music_url(music_file)
  cover_url = resolve_cover_url(cover_rel_path)

  return DialogueMusicResponse(
      dialogue_id=dialogue.id,
      message_id=message.id,
      user_input=message.user_input_text or "",
      reply=message.system_reply_text or "",
      message_order=message.message_order,
      dialogue_title=dialogue.title,
      created_at=message.created_at,
      music_url=music_url,
      format="wav",
      duration_seconds=int(gen_result.duration_sec),
      music_file_id=music_file.id,
      cover_url=cover_url,
  )
