from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional

from pydantic import BaseModel


class TaskStatus(str, Enum):
    pending = "pending"
    processing = "processing"
    completed = "completed"
    failed = "failed"


class TaskType(str, Enum):
    generate_music = "generate_music"
    analyze_emotion = "analyze_emotion"


class TaskCreateResponse(BaseModel):
    task_id: str
    status: TaskStatus


class TaskBase(BaseModel):
    id: str
    type: TaskType
    status: TaskStatus
    created_at: datetime
    updated_at: datetime
    message: Optional[str] = None


class TaskDetail(TaskBase):
    input: Optional[Dict[str, Any]] = None
    result: Optional[Dict[str, Any]] = None


class TaskListResponse(BaseModel):
    items: list[TaskBase]

