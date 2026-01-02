from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, JSON, Numeric, String, Text
from sqlalchemy.orm import relationship

from app.db.base_class import Base


class EmotionAnalysis(Base):
  __tablename__ = "emotion_analysis"

  id = Column(Integer, primary_key=True, autoincrement=True)
  music_file_id = Column(ForeignKey("music_files.id"), nullable=False, index=True)
  user_id = Column(ForeignKey("users.id"), nullable=False, index=True)
  main_emotion = Column(String(50), nullable=True)
  emotion_intensity = Column(Numeric(5, 2), nullable=True)
  arousal_level = Column(Numeric(5, 2), nullable=True)
  raw_result = Column(JSON, nullable=True)
  report_path = Column(String(500), nullable=True)
  created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

  music_file = relationship("MusicFile", back_populates="analysis")
  user = relationship("User", back_populates="emotion_analyses")
