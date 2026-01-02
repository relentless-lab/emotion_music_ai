from __future__ import annotations

import uuid
from pathlib import Path
from typing import Literal

import numpy as np

from app.core.config import settings

try:
    import soundfile as sf
except ImportError:
    sf = None  # 本地未装依赖时占位，避免 import 失败


# 生成音频统一放在 {STATIC_ROOT}/audio 下
STATIC_ROOT = Path(settings.STATIC_ROOT)
AUDIO_DIR = STATIC_ROOT / "audio"
AUDIO_DIR.mkdir(parents=True, exist_ok=True)


def save_audio_bytes(
    data: bytes,
    *,
    prefix: str = "gen",
    ext: str = "wav",
) -> str:
    """
    保存已编码的音频文件（如远程推理服务返回的 wav/flac bytes）。
    返回文件名（不含路径，如 gen_xxx.wav）。
    """
    filename = f"{prefix}_{uuid.uuid4().hex}.{ext.lstrip('.')}"
    out_path = AUDIO_DIR / filename
    out_path.write_bytes(data)
    print(f"[storage_service] Saved audio bytes to {out_path}")
    return filename


def save_audio_waveform(
    waveform: np.ndarray,
    sample_rate: int,
    prefix: str = "gen",
    ext: Literal["wav"] = "wav",
) -> str:
    """
    将形状为 (channels, samples) 的 waveform 保存为音频文件。
    返回文件名（不含路径，如 gen_xxx.wav）。
    """
    if sf is None:
        raise RuntimeError(
            "soundfile 未安装，无法保存音频文件。"
            "请在部署环境安装 requirements.txt 中的依赖。"
        )

    if waveform.ndim != 2:
        raise ValueError(f"waveform 维度必须为 2，得到 {waveform.shape}")

    if waveform.dtype != np.float32:
        waveform = waveform.astype("float32")

    filename = f"{prefix}_{uuid.uuid4().hex}.{ext}"
    out_path = AUDIO_DIR / filename

    # soundfile 需要 (samples, channels)
    sf.write(str(out_path), waveform.T, sample_rate)

    print(f"[storage_service] Saved audio to {out_path}")
    return filename
