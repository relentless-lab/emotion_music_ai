from __future__ import annotations

import math
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.core.dependencies import get_db
from app.models.like_record import LikeRecord
from app.models.user import User
from app.models.work import Work, WorkStatus, WorkVisibility
from app.models.work_play_log import WorkPlayLog
from app.schemas.ui import ClientConfig, HotSongItem, ModelOption, RecommendedCreatorItem, UploadPolicy
from app.services.url_resolver import resolve_cover_url, resolve_music_url

router = APIRouter()


@router.get("/config", response_model=ClientConfig, summary="Frontend config hints")
async def get_client_config() -> ClientConfig:
    """Provide the frontend with selectable models, upload constraints, and feature flags."""
    return ClientConfig(
        generation_models=[
            ModelOption(name="musicgen-small", label="MusicGen Small", type="generation", notes="Demo option"),
            ModelOption(name="riffusion", label="Riffusion", type="generation", notes="Seed-to-seed transitions"),
        ],
        emotion_models=[
            ModelOption(name="emo-classifier-v1", label="Emotion Classifier v1", type="emotion"),
        ],
        upload_policy=UploadPolicy(
            max_size_mb=25,
            accepted_types=["audio/mpeg", "audio/wav", "audio/x-wav", "audio/flac"],
            max_duration_seconds=600,
        ),
        features=[
            "generation",
            "emotion_analysis",
            "history",
            "waveform_preview",
            "hot_songs",
            "recommended_creators",
        ],
    )


def _minmax_normalize(values: list[float]) -> list[float]:
    if not values:
        return []
    vmin = min(values)
    vmax = max(values)
    if math.isclose(vmin, vmax):
        return [0.0 for _ in values]
    span = vmax - vmin
    return [(v - vmin) / span for v in values]


def _format_followers(n: int | None) -> str:
    v = int(n or 0)
    if v >= 1000000:
        return f"{v / 1000000:.1f}M followers"
    if v >= 1000:
        return f"{v / 1000:.1f}K followers"
    return f"{v} followers"


@router.get(
    "/hot-songs",
    response_model=list[HotSongItem],
    summary="Homepage hot songs (windowed, weighted by likes/plays)",
)
async def get_hot_songs(
    limit: int = Query(default=8, ge=1, le=50),
    window_days: int = Query(default=3, ge=1, le=30),
    db: Session = Depends(get_db),
) -> list[HotSongItem]:
    """
    Rank public & published works by recent activity within a time window.

    Score (default):
    - likes weight: 0.7
    - plays weight: 0.3

    We apply log1p to counts and then min-max normalize each metric in Python.
    """
    since = datetime.utcnow() - timedelta(days=window_days)

    likes_sub = (
        db.query(LikeRecord.work_id, func.count(LikeRecord.id).label("recent_likes"))
        .filter(LikeRecord.created_at >= since)
        .group_by(LikeRecord.work_id)
        .subquery()
    )
    plays_sub = (
        db.query(WorkPlayLog.work_id, func.count(WorkPlayLog.id).label("recent_plays"))
        .filter(WorkPlayLog.played_at >= since)
        .group_by(WorkPlayLog.work_id)
        .subquery()
    )

    # Pull a candidate pool larger than limit, then score in Python for flexibility.
    rows = (
        db.query(
            Work,
            func.coalesce(likes_sub.c.recent_likes, 0).label("recent_likes"),
            func.coalesce(plays_sub.c.recent_plays, 0).label("recent_plays"),
        )
        .options(joinedload(Work.music_file), joinedload(Work.user))
        .outerjoin(likes_sub, likes_sub.c.work_id == Work.id)
        .outerjoin(plays_sub, plays_sub.c.work_id == Work.id)
        .filter(Work.status == WorkStatus.published, Work.visibility == WorkVisibility.public)
        .order_by(func.coalesce(likes_sub.c.recent_likes, 0).desc(), func.coalesce(plays_sub.c.recent_plays, 0).desc())
        .limit(max(80, int(limit) * 20))
        .all()
    )

    works: list[Work] = [w for (w, _, _) in rows]
    recent_likes = [float(l or 0) for (_, l, _) in rows]
    recent_plays = [float(p or 0) for (_, _, p) in rows]

    likes_log = [math.log1p(v) for v in recent_likes]
    plays_log = [math.log1p(v) for v in recent_plays]
    likes_n = _minmax_normalize(likes_log)
    plays_n = _minmax_normalize(plays_log)

    scored = []
    for i, w in enumerate(works):
        score = 0.7 * likes_n[i] + 0.3 * plays_n[i]
        scored.append((score, w, int(recent_likes[i]), int(recent_plays[i])))
    scored.sort(key=lambda x: x[0], reverse=True)

    items: list[HotSongItem] = []
    for _, w, _, _ in scored[: int(limit)]:
        audio_url = resolve_music_url(w.music_file)
        items.append(
            HotSongItem(
                id=w.id,
                title=w.title,
                author_name=w.user.username if w.user else "AI Composer",
                cover_url=resolve_cover_url(w.cover_url),
                audio_url=audio_url,
                like_count=int(w.like_count or 0),
                play_count=int(w.play_count or 0),
                tags=w.tags,
                mood=w.mood,
            )
        )
    return items


