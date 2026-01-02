# backend/app/models/musicgen_pretrained.py (merged into main app)

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import numpy as np

from app.core.config import settings
from app.core.device import DeviceConfig, resolve_device
from app.musicgen.base import BaseMusicGenerator, GenerateConfig
from app.services.audio_stitch import crossfade_concat
from app.utils.translation import TranslationNotAvailable, zh2en

try:
    import torch
    from transformers import AutoProcessor, MusicgenForConditionalGeneration
except ImportError:
    torch = None
    AutoProcessor = None
    MusicgenForConditionalGeneration = None


@dataclass
class MusicGenPretrainedConfig:
    # 默认为 medium，可按显存改为 musicgen-small
    model_id: str = settings.MUSICGEN_MODEL_ID
    # 单段最大时长（秒），用于控制 generate_clip_en
    max_single_clip_sec: float = settings.MUSICGEN_MAX_SINGLE_CLIP_SEC
    # 粗略控制 tokens 数量：秒数 * tokens_per_second ≈ max_new_tokens
    tokens_per_second: float = settings.MUSICGEN_TOKENS_PER_SECOND


class MusicGenPretrained(BaseMusicGenerator):
    """
    使用 transformers 封装的 MusicGen 预训练模型。
    """

    def __init__(
        self,
        cfg: Optional[MusicGenPretrainedConfig] = None,
        device_cfg: Optional[DeviceConfig] = None,
    ) -> None:
        if (
            torch is None
            or AutoProcessor is None
            or MusicgenForConditionalGeneration is None
        ):
            raise RuntimeError(
                "缺少 transformers/torch 相关依赖；请在部署环境安装 requirements.txt 中的依赖后再实例化 MusicGenPretrained。"
            )

        self.cfg = cfg or MusicGenPretrainedConfig()
        self.device_cfg = device_cfg or DeviceConfig(
            use_cuda_if_available=settings.MUSICGEN_USE_CUDA_IF_AVAILABLE,
            preferred_device=settings.MUSICGEN_PREFERRED_DEVICE,
        )

        self.device = resolve_device(self.device_cfg)
        print(f"[MusicGenPretrained] Using device: {self.device}")

        # 加载模型和处理器
        print(f"[MusicGenPretrained] Loading model: {self.cfg.model_id} ...")
        self.model = MusicgenForConditionalGeneration.from_pretrained(
            self.cfg.model_id
        ).to(self.device)

        self.processor = AutoProcessor.from_pretrained(self.cfg.model_id)

        # sample_rate 从模型 config 读取
        self._sample_rate: int = int(self.model.config.audio_encoder.sampling_rate)
        print(f"[MusicGenPretrained] Sample rate = {self._sample_rate}")

    # ========= BaseMusicGenerator 接口实现 =========

    @property
    def sample_rate(self) -> int:
        return self._sample_rate

    def generate_clip_en(
        self,
        prompt_en: str,
        duration_sec: float,
    ) -> np.ndarray:
        """
        英文 prompt -> 单段音频（不拼接）。
        返回 shape = (channels, samples) 的 float32 波形。
        """
        if duration_sec <= 0:
            raise ValueError("duration_sec must be > 0")

        # 限制单段最大时长，避免超出 MusicGen 的 token 限制
        duration_sec = float(min(duration_sec, self.cfg.max_single_clip_sec))

        # 约束 max_new_tokens
        max_new_tokens = int(duration_sec * self.cfg.tokens_per_second)
        print(
            f"[MusicGenPretrained] Generating single clip: "
            f"{duration_sec:.1f}s, max_new_tokens={max_new_tokens}"
        )

        # 编码文本
        inputs = self.processor(
            text=[prompt_en],
            padding=True,
            return_tensors="pt",
        ).to(self.device)

        # 生成
        with torch.no_grad():
            generated_ids = self.model.generate(
                **inputs,
                max_new_tokens=max_new_tokens,
            )

        # 解码为波形，shape=(channels, samples)
        audio_values = self.processor.batch_decode(
            generated_ids,
            return_tensors="pt",
        )[0]

        # 兼容不同 transformers 版本返回类型
        if torch is not None and torch.is_tensor(audio_values):
            audio_np = (
                audio_values.detach()
                .cpu()
                .numpy()
                .astype("float32")
            )
        else:
            audio_np = np.asarray(audio_values, dtype="float32")

        print(f"[MusicGenPretrained] Generated clip shape = {audio_np.shape}")
        return audio_np

    def generate_from_zh(
        self,
        cfg: GenerateConfig,
    ) -> np.ndarray:
        """
        中文 prompt -> 翻译 -> 多段英文生成 + crossfade 拼接 -> 精确裁剪到目标时长。
        """
        prompt_zh = cfg.prompt_zh.strip()
        if not prompt_zh:
            raise ValueError("prompt_zh 不能为空")

        # 1) 规范时长：限制在 5~120 秒
        target_duration_sec = float(cfg.duration_sec)
        target_duration_sec = max(5.0, min(target_duration_sec, 120.0))

        # 2) 中 -> 英翻译
        try:
            prompt_en = zh2en(prompt_zh)
        except TranslationNotAvailable as e:
            print(
                f"[MusicGenPretrained] WARNING: translation not available ({e}), "
                f"using Chinese prompt directly."
            )
            prompt_en = prompt_zh

        print(f"[MusicGenPretrained] ZH prompt: {prompt_zh}")
        print(f"[MusicGenPretrained] EN prompt: {prompt_en}")
        print(f"[MusicGenPretrained] Target duration = {target_duration_sec:.1f}s")

        # 3) 如果目标时长 <= 单段最大长度，直接生成单段
        if target_duration_sec <= self.cfg.max_single_clip_sec:
            audio = self.generate_clip_en(
                prompt_en,
                duration_sec=target_duration_sec,
            )
            return audio

        # 4) 需要多段拼接：设计分段 + crossfade
        sr = self.sample_rate
        overlap_sec = 2.0  # 每段之间交叉淡入淡出 2 秒
        chunk_sec = min(self.cfg.max_single_clip_sec, settings.MUSICGEN_CHUNK_SEC)

        print(
            f"[MusicGenPretrained] Using multi-segment generation: "
            f"chunk_sec={chunk_sec}s, overlap_sec={overlap_sec}s"
        )

        # 为了保证拼完再裁剪时足够长，我们多生成一点
        target_samples_with_margin = int(
            (target_duration_sec + overlap_sec) * sr
        )

        segments = []
        total_samples = 0

        # 循环生成多段，直到累计长度 >= 目标 + overlap
        while total_samples < target_samples_with_margin:
            print(
                f"[MusicGenPretrained] Generating segment #{len(segments) + 1} ..."
            )
            seg = self.generate_clip_en(
                prompt_en,
                duration_sec=chunk_sec,
            )
            segments.append(seg)
            total_samples += seg.shape[1]
            print(
                f"[MusicGenPretrained] Total samples so far = {total_samples}, "
                f"target_with_margin = {target_samples_with_margin}"
            )

        # 5) 使用 crossfade_concat 做平滑拼接
        print("[MusicGenPretrained] Stitching segments with crossfade ...")
        full_audio = crossfade_concat(
            segments,
            sample_rate=sr,
            overlap_sec=overlap_sec,
        )

        # 6) 精确裁剪到目标时长
        max_samples = int(target_duration_sec * sr)
        if full_audio.shape[1] > max_samples:
            full_audio = full_audio[:, :max_samples]
        else:
            print(
                "[MusicGenPretrained] WARNING: 拼接后长度仍不足目标时长；"
                "可以考虑多生成一段再拼接。"
            )

        print(
            f"[MusicGenPretrained] Final audio shape = {full_audio.shape}, "
            f"duration ≈ {full_audio.shape[1] / sr:.2f}s"
        )

        return full_audio
