from datetime import datetime
from enum import Enum

from sqlalchemy import Column, DateTime, Enum as SAEnum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.db.base_class import Base


class WorkStatus(str, Enum):
  draft = "draft"
  published = "published"


class WorkVisibility(str, Enum):
  public = "public"
  unlisted = "unlisted"
  private = "private"


class Work(Base):
  __tablename__ = "works"

  id = Column(Integer, primary_key=True, autoincrement=True)
  user_id = Column(ForeignKey("users.id"), nullable=False, index=True)
  music_file_id = Column(ForeignKey("music_files.id"), nullable=False, index=True)
  title = Column(String(255), nullable=False)
  description = Column(Text, nullable=True)
  tags = Column(String(255), nullable=True)
  status = Column(SAEnum(WorkStatus), nullable=False, default=WorkStatus.draft)
  visibility = Column(SAEnum(WorkVisibility), nullable=False, default=WorkVisibility.public)
  mood = Column(String(100), nullable=True)
  cover_url = Column(String(255), nullable=True)
  like_count = Column(Integer, nullable=False, default=0)
  play_count = Column(Integer, nullable=False, default=0)
  created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
  updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
  published_at = Column(DateTime, nullable=True)

  user = relationship("User", back_populates="works")
  music_file = relationship("MusicFile", back_populates="work")
  likes = relationship("LikeRecord", back_populates="work", cascade="all, delete-orphan")
