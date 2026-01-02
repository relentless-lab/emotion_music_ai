from typing import List, Optional

from pydantic import BaseModel, Field


class ModelOption(BaseModel):
    name: str
    label: str
    type: str  # e.g., "generation" or "emotion"
    notes: Optional[str] = None


class UploadPolicy(BaseModel):
    max_size_mb: int
    accepted_types: List[str]
    max_duration_seconds: Optional[int] = None


class ClientConfig(BaseModel):
    generation_models: List[ModelOption]
    emotion_models: List[ModelOption]
    upload_policy: UploadPolicy
    features: List[str] = Field(default_factory=list)
