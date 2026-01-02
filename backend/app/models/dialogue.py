from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from app.db.base_class import Base


class Dialogue(Base):
  __tablename__ = "dialogues"

  id = Column(Integer, primary_key=True, autoincrement=True)
  user_id = Column(ForeignKey("users.id"), nullable=False, index=True)
  title = Column(String(200), nullable=True)
  message_count = Column(Integer, nullable=False, default=0)
  active = Column(Boolean, nullable=False, default=True)
  created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
  updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

  user = relationship("User", back_populates="dialogues")
  messages = relationship("DialogueMessage", back_populates="dialogue", cascade="all, delete-orphan")
  music_files = relationship("MusicFile", back_populates="dialogue", cascade="all, delete-orphan")
