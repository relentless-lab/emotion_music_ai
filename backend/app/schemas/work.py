from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class WorkCreateRequest(BaseModel):
  # 兼容前端可能传的 id 字段；优先使用 music_file_id
  music_file_id: Optional[int] = Field(None, description="已生成的音乐文件 ID")
  id: Optional[int] = Field(None, description="兼容字段，等价于 music_file_id", alias="id")
  title: Optional[str] = Field(None, description="作品标题，不传则用文件名")
  description: Optional[str] = Field(None, description="作品描述")
  tags: Optional[str] = Field(None, description="逗号分隔的标签")
  visibility: Optional[str] = Field(None, description="public/unlisted/private，默认 public")
  mood: Optional[str] = Field(None, description="作品情绪/风格")
  cover_url: Optional[str] = Field(None, description="封面地址")
  status: Optional[str] = Field(None, description="draft/published，默认 draft")


class WorkUpdateRequest(BaseModel):
  title: Optional[str] = Field(None, description="作品标题")
  description: Optional[str] = Field(None, description="作品描述")
  tags: Optional[str] = Field(None, description="逗号分隔的标签")
  visibility: Optional[str] = Field(None, description="public/unlisted/private")
  mood: Optional[str] = Field(None, description="作品情绪/风格")
  cover_url: Optional[str] = Field(None, description="封面地址")
  status: Optional[str] = Field(None, description="draft/published")


class WorkResponse(BaseModel):
  id: int
  music_file_id: int
  name: str
  title: str
  description: Optional[str] = None
  tags: Optional[str] = None
  status: str
  visibility: str
  mood: Optional[str] = None
  cover_url: Optional[str] = None
  like_count: int
  play_count: int
  audio_url: Optional[str] = None
  created_at: datetime = Field(..., serialization_alias="createdAt")
  updated_at: datetime = Field(..., serialization_alias="updatedAt")
  published_at: Optional[datetime] = None


class WorkAuthor(BaseModel):
  id: int
  username: str
  avatar: Optional[str] = None
  followers: int = 0
  following: int = 0


class WorkPublicResponse(WorkResponse):
  author: WorkAuthor
  liked: bool = False


class WorkPlayRequest(BaseModel):
  source: Optional[str] = Field(None, description="播放来源（用于统计，最长 50 字符）")