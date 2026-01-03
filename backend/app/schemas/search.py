from typing import Optional

from pydantic import BaseModel


class SongSearchResult(BaseModel):
  id: int
  title: str
  cover_url: Optional[str] = None
  # 用于前端直接播放（/static/... 或 OSS/直链）
  audio_url: Optional[str] = None
  like_count: int = 0
  play_count: int = 0
  tags: Optional[str] = None
  author_id: int
  author_name: str
  liked: bool = False


class UserSearchResult(BaseModel):
  id: int
  username: str
  avatar: Optional[str] = None
  bio: Optional[str] = None
  followers: int = 0
  following: int = 0
  is_followed: bool = False


class SearchResponse(BaseModel):
  query: str
  songs: list[SongSearchResult]
  users: list[UserSearchResult]
