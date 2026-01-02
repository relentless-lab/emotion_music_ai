from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, UniqueConstraint
from sqlalchemy.orm import relationship

from app.db.base_class import Base


class UserFollower(Base):
  __tablename__ = "user_followers"
  __table_args__ = (
      UniqueConstraint("follower_id", "following_id", name="uq_follow_pair"),
  )

  id = Column(Integer, primary_key=True, autoincrement=True)
  follower_id = Column(ForeignKey("users.id"), nullable=False, index=True)
  following_id = Column(ForeignKey("users.id"), nullable=False, index=True)
  created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

  follower = relationship("User", foreign_keys=[follower_id], back_populates="following")
  following = relationship("User", foreign_keys=[following_id], back_populates="followers")
