from __future__ import annotations

import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

import oss2

from app.core.config import settings


def build_oss_key(
    *,
    category: str,  # e.g. "music" | "picture" | "report"
    source: str,  # e.g. "upload" | "generated"
    user_id: int,
    original_filename: str | None = None,
    ext: str | None = None,
) -> str:
    """Build a hierarchical OSS key: {category}/{source}/u{uid}/YYYY/MM/DD/{uuid}{ext}."""
    suffix = ext or (Path(original_filename).suffix if original_filename else "")
    dt = datetime.utcnow()
    return f"{category}/{source}/u{user_id}/{dt:%Y/%m/%d}/{uuid.uuid4().hex}{suffix}"


class OSSStorage:
    """Thin wrapper around oss2 with config from settings."""

    def __init__(self):
        if not settings.OSS_ENABLED:
            raise RuntimeError("OSS is disabled (OSS_ENABLED=false)")
        if not (
            settings.OSS_ENDPOINT
            and settings.OSS_BUCKET
            and settings.OSS_ACCESS_KEY_ID
            and settings.OSS_ACCESS_KEY_SECRET
        ):
            raise RuntimeError("OSS config missing")

        auth = oss2.Auth(settings.OSS_ACCESS_KEY_ID, settings.OSS_ACCESS_KEY_SECRET)
        self.bucket = oss2.Bucket(auth, settings.OSS_ENDPOINT, settings.OSS_BUCKET)
        self.public_base_url = (settings.OSS_PUBLIC_BASE_URL or "").rstrip("/")
        self.sign_expires = int(settings.OSS_SIGN_EXPIRES)

    def put_bytes(self, key: str, data: bytes, content_type: Optional[str] = None) -> None:
        headers = {}
        if content_type:
            headers["Content-Type"] = content_type
        self.bucket.put_object(key, data, headers=headers)

    def put_file(self, key: str, local_path: str, content_type: Optional[str] = None) -> None:
        headers = {}
        if content_type:
            headers["Content-Type"] = content_type
        self.bucket.put_object_from_file(key, local_path, headers=headers)

    def get_url(self, key: str) -> str:
        # 公共读：直接拼公开 URL；私有：返回签名 URL
        if self.public_base_url:
            return f"{self.public_base_url}/{key}"
        return self.bucket.sign_url("GET", key, self.sign_expires)

    def delete(self, key: str) -> None:
        self.bucket.delete_object(key)


# ---------- helpers ----------
def encode_oss_path(key: str) -> str:
    return f"oss://{key}"


def decode_oss_path(storage_path: str | None) -> str | None:
    if storage_path and storage_path.startswith("oss://"):
        return storage_path[len("oss://") :]
    return None


def resolve_storage_path_to_url(storage_path: str | None) -> str | None:
    """
    - http(s)://... 直接返回
    - oss://key -> 生成可访问 URL
    - 其他返回 None（由上层决定是否兜底到本地静态目录）
    """
    if not storage_path:
        return None
    if storage_path.startswith("http://") or storage_path.startswith("https://"):
        return storage_path
    key = decode_oss_path(storage_path)
    if key:
        try:
            return OSSStorage().get_url(key)
        except Exception as exc:  # pragma: no cover - defensive
            print(f"[oss_storage] resolve url failed: {exc}")
            return None
    return None


def normalize_oss_like_url(value: str | None) -> str | None:
    """
    将指向当前桶的公开 URL 转成 oss://key。
    其他非本桶/非 http/oss 的值保持原样，方便兼容外部链接。
    """
    if not value:
        return value
    if value.startswith("oss://"):
        return value
    public_base = (settings.OSS_PUBLIC_BASE_URL or "").rstrip("/")
    if public_base and value.startswith(public_base + "/"):
        key = value[len(public_base) + 1 :]
        return encode_oss_path(key)
    return value



