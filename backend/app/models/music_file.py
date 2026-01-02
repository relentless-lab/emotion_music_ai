from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from app.db.base_class import Base


class MusicFile(Base):
  __tablename__ = "music_files"

  id = Column(Integer, primary_key=True, autoincrement=True)
  user_id = Column(ForeignKey("users.id"), nullable=False, index=True)
  dialogue_id = Column(ForeignKey("dialogues.id"), nullable=True, index=True)
  file_name = Column(String(255), nullable=False)
  storage_path = Column(String(500), nullable=False)
  # 相对路径形式的专辑封面图片（如 "/static/covers/xxx.png"）
  cover_image_path = Column(String(500), nullable=True)
  size_bytes = Column(Integer, nullable=True)
  file_type = Column(String(20), nullable=True)
  source_type = Column(String(20), nullable=False, default="upload")
  duration_seconds = Column(Integer, nullable=True)
  created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

  user = relationship("User", back_populates="music_files")
  dialogue = relationship("Dialogue", back_populates="music_files")
  analysis = relationship("EmotionAnalysis", back_populates="music_file", uselist=False)
  messages = relationship("DialogueMessage", back_populates="music_file")
  work = relationship("Work", back_populates="music_file", uselist=False)
