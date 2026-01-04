from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import numpy as np

from app.core.config import settings
from app.core.device import DeviceConfig
from app.musicgen.base import GenerateConfig, ModelName
from app.musicgen.musicgen_pretrained import MusicGenPretrained, MusicGenPretrainedConfig
from app.musicgen.musicgen_remote import MusicGenRemote
from app.services.storage_service import save_audio_bytes, save_audio_waveform
from app.songgen.songgen_remote import get_songgen_client
from app.services.songgen_style_tags import (
    merge_style_tags,
    normalize_songgen_descriptions,
    suggest_songgen_style_tags,
)
from app.services.songgen_llm_enhancer import enhance_for_songgen, ensure_structured_lyrics, sanitize_user_lyrics

import wave
from pathlib import Path


@dataclass
class GenerateResult:
    filename: str      # 文件名，如 "musicgen_pretrained_xxx.wav"
    rel_path: str      # 相对于项目根的路径，如 "static/audio/xxx.wav"
    duration_sec: float
    sample_rate: int
    model_name: ModelName


# 简单单例缓存
_musicgen_pretrained: MusicGenPretrained | None = None


def get_musicgen_pretrained() -> MusicGenPretrained:
    global _musicgen_pretrained
    if _musicgen_pretrained is None:
        mg_cfg = MusicGenPretrainedConfig(
            model_id=settings.MUSICGEN_MODEL_ID,
            max_single_clip_sec=settings.MUSICGEN_MAX_SINGLE_CLIP_SEC,
            tokens_per_second=settings.MUSICGEN_TOKENS_PER_SECOND,
        )
        
        if settings.REMOTE_INFERENCE_URL:
            print(f"[generation_service] Using Remote Generator at {settings.REMOTE_INFERENCE_URL}")
            _musicgen_pretrained = MusicGenRemote(cfg=mg_cfg)
        else:
            print(f"[generation_service] Using Local Generator (Model: {settings.MUSICGEN_MODEL_ID})")
            dev_cfg = DeviceConfig(
                use_cuda_if_available=settings.MUSICGEN_USE_CUDA_IF_AVAILABLE,
                preferred_device=settings.MUSICGEN_PREFERRED_DEVICE,
            )
            _musicgen_pretrained = MusicGenPretrained(cfg=mg_cfg, device_cfg=dev_cfg)
            
    return _musicgen_pretrained


def get_generator(model_name: ModelName) -> MusicGenPretrained:
    # 目前只有一个模型，直接返回；未来可扩展 finetune 模型
    if model_name == "musicgen_finetune":
        return get_musicgen_pretrained()
    return get_musicgen_pretrained()


