from __future__ import annotations

import base64
from pathlib import Path
from typing import Optional
from uuid import uuid4

from openai import AsyncOpenAI
import httpx

from app.core.config import settings
from app.services.oss_storage import (
    OSSStorage,
    build_oss_key,
    encode_oss_path,
    normalize_oss_like_url,
    resolve_storage_path_to_url,
)


def _get_client() -> Optional[AsyncOpenAI]:
    if not settings.OPENAI_API_KEY:
        return None
    return AsyncOpenAI(api_key=settings.OPENAI_API_KEY, base_url=settings.OPENAI_API_BASE)


async def generate_album_cover_image(prompt: str, user_id: int | None = None) -> Optional[str]:
    """
    使用 Qwen-image (通过硅基流动 OpenAI 兼容接口) 生成专辑封面。

    返回值为相对路径，例如："/static/covers/cover_xxx.png"
    若调用失败则返回 None。
    """
    client = _get_client()
    if client is None:
        return None

    covers_root = Path(settings.STATIC_ROOT) / "covers"
    covers_root.mkdir(parents=True, exist_ok=True)

    # Some providers (e.g. certain OpenAI-compatible gateways) may not support response_format="b64_json".
    # We try b64_json first, then fallback to provider default (often URL).
    try:
        resp = await client.images.generate(  # type: ignore[call-arg]
            model=getattr(settings, "IMAGE_MODEL", "Qwen/Qwen-Image"),
            prompt=prompt,
            size="1024x1024",
            n=1,
            response_format="b64_json",
        )
    except Exception as exc_first:
        print(f"[image_service] 图片生成（b64_json）失败，尝试降级为 url: {exc_first}")
        try:
            resp = await client.images.generate(  # type: ignore[call-arg]
                model=getattr(settings, "IMAGE_MODEL", "Qwen/Qwen-Image"),
                prompt=prompt,
                size="1024x1024",
                n=1,
            )
        except Exception as exc:
            print(f"[image_service] 调用图片生成接口失败: {exc}")
            return None

    if not resp or not getattr(resp, "data", None):
        print("[image_service] 图片生成响应为空")
        return None

    first = resp.data[0]

    def _upload_bytes(image_bytes: bytes) -> Optional[str]:
        # 优先走 OSS，若未启用则写本地文件
        if settings.OSS_ENABLED:
            try:
                key = build_oss_key(
                    category="picture",
                    source="generated",
                    user_id=user_id or 0,
                    ext=".png",
                )
                OSSStorage().put_bytes(key, image_bytes, content_type="image/png")
                return encode_oss_path(key)
            except Exception as exc:  # pragma: no cover - defensive path
                print(f"[image_service] 上传 OSS 失败，降级本地: {exc}")

        # fallback 写本地（兼容未启用 OSS）
        filename = f"cover_{uuid4().hex}.png"
        filepath = covers_root / filename
        filepath.write_bytes(image_bytes)
        return f"/{settings.STATIC_ROOT}/covers/{filename}"

    # 1) 优先使用 b64_json
    image_b64 = getattr(first, "b64_json", None)
    if image_b64:
        try:
            image_bytes = base64.b64decode(image_b64)
            return _upload_bytes(image_bytes)
        except Exception as exc:
            print(f"[image_service] 解码 b64 图片失败: {exc}")

    # 2) 若没有 b64_json，则尝试下载 URL
    image_url = getattr(first, "url", None)
    if image_url:
        try:
            timeout = httpx.Timeout(connect=15.0, read=120.0, write=15.0, pool=15.0)
            async with httpx.AsyncClient(timeout=timeout, trust_env=False) as client_http:
                r = await client_http.get(image_url)
                r.raise_for_status()
                image_bytes = r.content
            return _upload_bytes(image_bytes)
        except Exception as exc:
            print(f"[image_service] 下载图片失败: {exc}")
            # 退一步：至少返回远程 URL，前端仍然可以展示
            normalized = normalize_oss_like_url(image_url)
            url = resolve_storage_path_to_url(normalized)
            return url or image_url

    print("[image_service] 响应中既没有 b64_json 也没有 url")
    return None


