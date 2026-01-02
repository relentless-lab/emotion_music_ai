from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel

from app.schemas.tasks import TaskStatus


class EmotionAnalysisResponse(BaseModel):
  analysis_id: int
  music_file_id: int
  emotion: str
  confidence: float
  extra: Optional[Dict[str, Any]] = None
  summary: Optional[str] = None
  created_at: datetime


class EmotionSummaryResponse(BaseModel):
  summary: str


class EmotionTaskCreateResponse(BaseModel):
  task_id: str
  status: TaskStatus
  music_file_id: int
  audio_url: Optional[str] = None
