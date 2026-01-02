"""One-off migration: move local audio/images to OSS and update DB to oss://key.

Usage (from backend/):
  python scripts/migrate_local_to_oss.py
  python scripts/migrate_local_to_oss.py --delete-local   # optional, delete after upload
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Iterable, Optional

from sqlalchemy import select

# Ensure project root on path
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.append(str(BASE_DIR))

from app.core.config import settings
from app.db.session import SessionLocal
from app.models.music_file import MusicFile
from app.models.work import Work
from app.services.oss_storage import (
    OSSStorage,
    build_oss_key,
    decode_oss_path,
    encode_oss_path,
    normalize_oss_like_url,
)


def guess_content_type(path: Path) -> Optional[str]:
    ext = path.suffix.lower()
    if ext in {".wav"}:
        return "audio/wav"
    if ext in {".mp3"}:
        return "audio/mpeg"
    if ext in {".flac"}:
        return "audio/flac"
    if ext in {".png"}:
        return "image/png"
    if ext in {".jpg", ".jpeg"}:
        return "image/jpeg"
    return None


def pick_first_existing(candidates: Iterable[Path]) -> Optional[Path]:
    for p in candidates:
        if p and p.exists() and p.is_file():
            return p
    return None


def migrate_audio(
    oss: OSSStorage,
    mf: MusicFile,
    delete_local: bool,
) -> tuple[bool, str]:
    """Migrate one MusicFile audio. Returns (changed, message)."""
    if decode_oss_path(mf.storage_path):
        return False, "already oss"

    candidates = []
    if mf.storage_path:
        candidates.append(Path(mf.storage_path))
    if mf.file_name:
        candidates.append(Path(settings.STATIC_ROOT) / "audio" / Path(mf.file_name).name)

    local_path = pick_first_existing(candidates)
    if not local_path:
        return False, "no local file found"

    source = "generated" if getattr(mf, "source_type", "") == "generated" else "upload"
    key = build_oss_key(
        category="music",
        source=source,
        user_id=mf.user_id or 0,
        original_filename=local_path.name,
        ext=local_path.suffix,
    )
    oss.put_file(key, str(local_path), content_type=guess_content_type(local_path))
    mf.storage_path = encode_oss_path(key)

    if delete_local:
        try:
            local_path.unlink(missing_ok=True)
        except Exception as exc:  # pragma: no cover
            return True, f"uploaded but delete failed: {exc}"
    return True, "uploaded"


def migrate_cover_value(
    oss: OSSStorage,
    value: Optional[str],
    user_id: int,
    source: str,
    delete_local: bool,
) -> tuple[Optional[str], str]:
    """Migrate a cover path/string, return (new_value, message)."""
    if not value:
        return value, "empty"

    # Already OSS or same-bucket URL
    normalized = normalize_oss_like_url(value)
    if decode_oss_path(normalized):
        return normalized, "already oss"

    if normalized.startswith("http://") or normalized.startswith("https://"):
        # 外部链接，保持
        return normalized, "external url"

    # Local candidates
    candidates: list[Path] = []
    if normalized.startswith("/static/covers/") or normalized.startswith("static/covers/"):
        candidates.append(Path(settings.STATIC_ROOT) / "covers" / Path(normalized).name)
    else:
        # try as absolute path
        candidates.append(Path(normalized))

    local_path = pick_first_existing(candidates)
    if not local_path:
        return value, "no local cover"

    key = build_oss_key(
        category="picture",
        source=source,
        user_id=user_id or 0,
        original_filename=local_path.name,
        ext=local_path.suffix,
    )
    oss.put_file(key, str(local_path), content_type=guess_content_type(local_path))
    if delete_local:
        try:
            local_path.unlink(missing_ok=True)
        except Exception as exc:  # pragma: no cover
            return encode_oss_path(key), f"uploaded cover delete failed: {exc}"
    return encode_oss_path(key), "uploaded cover"


def main(delete_local: bool) -> None:
    if not settings.OSS_ENABLED:
        print("ERROR: OSS_ENABLED is false; aborting.")
        return
    if SessionLocal is None:
        print("ERROR: DATABASE_URL is not configured; aborting.")
        return

    oss = OSSStorage()
    session = SessionLocal()

    audio_total = audio_uploaded = 0
    cover_total = cover_uploaded = 0

    try:
        for mf in session.scalars(select(MusicFile)).all():
            audio_total += 1
            changed, msg = migrate_audio(oss, mf, delete_local)
            if changed:
                audio_uploaded += 1
            # Migrate generated cover images on music_file
            new_cover, cmsg = migrate_cover_value(
                oss,
                mf.cover_image_path,
                user_id=mf.user_id or 0,
                source="generated",
                delete_local=delete_local,
            )
            if new_cover != mf.cover_image_path:
                mf.cover_image_path = new_cover
                cover_uploaded += 1
            print(f"[MusicFile id={mf.id}] audio: {msg}; cover: {cmsg}")
            session.add(mf)

        for work in session.scalars(select(Work)).all():
            cover_total += 1
            new_cover, msg = migrate_cover_value(
                oss,
                work.cover_url,
                user_id=work.user_id or 0,
                source="upload",
                delete_local=delete_local,
            )
            if new_cover != work.cover_url:
                work.cover_url = new_cover
                cover_uploaded += 1
                session.add(work)
            print(f"[Work id={work.id}] cover: {msg}")

        session.commit()
    finally:
        session.close()

    print(
        f"Done. audio total={audio_total}, uploaded/updated={audio_uploaded}; "
        f"cover total={cover_total}, uploaded/updated={cover_uploaded}; "
        f"delete_local={delete_local}"
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Migrate local audio/images to OSS.")
    parser.add_argument(
        "--delete-local",
        action="store_true",
        help="Delete local files after successful upload (default: keep).",
    )
    args = parser.parse_args()
    main(delete_local=args.delete_local)



