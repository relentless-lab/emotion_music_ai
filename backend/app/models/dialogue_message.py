from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, Text
from sqlalchemy.orm import relationship

from app.db.base_class import Base


class DialogueMessage(Base):
  __tablename__ = "dialogue_messages"

  id = Column(Integer, primary_key=True, autoincrement=True)
  dialogue_id = Column(ForeignKey("dialogues.id"), nullable=False, index=True)
  music_file_id = Column(ForeignKey("music_files.id"), nullable=True, index=True)
  user_input_text = Column(Text, nullable=True)
  system_reply_text = Column(Text, nullable=True)
  message_order = Column(Integer, nullable=True)
  created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

  dialogue = relationship("Dialogue", back_populates="messages")
  music_file = relationship("MusicFile", back_populates="messages")
