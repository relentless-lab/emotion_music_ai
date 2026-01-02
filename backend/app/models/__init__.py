"""
Database models live here. Add SQLAlchemy or ORM models as needed.
"""

from app.models.task import TaskRecord
from app.models.user import User
from app.models.dialogue import Dialogue
from app.models.dialogue_message import DialogueMessage
from app.models.music_file import MusicFile
from app.models.emotion_analysis import EmotionAnalysis
from app.models.work import Work, WorkStatus, WorkVisibility
from app.models.like_record import LikeRecord
from app.models.user_follower import UserFollower
from app.models.work_play_log import WorkPlayLog
from app.models.work_popularity_snapshot import WorkPopularitySnapshot
from app.models.creator_recommendation import CreatorRecommendation

__all__ = [
    "TaskRecord",
    "User",
    "Dialogue",
    "DialogueMessage",
    "MusicFile",
    "EmotionAnalysis",
    "Work",
    "WorkStatus",
    "WorkVisibility",
    "LikeRecord",
    "UserFollower",
    "WorkPlayLog",
    "WorkPopularitySnapshot",
    "CreatorRecommendation",
]
