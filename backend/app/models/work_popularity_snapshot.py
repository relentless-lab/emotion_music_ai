from datetime import datetime

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer

from app.db.base_class import Base


class WorkPopularitySnapshot(Base):
  __tablename__ = "work_popularity_snapshots"

  id = Column(Integer, primary_key=True, autoincrement=True)
  work_id = Column(ForeignKey("works.id"), nullable=False, index=True)
  window_days = Column(Integer, nullable=False, default=3)
  start_time = Column(DateTime, nullable=True)
  end_time = Column(DateTime, nullable=True)
  plays = Column(Integer, nullable=False, default=0)
  likes = Column(Integer, nullable=False, default=0)
  score = Column(Float, nullable=False, default=0)
  rank = Column(Integer, nullable=True)
  snapshot_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
