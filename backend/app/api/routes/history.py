from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user, get_db
from app.models.dialogue import Dialogue
from app.models.dialogue_message import DialogueMessage
from app.models.emotion_analysis import EmotionAnalysis
from app.models.user import User
from app.schemas.history import DialogueHistoryResponse, DialogueMessageItem, EmotionDetailResponse, HistoryItem, HistoryListResponse
from app.services.url_resolver import resolve_music_url, resolve_cover_url

router = APIRouter()


@router.get(
    "",
    response_model=HistoryListResponse,
    summary="List dialogues and emotion analyses for current user",
)
async def list_history(
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> HistoryListResponse:
  if limit < 1 or limit > 200:
    raise HTTPException(status_code=400, detail="limit 需在 1-200 之间")
  if offset < 0:
    raise HTTPException(status_code=400, detail="offset 不能为负数")

  # 对话列表
  dialogues = (
      db.query(Dialogue)
      .filter(Dialogue.user_id == current_user.id)
      .order_by(Dialogue.updated_at.desc())
      .all()
  )

  # 情绪分析列表
  emotions = (
      db.query(EmotionAnalysis)
      .filter(EmotionAnalysis.user_id == current_user.id)
      .order_by(EmotionAnalysis.created_at.desc())
      .all()
  )

  merged = []
  for d in dialogues:
    merged.append(
        {
            "type": "dialogue",
            "id": d.id,
            "title": d.title,
            "message_count": d.message_count,
            "active": d.active,
            "created_at": d.created_at,
            "updated_at": d.updated_at,
        }
    )

  for e in emotions:
    merged.append(
        {
            "type": "emotion",
            "id": e.id,
            "title": e.main_emotion or "emotion",
            "emotion": e.main_emotion,
            "confidence": float(e.emotion_intensity) if e.emotion_intensity is not None else None,
            "created_at": e.created_at,
            "updated_at": e.created_at,
        }
    )

  merged_sorted = sorted(merged, key=lambda x: x["updated_at"], reverse=True)
  total = len(merged_sorted)
  sliced = merged_sorted[offset : offset + limit]

  return HistoryListResponse(
      total=total,
      items=[HistoryItem(**item) for item in sliced],
  )


@router.get(
    "/dialogues/{dialogue_id}",
    response_model=DialogueHistoryResponse,
    summary="Get dialogue history for current user",
)
async def get_dialogue_history(
    dialogue_id: int,
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DialogueHistoryResponse:
  if limit < 1 or limit > 200:
    raise HTTPException(status_code=400, detail="limit 需在 1-200 之间")
  if offset < 0:
    raise HTTPException(status_code=400, detail="offset 不能为负数")

  dialogue = (
      db.query(Dialogue)
      .filter(Dialogue.id == dialogue_id, Dialogue.user_id == current_user.id)
      .first()
  )
  if not dialogue:
    raise HTTPException(status_code=404, detail="未找到对话")

  messages_query = (
      db.query(DialogueMessage)
      .filter(DialogueMessage.dialogue_id == dialogue.id)
      .order_by(DialogueMessage.message_order.asc())
  )
  total = messages_query.count()
  messages = messages_query.offset(offset).limit(limit).all()

  return DialogueHistoryResponse(
      dialogue_id=dialogue.id,
      dialogue_title=dialogue.title,
      type="dialogue",
      total_messages=total,
      messages=[
          DialogueMessageItem(
              id=m.id,
              dialogue_id=m.dialogue_id,
              user_input=m.user_input_text,
              reply=m.system_reply_text,
              message_order=m.message_order,
              created_at=m.created_at,
              music_file_id=m.music_file_id,
              music_url=resolve_music_url(m.music_file),
              duration_seconds=getattr(m.music_file, "duration_seconds", None),
              file_name=m.music_file.file_name if m.music_file else None,
              cover_url=(
                  resolve_cover_url(m.music_file.cover_image_path)
                  if m.music_file and getattr(m.music_file, "cover_image_path", None)
                  else None
              ),
          )
          for m in messages
      ],
  )


@router.get(
    "/emotions/{analysis_id}",
    response_model=EmotionDetailResponse,
    summary="Get emotion analysis detail for current user",
)
async def get_emotion_detail(
    analysis_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> EmotionDetailResponse:
  analysis = (
      db.query(EmotionAnalysis)
      .filter(EmotionAnalysis.id == analysis_id, EmotionAnalysis.user_id == current_user.id)
      .first()
  )
  if not analysis:
    raise HTTPException(status_code=404, detail="未找到情绪分析记录")

  music_file = analysis.music_file
  audio_url = resolve_music_url(music_file)
  raw_result = analysis.raw_result or {}
  summary = None
  if isinstance(raw_result, dict):
    summary = raw_result.get("summary") or raw_result.get("extra", {}).get("summary")

  return EmotionDetailResponse(
      id=analysis.id,
      music_file_id=analysis.music_file_id,
      emotion=analysis.main_emotion,
      confidence=float(analysis.emotion_intensity) if analysis.emotion_intensity is not None else None,
      raw_result=analysis.raw_result,
      created_at=analysis.created_at,
      audio_url=audio_url,
      summary=summary,
      report_path=analysis.report_path,
      arousal_level=float(analysis.arousal_level) if analysis.arousal_level is not None else None,
  )
