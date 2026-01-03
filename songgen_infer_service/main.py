from __future__ import annotations

from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from .config import settings
from .jobs import JobStatus, registry


app = FastAPI(title="SongGeneration Inference Service", version="1.0")


class GenerateRequest(BaseModel):
    # ✅ 允许空 prompt（纯音乐场景），runner 会自动兜底为默认结构
    prompt: str = Field("", description="歌词或音乐描述；纯音乐可为空")
    style: Optional[str] = None
    duration_sec: int = Field(30, ge=1, le=60 * 10)
    format: str = Field("wav", description="wav|flac")
    seed: Optional[int] = None
    separate: bool = False

    # ✅ 新增：显式控制“纯音乐/有人声”
    instrumental: bool = Field(True, description="true=纯音乐(no vocals)；false=有人声/可带歌词")
    vocal_only: bool = Field(False, description="true=纯人声(a cappella)。与 instrumental/separate 互斥")
    lyrics: Optional[str] = Field(None, description="歌词内容（仅 vocal 场景使用；可为空，空则回退到 prompt）")

    # Prompt audio (reference) for imitation:
    # NOTE: This JSON endpoint intentionally does NOT accept binary audio.
    # Use /v1/generate-with-audio to upload a file.
    auto_prompt_audio_type: Optional[str] = Field(
        None, description="可选：不上传音频时，让模型自动选参考类型（如 Pop/Jazz 等）"
    )


class GenerateResponse(BaseModel):
    job_id: str
    status: str


class JobStatusResponse(BaseModel):
    job_id: str
    status: str
    audio_path: Optional[str] = None
    error: Optional[str] = None


@app.post("/v1/generate", response_model=GenerateResponse)
async def generate(payload: GenerateRequest) -> GenerateResponse:
    # flag 互斥校验（与上游文档一致）
    if payload.instrumental and payload.vocal_only:
        raise HTTPException(status_code=422, detail="instrumental 与 vocal_only 互斥")
    if payload.separate and (payload.instrumental or payload.vocal_only):
        raise HTTPException(status_code=422, detail="separate 与 instrumental/vocal_only 互斥（separate 用于分离人声与伴奏）")

    if (not payload.instrumental) and (not (payload.lyrics or "").strip()) and (not (payload.prompt or "").strip()):
        raise HTTPException(status_code=422, detail="vocal 模式下，prompt 或 lyrics 至少提供一个")
    job = registry.create()
    Path(job.job_dir).mkdir(parents=True, exist_ok=True)
    registry.submit(
        job,
        prompt=payload.prompt,
        style=payload.style,
        duration_sec=payload.duration_sec,
        fmt=payload.format,
        seed=payload.seed,
        separate=payload.separate,
        instrumental=payload.instrumental,
        vocal_only=payload.vocal_only,
        lyrics=payload.lyrics,
        prompt_audio_path=None,
        auto_prompt_audio_type=payload.auto_prompt_audio_type,
    )
    return GenerateResponse(job_id=job.job_id, status=job.status.value)


@app.post("/v1/generate-with-audio", response_model=GenerateResponse)
async def generate_with_audio(
    prompt_audio: UploadFile = File(..., description="参考音频文件（wav/mp3/flac 等）"),
    prompt: str = Form("", description="歌词或音乐描述；可为空"),
    style: Optional[str] = Form(None),
    duration_sec: int = Form(30),
    format: str = Form("wav"),
    seed: Optional[int] = Form(None),
    separate: bool = Form(False),
    instrumental: bool = Form(True),
    vocal_only: bool = Form(False),
    lyrics: Optional[str] = Form(None),
    auto_prompt_audio_type: Optional[str] = Form(None),
) -> GenerateResponse:
    # flag 互斥校验（与 /v1/generate 一致）
    if instrumental and vocal_only:
        raise HTTPException(status_code=422, detail="instrumental 与 vocal_only 互斥")
    if separate and (instrumental or vocal_only):
        raise HTTPException(status_code=422, detail="separate 与 instrumental/vocal_only 互斥（separate 用于分离人声与伴奏）")

    if (not instrumental) and (not (lyrics or "").strip()) and (not (prompt or "").strip()):
        raise HTTPException(status_code=422, detail="vocal 模式下，prompt 或 lyrics 至少提供一个")

    job = registry.create()
    Path(job.job_dir).mkdir(parents=True, exist_ok=True)

    # Save uploaded prompt audio under job dir and pass absolute path into jsonl.
    original_name = (prompt_audio.filename or "").strip() or "prompt_audio"
    suffix = Path(original_name).suffix or ".wav"
    audio_path = Path(job.job_dir) / f"prompt_audio{suffix}"
    try:
        content = await prompt_audio.read()
        audio_path.write_bytes(content)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"保存参考音频失败: {exc}") from exc

    registry.submit(
        job,
        prompt=prompt,
        style=style,
        duration_sec=duration_sec,
        fmt=format,
        seed=seed,
        separate=separate,
        instrumental=instrumental,
        vocal_only=vocal_only,
        lyrics=lyrics,
        prompt_audio_path=str(audio_path),
        auto_prompt_audio_type=auto_prompt_audio_type,
    )
    return GenerateResponse(job_id=job.job_id, status=job.status.value)


@app.get("/v1/jobs/{job_id}", response_model=JobStatusResponse)
async def get_job(job_id: str) -> JobStatusResponse:
    job = registry.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="job not found")
    return JobStatusResponse(**job.to_dict())


@app.get("/v1/jobs/{job_id}/audio")
async def get_audio(job_id: str):
    job = registry.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="job not found")
    if job.status != JobStatus.succeeded or not job.audio_path:
        raise HTTPException(status_code=409, detail=f"job not ready (status={job.status.value})")

    p = Path(job.audio_path)
    if not p.exists():
        raise HTTPException(status_code=404, detail="audio not found on disk")

    suffix = p.suffix.lower()
    media_type = "application/octet-stream"
    if suffix == ".wav":
        media_type = "audio/wav"
    elif suffix == ".flac":
        media_type = "audio/flac"

    return FileResponse(str(p), media_type=media_type, filename=p.name)


