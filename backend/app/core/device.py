from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class DeviceConfig:
    use_cuda_if_available: bool = True
    preferred_device: Optional[str] = None  # e.g. "cpu" / "cuda:0"


def resolve_device(cfg: DeviceConfig) -> str:
    try:
        import torch  # type: ignore
    except ImportError:
        # Local dev without torch: default to CPU to avoid import errors.
        return "cpu"

    if cfg.preferred_device is not None:
        return cfg.preferred_device

    if cfg.use_cuda_if_available and torch.cuda.is_available():
        return "cuda"
    return "cpu"
