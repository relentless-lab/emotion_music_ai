from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Optional

import requests

from app.core.config import settings


@dataclass(frozen=True)
class SongGenJobResult:
    job_id: str
    status: str
    audio_url: Optional[str] = None
    error: Optional[str] = None


class SongGenRemoteClient:
    """
    Client for the 4090-side `songgen_infer_service`.

    Protocol:
    - POST   /v1/generate        -> {job_id, status}
    - GET    /v1/jobs/{job_id}   -> {job_id, status, audio_path?, error?}
    - GET    /v1/jobs/{job_id}/audio -> audio bytes
    """

    def __init__(self, base_url: str) -> None:
        self.base_url = base_url.rstrip("/")

    def submit(
        self,
        *,
        prompt: str,
        style: Optional[str],
        duration_sec: int,
        fmt: str,
        seed: Optional[int],
        separate: bool,
        instrumental: bool,
        vocal_only: bool = False,
        lyrics: Optional[str],
        timeout_seconds: int,
    ) -> str:
        payload = {
            "prompt": prompt or "",
            "style": style,
            "duration_sec": int(duration_sec),
            "format": fmt,
            "seed": seed,
            "separate": bool(separate),
            "instrumental": bool(instrumental),
            "vocal_only": bool(vocal_only),
            "lyrics": lyrics,
        }
        resp = requests.post(
            f"{self.base_url}/v1/generate",
            json=payload,
            timeout=timeout_seconds,
            proxies={"http": None, "https": None},
        )
        resp.raise_for_status()
        data = resp.json()
        job_id = data.get("job_id")
        if not job_id:
            raise RuntimeError(f"songgen submit: missing job_id (resp={data})")
        return str(job_id)

    def poll_until_done(
        self,
        job_id: str,
        *,
        timeout_seconds: int,
        poll_interval_seconds: float,
    ) -> SongGenJobResult:
        deadline = time.time() + timeout_seconds
        last_status: str | None = None
        while time.time() < deadline:
            resp = requests.get(
                f"{self.base_url}/v1/jobs/{job_id}",
                timeout=min(30, max(5, int(timeout_seconds))),
                proxies={"http": None, "https": None},
            )
            resp.raise_for_status()
            data = resp.json() or {}
            status = str(data.get("status") or "")
            last_status = status or last_status
            if status in {"succeeded", "failed"}:
                return SongGenJobResult(
                    job_id=job_id,
                    status=status,
                    audio_url=f"{self.base_url}/v1/jobs/{job_id}/audio" if status == "succeeded" else None,
                    error=data.get("error"),
                )
            time.sleep(max(0.3, float(poll_interval_seconds)))

        raise TimeoutError(f"songgen job timeout after {timeout_seconds}s (job_id={job_id}, last_status={last_status})")

    def download_audio(self, job_id: str, *, timeout_seconds: int) -> bytes:
        resp = requests.get(
            f"{self.base_url}/v1/jobs/{job_id}/audio",
            timeout=timeout_seconds,
            proxies={"http": None, "https": None},
        )
        resp.raise_for_status()
        return resp.content


def get_songgen_client() -> SongGenRemoteClient:
    if not settings.SONGGEN_REMOTE_URL:
        raise RuntimeError("SONGGEN_REMOTE_URL is not configured")
    return SongGenRemoteClient(settings.SONGGEN_REMOTE_URL)


