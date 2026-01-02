from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Literal

import numpy as np

# 未来可扩展更多模型名称
ModelName = Literal["musicgen_pretrained", "musicgen_finetune", "songgen_full_new"]


@dataclass
class GenerateConfig:
    prompt_zh: str         # 中文描述
    duration_sec: float    # 目标时长（秒）
    model_name: ModelName = "musicgen_pretrained"


class BaseMusicGenerator(ABC):
    """
    所有音乐生成模型需实现：
    - generate_clip_en: 英文 prompt -> 单段音频
    - generate_from_zh: 中文 prompt -> 完整音频（内部完成翻译、多段生成、拼接）
    """

    @property
    @abstractmethod
    def sample_rate(self) -> int:
        """模型生成音频的采样率"""
        ...

    @abstractmethod
    def generate_clip_en(
        self,
        prompt_en: str,
        duration_sec: float,
    ) -> np.ndarray:
        """
        英文 prompt -> 单段音频（不拼接）。
        返回 shape = (channels, samples) 的 float32 波形。
        """
        ...

    @abstractmethod
    def generate_from_zh(
        self,
        cfg: GenerateConfig,
    ) -> np.ndarray:
        """
        中文 prompt -> 完整音频（内部翻译/多段生成/拼接）。
        对外暴露给 FastAPI 的核心入口。
        """
        ...
