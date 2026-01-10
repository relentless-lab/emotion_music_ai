from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.dependencies import (
    get_current_user,
    get_current_user_optional,
    get_db,
)
from app.models import LikeRecord, User, UserFollower
from app.models.work import Work, WorkStatus, WorkVisibility
from app.schemas.search import UserSearchResult
from app.schemas.social import SimpleMessage, ToggleResponse
from app.schemas.user_public import PublicUser, PublicUserProfile
from app.schemas.work import WorkAuthor, WorkPublicResponse
from app.services.url_resolver import resolve_music_url, resolve_cover_url

router = APIRouter()


def _ensure_public_work(db: Session, work_id: int) -> Work:
  work = db.query(Work).filter(Work.id == work_id).first()
  if not work:
    raise HTTPException(status_code=404, detail="作品不存在")
  status_value = work.status.value if hasattr(work.status, "value") else str(work.status)
  visibility_value = work.visibility.value if hasattr(work.visibility, "value") else str(work.visibility)
  if status_value != WorkStatus.published.value or visibility_value != WorkVisibility.public.value:
    raise HTTPException(status_code=403, detail="作品未公开，无法点赞")
  return work


def _to_public_work(work: Work, liked: bool = False) -> WorkPublicResponse:
  music_file = work.music_file
  audio_url = resolve_music_url(music_file)
  author = work.user
  author_payload = WorkAuthor(
      id=author.id,
      username=author.username,
      avatar=author.avatar,
      followers=author.followers_count,
      following=author.following_count,
  )
  return WorkPublicResponse(
      id=work.id,
      music_file_id=work.music_file_id,
      name=work.title,
      title=work.title,
      description=work.description,
      tags=work.tags,
      status=work.status.value if hasattr(work.status, "value") else str(work.status),
      visibility=work.visibility.value if hasattr(work.visibility, "value") else str(work.visibility),
      mood=work.mood,
      cover_url=resolve_cover_url(work.cover_url),
      like_count=work.like_count,
      play_count=work.play_count,
      audio_url=audio_url,
      created_at=work.created_at,
      updated_at=work.updated_at,
      published_at=work.published_at,
      author=author_payload,
      liked=liked,
  )