@router.get(
    "/recommended-creators",
    response_model=list[RecommendedCreatorItem],
    summary="Homepage recommended creators",
)
async def get_recommended_creators(
    limit: int = Query(default=9, ge=1, le=50),
    db: Session = Depends(get_db),
) -> list[RecommendedCreatorItem]:
    """
    Recommend creators by long-term contribution signals (normalized + weighted):
    - total_generations (10%)
    - total_works       (20%)
    - total_likes       (60%)

    We apply log1p and min-max normalize each metric to reduce scale differences.
    """
    # Candidate creators: anyone with some activity signal
    users = (
        db.query(User)
        .filter(
            (User.total_generations > 0)
            | (User.total_works > 0)
            | (User.total_likes > 0)
        )
        .order_by(User.total_likes.desc(), User.total_works.desc(), User.total_generations.desc())
        .limit(2000)
        .all()
    )
    if not users:
        return []

    gens_log = [math.log1p(u.total_generations or 0) for u in users]
    works_log = [math.log1p(u.total_works or 0) for u in users]
    likes_log = [math.log1p(u.total_likes or 0) for u in users]

    gens_n = _minmax_normalize(gens_log)
    works_n = _minmax_normalize(works_log)
    likes_n = _minmax_normalize(likes_log)

    w_gen, w_works, w_likes = 0.1, 0.2, 0.6
    w_sum = w_gen + w_works + w_likes
    w_gen, w_works, w_likes = (w_gen / w_sum, w_works / w_sum, w_likes / w_sum)

    scored: list[tuple[float, User]] = []
    for i, u in enumerate(users):
        score = w_gen * gens_n[i] + w_works * works_n[i] + w_likes * likes_n[i]
        scored.append((score, u))

    if all(math.isclose(s, 0.0) for s, _ in scored):
        scored.sort(
            key=lambda it: (
                (it[1].total_likes or 0),
                (it[1].total_works or 0),
                (it[1].total_generations or 0),
                (it[1].followers_count or 0),
                (it[1].created_at or datetime.min),
            ),
            reverse=True,
        )
    else:
        scored.sort(
            key=lambda it: (
                it[0],
                (it[1].total_likes or 0),
                (it[1].total_works or 0),
                (it[1].total_generations or 0),
                (it[1].followers_count or 0),
            ),
            reverse=True,
        )

    top = [u for _, u in scored[: int(limit)]]
    return [
        RecommendedCreatorItem(
            id=u.id,
            name=u.username,
            handle=f"@{u.username}",
            followers=_format_followers(u.followers_count),
            # IMPORTANT: resolve oss:// and other storage paths to actual URL
            avatar=resolve_cover_url(u.avatar),
        )
        for u in top
    ]

