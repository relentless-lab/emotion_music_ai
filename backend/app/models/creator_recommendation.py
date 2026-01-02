from datetime import datetime

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String

from app.db.base_class import Base


class CreatorRecommendation(Base):
  __tablename__ = "creator_recommendations"

  id = Column(Integer, primary_key=True, autoincrement=True)
  user_id = Column(ForeignKey("users.id"), nullable=False, index=True)
  window_days = Column(Integer, nullable=False, default=3)
  score = Column(Float, nullable=False, default=0)
  reason = Column(String(255), nullable=True)
  snapshot_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