@router.post("/works/{work_id}/like", response_model=ToggleResponse, summary="Like a work")
async def like_work(
    work_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ToggleResponse:
  work = _ensure_public_work(db, work_id)
  existing = (
      db.query(LikeRecord)
      .filter(LikeRecord.user_id == current_user.id, LikeRecord.work_id == work_id)
      .first()
  )
  if existing:
    return ToggleResponse(liked=True)

  record = LikeRecord(user_id=current_user.id, work_id=work_id)
  db.add(record)
  work.like_count = (work.like_count or 0) + 1

  author = work.user
  author.total_likes = (author.total_likes or 0) + 1
  current_user.liked_works_count = (current_user.liked_works_count or 0) + 1

  db.add(author)
  db.add(work)
  db.add(current_user)
  db.commit()
  return ToggleResponse(liked=True)


@router.delete("/works/{work_id}/like", response_model=ToggleResponse, summary="Unlike a work")
async def unlike_work(
    work_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ToggleResponse:
  record = (
      db.query(LikeRecord)
      .filter(LikeRecord.user_id == current_user.id, LikeRecord.work_id == work_id)
      .first()
  )
  if not record:
    return ToggleResponse(liked=False)

  work = db.query(Work).filter(Work.id == work_id).first()
  author = work.user if work else None

  db.delete(record)
  if work:
    work.like_count = max((work.like_count or 0) - 1, 0)
    db.add(work)
  if author:
    author.total_likes = max((author.total_likes or 0) - 1, 0)
    db.add(author)

  current_user.liked_works_count = max((current_user.liked_works_count or 0) - 1, 0)
  db.add(current_user)
  db.commit()
  return ToggleResponse(liked=False)


@router.get("/likes/works", response_model=list[WorkPublicResponse], summary="List liked works")
async def list_liked_works(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[WorkPublicResponse]:
  likes = (
      db.query(LikeRecord)
      .filter(LikeRecord.user_id == current_user.id)
      .order_by(LikeRecord.created_at.desc())
      .all()
  )
  work_ids = [l.work_id for l in likes]
  if not work_ids:
    return []

  works = (
      db.query(Work)
      .filter(
          Work.id.in_(work_ids),
          Work.status == WorkStatus.published,
          Work.visibility == WorkVisibility.public,
      )
      .all()
  )
  work_map = {w.id: w for w in works}
  return [_to_public_work(work_map[wid], liked=True) for wid in work_ids if wid in work_map]


@router.post("/users/{user_id}/follow", response_model=ToggleResponse, summary="Follow a user")
async def follow_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ToggleResponse:
  if current_user.id == user_id:
    raise HTTPException(status_code=400, detail="无法关注自己")

  target = db.query(User).filter(User.id == user_id).first()
  if not target:
    raise HTTPException(status_code=404, detail="用户不存在")

  existing = (
      db.query(UserFollower)
      .filter(
          UserFollower.follower_id == current_user.id,
          UserFollower.following_id == user_id,
      )
      .first()
  )
  if existing:
    return ToggleResponse(followed=True)

  link = UserFollower(follower_id=current_user.id, following_id=user_id)
  db.add(link)
  current_user.following_count = (current_user.following_count or 0) + 1
  target.followers_count = (target.followers_count or 0) + 1
  db.add(current_user)
  db.add(target)
  db.commit()
  return ToggleResponse(followed=True)


@router.delete("/users/{user_id}/follow", response_model=ToggleResponse, summary="Unfollow a user")
async def unfollow_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ToggleResponse:
  link = (
      db.query(UserFollower)
      .filter(
          UserFollower.follower_id == current_user.id,
          UserFollower.following_id == user_id,
      )
      .first()
  )
  if not link:
    return ToggleResponse(followed=False)

  target = db.query(User).filter(User.id == user_id).first()
  db.delete(link)

  current_user.following_count = max((current_user.following_count or 0) - 1, 0)
  db.add(current_user)
  if target:
    target.followers_count = max((target.followers_count or 0) - 1, 0)
    db.add(target)
  db.commit()
  return ToggleResponse(followed=False)


@router.get("/users/{user_id}/followers", response_model=list[UserSearchResult], summary="List followers")
async def list_followers(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_current_user_optional),
) -> list[UserSearchResult]:
  links = db.query(UserFollower).filter(UserFollower.following_id == user_id).all()
  follower_ids = [l.follower_id for l in links]
  if not follower_ids:
    return []
  users = db.query(User).filter(User.id.in_(follower_ids)).all()
  followed_ids: set[int] = set()
  if current_user:
    followed_rows = (
        db.query(UserFollower.following_id)
        .filter(
            UserFollower.follower_id == current_user.id,
            UserFollower.following_id.in_(follower_ids),
        )
        .all()
    )
    followed_ids = {row[0] for row in followed_rows}
  return [
      UserSearchResult(
          id=u.id,
          username=u.username,
          avatar=resolve_cover_url(u.avatar),
          bio=u.personal_profile,
          followers=u.followers_count,
          following=u.following_count,
          is_followed=u.id in followed_ids,
      )
      for u in users
  ]


@router.get("/users/{user_id}/following", response_model=list[UserSearchResult], summary="List following")
async def list_following(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_current_user_optional),
) -> list[UserSearchResult]:
  links = db.query(UserFollower).filter(UserFollower.follower_id == user_id).all()
  following_ids = [l.following_id for l in links]
  if not following_ids:
    return []
  users = db.query(User).filter(User.id.in_(following_ids)).all()
  followed_ids: set[int] = set()
  if current_user:
    followed_rows = (
        db.query(UserFollower.following_id)
        .filter(
            UserFollower.follower_id == current_user.id,
            UserFollower.following_id.in_(following_ids),
        )
        .all()
    )
    followed_ids = {row[0] for row in followed_rows}
  return [
      UserSearchResult(
          id=u.id,
          username=u.username,
          avatar=resolve_cover_url(u.avatar),
          bio=u.personal_profile,
          followers=u.followers_count,
          following=u.following_count,
          is_followed=u.id in followed_ids,
      )
      for u in users
  ]


@router.get("/users/{user_id}", response_model=PublicUserProfile, summary="Public user profile")
async def get_public_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_current_user_optional),
) -> PublicUserProfile:
  user = db.query(User).filter(User.id == user_id).first()
  if not user:
    raise HTTPException(status_code=404, detail="用户不存在")

  is_followed = False
  if current_user:
    is_followed = (
        db.query(UserFollower)
        .filter(
            UserFollower.follower_id == current_user.id,
            UserFollower.following_id == user_id,
        )
        .first()
        is not None
    )

  works = (
      db.query(Work)
      .filter(
          Work.user_id == user.id,
          Work.status == WorkStatus.published,
          Work.visibility == WorkVisibility.public,
      )
      .order_by(Work.created_at.desc())
      .limit(20)
      .all()
  )

  # If viewer is logged in, compute which of the returned works are liked by the viewer.
  # IMPORTANT: do this in ONE query to avoid N+1.
  liked_work_ids: set[int] = set()
  if current_user and works:
    rows = (
        db.query(LikeRecord.work_id)
        .filter(
            LikeRecord.user_id == current_user.id,
            LikeRecord.work_id.in_([w.id for w in works]),
        )
        .all()
    )
    liked_work_ids = {row[0] for row in rows}

  liked_songs: list[WorkPublicResponse] = []
  if current_user and current_user.id == user.id:
    liked = (
        db.query(LikeRecord)
        .filter(LikeRecord.user_id == user.id)
        .order_by(LikeRecord.created_at.desc())
        .limit(20)
        .all()
    )
    work_ids = [l.work_id for l in liked]
    if work_ids:
      liked_works = (
          db.query(Work)
          .filter(
              Work.id.in_(work_ids),
              Work.status == WorkStatus.published,
              Work.visibility == WorkVisibility.public,
          )
          .all()
      )
      liked_map = {w.id: w for w in liked_works}
      liked_songs = [_to_public_work(liked_map[wid], liked=True) for wid in work_ids if wid in liked_map]

  profile = PublicUser(
      id=user.id,
      username=user.username,
      avatar=resolve_cover_url(user.avatar),
      bio=user.personal_profile,
      followers=user.followers_count,
      following=user.following_count,
      likesReceived=user.total_likes,
      playsThisMonth=user.plays_this_month,
      likedSongs=user.liked_works_count,
      generations=user.total_generations,
      emotionDetections=user.emotion_detection_count,
      works=user.total_works,
      is_followed=is_followed,
  )

  return PublicUserProfile(
      user=profile,
      works=[_to_public_work(w, liked=(w.id in liked_work_ids)) for w in works],
      liked_songs=liked_songs,
  )
