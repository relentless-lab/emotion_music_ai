from __future__ import annotations

from pathlib import Path

from app.models.music_file import MusicFile
from app.services.oss_storage import resolve_storage_path_to_url


def resolve_music_url(music_file: MusicFile | None) -> str | None:
    """
    根据 music_file 的存储字段解析成可访问 URL。
    优先使用 oss:// 或 http(s)，否则兜底旧的本地路径。
    """
    if not music_file:
        return None

    # 优先 OSS / 直链
    url = resolve_storage_path_to_url(music_file.storage_path)
    if url:
        return url

    # 兼容旧数据：generated 用 static/audio，upload 用 media
    if getattr(music_file, "source_type", None) == "generated" and music_file.file_name:
        return f"/static/audio/{Path(music_file.file_name).name}"

    if music_file.storage_path:
        return f"/media/{Path(music_file.storage_path).name}"

    return None


def resolve_cover_url(path: str | None) -> str | None:
    """解析封面路径（oss:// | http(s) | /static/...）。"""
    url = resolve_storage_path_to_url(path)
    return url or path



