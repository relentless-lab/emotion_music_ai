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


class HotSongItem(BaseModel):
    id: int
    title: str
    author_name: Optional[str] = None
    cover_url: Optional[str] = None
    audio_url: Optional[str] = None
    like_count: int = 0
    play_count: int = 0
    tags: Optional[str] = None
    mood: Optional[str] = None


class RecommendedCreatorItem(BaseModel):
    id: int
    name: str
    followers: str
    handle: str
    avatar: Optional[str] = None