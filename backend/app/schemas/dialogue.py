from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field
from app.schemas.tasks import TaskStatus


class DialogueMessageRequest(BaseModel):
  dialogue_id: Optional[int] = Field(None, description="Existing dialogue ID to continue the conversation.")
  message: str = Field(..., min_length=1, max_length=4000, description="User input text.")
  title: Optional[str] = Field(None, description="Optional title for a new dialogue.")
  duration_seconds: Optional[float] = Field(
      None, ge=1.0, le=600.0, description="Optional music duration (seconds) for chat-generate."
  )
  cover_url: Optional[str] = Field(None, description="Pre-generated cover URL to avoid re-generation.")

  # --- SongGeneration(full-new) 扩展字段（保持向后兼容）---
  instrumental: bool = Field(True, description="true=纯音乐；false=有人声/可带歌词")
  lyrics: Optional[str] = Field(None, description="歌词（vocal 场景使用；可空，空则回退到 message）")
  style: Optional[str] = Field(None, description="风格标签（如 'female, sad, piano, pop'；可选）")


class CoverGenerateResponse(BaseModel):
  cover_url: str
  prompt: str


class DialogueTaskCreateResponse(BaseModel):
  """Async generation task creation response."""
  task_id: str
  status: TaskStatus
  dialogue_id: int


class DialogueMessageResponse(BaseModel):
  dialogue_id: int
  message_id: int
  user_input: str
  reply: str
  message_order: Optional[int] = None
  dialogue_title: Optional[str] = None
  created_at: datetime


class DialogueMusicResponse(DialogueMessageResponse):
  music_url: str
  format: str = "wav"
  duration_seconds: Optional[int] = None
  music_file_id: Optional[int] = None
  cover_url: Optional[str] = None
