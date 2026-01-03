from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, Optional
from uuid import uuid4

from .config import settings
from .songgen_runner import run_songgen_job


class JobStatus(str, Enum):
    queued = "queued"
    running = "running"
    succeeded = "succeeded"
    failed = "failed"


@dataclass
class Job:
    job_id: str
    status: JobStatus = JobStatus.queued
    job_dir: str = ""
    audio_path: Optional[str] = None
    error: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "job_id": self.job_id,
            "status": self.status.value,
            "audio_path": self.audio_path,
            "error": self.error,
        }


class JobRegistry:
    def __init__(self) -> None:
        self._jobs: Dict[str, Job] = {}
        self._sem = asyncio.Semaphore(max(1, int(settings.SONGGEN_CONCURRENCY)))

    def create(self) -> Job:
        job_id = uuid4().hex
        job_dir = str(Path(settings.SONGGEN_JOBS_DIR) / job_id)
        job = Job(job_id=job_id, status=JobStatus.queued, job_dir=job_dir)
        self._jobs[job_id] = job
        return job

    def get(self, job_id: str) -> Optional[Job]:
        return self._jobs.get(job_id)

    def all(self) -> Dict[str, Job]:
        return self._jobs

    def submit(
        self,
        job: Job,
        *,
        prompt: str,
        style: Optional[str],
        duration_sec: int,
        fmt: str,
        seed: Optional[int],
        separate: bool,
        instrumental: bool,
        vocal_only: bool,
        lyrics: Optional[str],
        prompt_audio_path: Optional[str],
        auto_prompt_audio_type: Optional[str],
    ) -> None:
        # fire-and-forget background coroutine
        asyncio.create_task(
            self._run_job(
                job,
                prompt=prompt,
                style=style,
                duration_sec=duration_sec,
                fmt=fmt,
                seed=seed,
                separate=separate,
                instrumental=instrumental,
                vocal_only=vocal_only,
                lyrics=lyrics,
                prompt_audio_path=prompt_audio_path,
                auto_prompt_audio_type=auto_prompt_audio_type,
            )
        )

    async def _run_job(
        self,
        job: Job,
        *,
        prompt: str,
        style: Optional[str],
        duration_sec: int,
        fmt: str,
        seed: Optional[int],
        separate: bool,
        instrumental: bool,
        vocal_only: bool,
        lyrics: Optional[str],
        prompt_audio_path: Optional[str],
        auto_prompt_audio_type: Optional[str],
    ) -> None:
        async with self._sem:
            job.status = JobStatus.running
            job.updated_at = datetime.utcnow()
            try:
                audio_path = await run_songgen_job(
                    job_dir=job.job_dir,
                    prompt=prompt,
                    style=style,
                    duration_sec=duration_sec,
                    fmt=fmt,
                    seed=seed,
                    separate=separate,
                    instrumental=instrumental,
                    vocal_only=vocal_only,
                    lyrics=lyrics,
                    prompt_audio_path=prompt_audio_path,
                    auto_prompt_audio_type=auto_prompt_audio_type,
                    timeout_seconds=int(settings.SONGGEN_TIMEOUT_SECONDS),
                )
                job.audio_path = audio_path
                job.status = JobStatus.succeeded
                job.error = None
            except Exception as exc:  # noqa: BLE001
                job.status = JobStatus.failed
                job.error = str(exc)
            finally:
                job.updated_at = datetime.utcnow()


registry = JobRegistry()


