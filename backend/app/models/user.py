from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String, Text
from sqlalchemy.orm import relationship

from app.db.base_class import Base


class User(Base):
  __tablename__ = "users"

  id = Column(Integer, primary_key=True, autoincrement=True)
  username = Column(String(50), nullable=False, unique=True, index=True)
  email = Column(String(100), nullable=True, unique=True, index=True)
  password_hash = Column(String(255), nullable=False)
  avatar = Column(String(255), nullable=True)
  personal_profile = Column(Text, nullable=True)
  following_count = Column(Integer, nullable=False, default=0)
  followers_count = Column(Integer, nullable=False, default=0)
  total_likes = Column(Integer, nullable=False, default=0)
  total_generations = Column(Integer, nullable=False, default=0)
  total_works = Column(Integer, nullable=False, default=0)
  emotion_detection_count = Column(Integer, nullable=False, default=0)
  plays_received = Column(Integer, nullable=False, default=0)
  plays_this_month = Column(Integer, nullable=False, default=0)
  liked_works_count = Column(Integer, nullable=False, default=0)
  created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
  last_login = Column(DateTime, nullable=True)

  tasks = relationship("TaskRecord", back_populates="user")
  dialogues = relationship("Dialogue", back_populates="user")
  music_files = relationship("MusicFile", back_populates="user")
  emotion_analyses = relationship("EmotionAnalysis", back_populates="user")
  works = relationship("Work", back_populates="user")
  likes = relationship("LikeRecord", back_populates="user")
  following = relationship("UserFollower", foreign_keys="UserFollower.follower_id", back_populates="follower")
  followers = relationship("UserFollower", foreign_keys="UserFollower.following_id", back_populates="following")
