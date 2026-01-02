from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel


class HistoryItem(BaseModel):
  id: int
  title: Optional[str] = None
  type: str  # "dialogue" 或 "emotion"
  created_at: datetime
  updated_at: datetime
  # 对话专用
  message_count: Optional[int] = None
  active: Optional[bool] = None
  # 情绪分析专用
  emotion: Optional[str] = None
  confidence: Optional[float] = None


class HistoryListResponse(BaseModel):
  total: int
  items: List[HistoryItem]


class DialogueMessageItem(BaseModel):
  id: int
  dialogue_id: int
  user_input: Optional[str] = None
  reply: Optional[str] = None
  message_order: Optional[int] = None
  created_at: datetime
  music_file_id: Optional[int] = None
  music_url: Optional[str] = None
  duration_seconds: Optional[int] = None
  file_name: Optional[str] = None
  cover_url: Optional[str] = None


class DialogueHistoryResponse(BaseModel):
  dialogue_id: int
  dialogue_title: Optional[str] = None
  type: str = "dialogue"
  total_messages: int
  messages: List[DialogueMessageItem]


class EmotionDetailResponse(BaseModel):
  id: int
  music_file_id: int
  emotion: Optional[str] = None
  confidence: Optional[float] = None
  raw_result: Optional[dict] = None
  created_at: datetime
  audio_url: Optional[str] = None
  summary: Optional[str] = None
  report_path: Optional[str] = None
  arousal_level: Optional[float] = None
