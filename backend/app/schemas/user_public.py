from typing import List, Optional

from pydantic import BaseModel

from app.schemas.work import WorkPublicResponse


class PublicUser(BaseModel):
  id: int
  username: str
  avatar: Optional[str] = None
  bio: Optional[str] = None
  followers: int = 0
  following: int = 0
  likesReceived: int = 0
  playsThisMonth: int = 0
  likedSongs: int = 0
  generations: int = 0
  emotionDetections: int = 0
  works: int = 0
  is_followed: bool = False


class PublicUserProfile(BaseModel):
  user: PublicUser
  works: List[WorkPublicResponse] = []
  liked_songs: List[WorkPublicResponse] = []
