from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, or_
from sqlalchemy.orm import Session, joinedload

from app.core.dependencies import get_current_user_optional, get_db
from app.models import LikeRecord, User, UserFollower
from app.models.work import Work, WorkStatus, WorkVisibility
from app.schemas.search import SearchResponse, SongSearchResult, UserSearchResult
from app.services.url_resolver import resolve_cover_url, resolve_music_url

router = APIRouter()


def _ilike(column, keyword: str):
  """Case-insensitive contains; works on MySQL by lowering both sides."""
  lowered = keyword.lower()
  return func.lower(column).like(f"%{lowered}%")


@router.get("", response_model=SearchResponse, summary="Search songs and users")
async def search(
    query: str = Query(..., min_length=1),
    type: str = Query("all", description="all|song|user"),
    limit: int = 20,
    offset: int = 0,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_current_user_optional),
) -> SearchResponse:
  keyword = query.strip()
  if not keyword:
    return SearchResponse(query="", songs=[], users=[])

  safe_limit = min(max(limit, 1), 50)
  songs: list[SongSearchResult] = []
  users: list[UserSearchResult] = []

  if type in {"all", "song", "songs"}:
    works_query = (
        db.query(Work)
        .options(joinedload(Work.user), joinedload(Work.music_file))
        .filter(
            Work.status == WorkStatus.published,
            Work.visibility == WorkVisibility.public,
            or_(
                _ilike(Work.title, keyword),
                _ilike(Work.tags, keyword),
                _ilike(Work.description, keyword),
            ),
        )
        .order_by(Work.like_count.desc(), Work.play_count.desc(), Work.created_at.desc())
        .offset(offset)
        .limit(safe_limit)
    )
    works = works_query.all()
    liked_ids: set[int] = set()
    if current_user and works:
      liked_rows = (
          db.query(LikeRecord.work_id)
          .filter(
              LikeRecord.user_id == current_user.id,
              LikeRecord.work_id.in_([w.id for w in works]),
          )
          .all()
      )
      liked_ids = {row[0] for row in liked_rows}

    for w in works:
      author = w.user
      songs.append(
          SongSearchResult(
              id=w.id,
              title=w.title,
              cover_url=resolve_cover_url(w.cover_url),
              audio_url=resolve_music_url(w.music_file),
              like_count=w.like_count,
              play_count=w.play_count,
              tags=w.tags,
              author_id=author.id,
              author_name=author.username,
              liked=w.id in liked_ids,
          )
      )

  if type in {"all", "user", "users"}:
    user_query = (
        db.query(User)
        .filter(
            or_(
                _ilike(User.username, keyword),
                _ilike(User.personal_profile, keyword),
            )
        )
        .order_by(User.followers_count.desc(), User.total_likes.desc())
        .offset(offset)
        .limit(safe_limit)
    )
    found_users = user_query.all()
    followed_ids: set[int] = set()
    if current_user and found_users:
      follow_rows = (
          db.query(UserFollower.following_id)
          .filter(
              UserFollower.follower_id == current_user.id,
              UserFollower.following_id.in_([u.id for u in found_users]),
          )
          .all()
      )
      followed_ids = {row[0] for row in follow_rows}

    for u in found_users:
      users.append(
          UserSearchResult(
              id=u.id,
              username=u.username,
              avatar=resolve_cover_url(u.avatar),
              bio=u.personal_profile,
              followers=u.followers_count,
              following=u.following_count,
              is_followed=u.id in followed_ids,
          )
      )

  return SearchResponse(query=keyword, songs=songs, users=users)
