from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Index

from app.db.base_class import Base


class WorkPlayLog(Base):
  __tablename__ = "work_play_logs"

  id = Column(Integer, primary_key=True, autoincrement=True)
  user_id = Column(ForeignKey("users.id"), nullable=True, index=True)
  work_id = Column(ForeignKey("works.id"), nullable=False, index=True)
  played_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
  source = Column(String(50), nullable=True)


# Helpful composite indexes (Alembic creates them via __table_args__ is easier to reason about)
Index("ix_work_play_logs_work_time", WorkPlayLog.work_id, WorkPlayLog.played_at)
