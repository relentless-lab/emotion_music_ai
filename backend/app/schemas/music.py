from typing import Optional

from pydantic import BaseModel, Field


class MusicGenerateRequest(BaseModel):
    prompt: str = Field(..., description="Natural language description of the desired music.")
    duration_seconds: Optional[int] = Field(None, ge=1, le=600, description="Optional length in seconds.")
    style: Optional[str] = Field(None, description="Target style/genre guidance.")
    model: Optional[str] = Field(None, description="Preferred generation model name or version.")
    instrumental: bool = Field(True, description="true=纯音乐；false=有人声/可带歌词")
    lyrics: Optional[str] = Field(None, description="歌词（vocal 场景使用；可选）")


class MusicGenerateResult(BaseModel):
    audio_url: str
    cover_url: Optional[str] = None
    format: str = "mp3"
    duration_seconds: Optional[int] = None
    prompt: Optional[str] = None
    notes: Optional[str] = None


class EmotionAnalysisResult(BaseModel):
    emotion: str
    confidence: float
    extra: Optional[dict] = None

