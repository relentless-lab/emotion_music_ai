from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, UniqueConstraint
from sqlalchemy.orm import relationship

from app.db.base_class import Base


class LikeRecord(Base):
  __tablename__ = "like_records"
  __table_args__ = (
      UniqueConstraint("user_id", "work_id", name="uq_user_work_like"),
  )

  id = Column(Integer, primary_key=True, autoincrement=True)
  user_id = Column(ForeignKey("users.id"), nullable=False, index=True)
  work_id = Column(ForeignKey("works.id"), nullable=False, index=True)
  created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

  user = relationship("User", back_populates="likes")
  work = relationship("Work", back_populates="likes")
