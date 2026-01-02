from app.db.base_class import Base

# 导入模型以便 Alembic 自动发现
# flake8: noqa
from app.models.user import User  # noqa: E402,F401
from app.models.task import TaskRecord  # noqa: E402,F401
from app.models.dialogue import Dialogue  # noqa: E402,F401
from app.models.dialogue_message import DialogueMessage  # noqa: E402,F401
from app.models.music_file import MusicFile  # noqa: E402,F401
from app.models.emotion_analysis import EmotionAnalysis  # noqa: E402,F401
from app.models.work import Work  # noqa: E402,F401
from app.models.like_record import LikeRecord  # noqa: E402,F401
from app.models.user_follower import UserFollower  # noqa: E402,F401
from app.models.work_play_log import WorkPlayLog  # noqa: E402,F401
from app.models.work_popularity_snapshot import WorkPopularitySnapshot  # noqa: E402,F401
from app.models.creator_recommendation import CreatorRecommendation  # noqa: E402,F401