def generate_music_file(
    prompt_zh: str,
    duration_sec: float,
    model_name: ModelName = "musicgen_pretrained",
    *,
    instrumental: bool = True,
    lyrics: str | None = None,
    style: str | None = None,
) -> GenerateResult:
    """
    对外提供的统一生成接口：
    - 输入：中文描述 + 目标时长 + 模型名
    - 过程：调用模型层生成长音频 -> 保存为 wav 文件
    - 输出：包含文件路径、实际时长等信息的 GenerateResult
    """
    # 优先走 SongGeneration(full-new) 远程推理（4090）
    if settings.SONGGEN_REMOTE_URL or model_name == "songgen_full_new":
        client = get_songgen_client()

        # --- LLM enhancer (optional): better descriptions + auto lyric writing for vocal mode ---
        llm_descriptions: str | None = None
        llm_lyrics: str | None = None
        if getattr(settings, "SONGGEN_LLM_ENABLED", False):
            r = enhance_for_songgen(
                prompt_zh=prompt_zh or "",
                instrumental=bool(instrumental),
                duration_sec=int(duration_sec),
                user_style=style,
                user_lyrics=lyrics,
            )
            llm_descriptions = r.descriptions
            llm_lyrics = r.lyrics

        # 1) Lyrics to send:
        # - instrumental: always None (model should not sing; enforced by --bgm on 4090)
        # - vocal + user provided: sanitize for robustness (spaces/newlines/punct)
        # - vocal + missing: prefer LLM-generated lyrics; if unavailable, fallback to None (4090 runner will fallback)
        lyrics_to_send: str | None = None
        if not bool(instrumental):
            if (lyrics or "").strip():
                lyrics_to_send = sanitize_user_lyrics(
                    lyrics or "",
                    max_chars=int(getattr(settings, "SONGGEN_LLM_MAX_LYRIC_CHARS", 1200)),
                )
            else:
                lyrics_to_send = llm_lyrics
            if (lyrics_to_send or "").strip():
                lyrics_to_send = ensure_structured_lyrics(lyrics_to_send or "", duration_sec=int(duration_sec))

        # 2) Descriptions/style to send:
        # Prefer LLM descriptions; fallback to deterministic keyword extractor.
        if (llm_descriptions or "").strip():
            style_to_send = llm_descriptions or ""
        else:
            suggestion = suggest_songgen_style_tags(prompt_zh or "")
            extra_tags = suggestion.tags
            # Guard negative tags: they can backfire on some models (interpreted as presence).
            if not getattr(settings, "SONGGEN_ALLOW_NEGATIVE_TAGS", False):
                extra_tags = [t for t in extra_tags if not (t or "").strip().lower().startswith("no ")]
            style_to_send = merge_style_tags(base_style=style, extra_tags=extra_tags)

        if not (style_to_send or "").strip():
            style_to_send = "instrumental" if instrumental else "vocal"

        # Normalize into recommended 6 stable dimensions for SongGeneration.
        normalized = normalize_songgen_descriptions(
            prompt_zh=prompt_zh or "",
            style=style_to_send,
            instrumental=bool(instrumental),
        )
        style_to_send = normalized or style_to_send

        # Debug visibility: makes it easy to verify tag extraction in logs
        try:
            print(
                f"[generation_service] (songgen) prompt='{(prompt_zh or '').strip()[:80]}' "
                f"instrumental={bool(instrumental)} style_to_send='{style_to_send}' "
                f"lyrics_provided={bool((lyrics or '').strip())} lyrics_llm_used={bool(llm_lyrics)}"
            )
        except Exception:
            pass

        # 统一向 4090 请求 wav，主后端按旧逻辑落盘到 static/audio
        job_id = client.submit(
            prompt=prompt_zh or "",
            style=style_to_send,
            duration_sec=int(duration_sec),
            fmt="wav",
            seed=None,
            separate=False,
            instrumental=bool(instrumental),
            lyrics=lyrics_to_send,
            timeout_seconds=int(settings.SONGGEN_REQUEST_TIMEOUT_SECONDS),
        )

        result = client.poll_until_done(
            job_id,
            timeout_seconds=int(settings.SONGGEN_TOTAL_TIMEOUT_SECONDS),
            poll_interval_seconds=float(settings.SONGGEN_POLL_INTERVAL_SECONDS),
        )
        if result.status != "succeeded":
            raise RuntimeError(result.error or f"songgen failed (job_id={job_id})")

        audio_bytes = client.download_audio(job_id, timeout_seconds=int(settings.SONGGEN_REQUEST_TIMEOUT_SECONDS))
        filename = save_audio_bytes(audio_bytes, prefix="songgen_full_new", ext="wav")
        rel_path = f"static/audio/{filename}"

        # best-effort: parse duration from wav header
        audio_abs = Path(rel_path)
        if not audio_abs.is_absolute():
            audio_abs = Path.cwd() / audio_abs
        try:
            with wave.open(str(audio_abs), "rb") as wf:
                sr = int(wf.getframerate())
                frames = int(wf.getnframes())
                actual_duration = frames / float(sr) if sr else float(duration_sec)
        except Exception:
            sr = 48000
            actual_duration = float(duration_sec)

        print(
            f"[generation_service] (songgen) Generated file {filename}, "
            f"duration ≈ {actual_duration:.2f}s, sr={sr}, job_id={job_id}"
        )

        return GenerateResult(
            filename=filename,
            rel_path=rel_path,
            duration_sec=actual_duration,
            sample_rate=sr,
            model_name="songgen_full_new",
        )

    # 否则走原 MusicGen（本地或旧 REMOTE_INFERENCE_URL clip 级转发）
    gen = get_generator(model_name)
    cfg = GenerateConfig(prompt_zh=prompt_zh, duration_sec=duration_sec, model_name=model_name)
    waveform: np.ndarray = gen.generate_from_zh(cfg)
    sr: int = gen.sample_rate
    actual_duration = waveform.shape[1] / sr

    filename = save_audio_waveform(waveform, sr, prefix=model_name)  # 文件名带上模型名便于区分
    rel_path = f"static/audio/{filename}"

    print(f"[generation_service] Generated file {filename}, duration ≈ {actual_duration:.2f}s, sr={sr}")
    return GenerateResult(
        filename=filename,
        rel_path=rel_path,
        duration_sec=actual_duration,
        sample_rate=sr,
        model_name=model_name,
    )
