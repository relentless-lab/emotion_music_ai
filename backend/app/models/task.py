from datetime import datetime

from sqlalchemy import Column, DateTime, Enum, ForeignKey, JSON, String, Text
from sqlalchemy.orm import relationship

from app.db.base_class import Base
from app.schemas.tasks import TaskStatus, TaskType


class TaskRecord(Base):
  __tablename__ = "tasks"

  id = Column(String(36), primary_key=True)  # UUID str
  user_id = Column(ForeignKey("users.id"), nullable=True, index=True)
  type = Column(Enum(TaskType), nullable=False)
  status = Column(Enum(TaskStatus), nullable=False, default=TaskStatus.pending)
  input = Column(JSON, nullable=True)
  result = Column(JSON, nullable=True)
  message = Column(Text, nullable=True)
  created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
  updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

  user = relationship("User", back_populates="tasks")
