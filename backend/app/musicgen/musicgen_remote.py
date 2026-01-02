import numpy as np
import requests
import base64
import logging
from typing import Optional

from app.core.config import settings
from app.musicgen.musicgen_pretrained import MusicGenPretrained, MusicGenPretrainedConfig
from app.musicgen.base import GenerateConfig

logger = logging.getLogger(__name__)

class MusicGenRemote(MusicGenPretrained):
    """
    远程 MusicGen 生成器：
    继承自 MusicGenPretrained 以复用其分段拼接 (generate_from_zh) 逻辑，
    但将最核心的单段生成 (generate_clip_en) 转发给远程 GPU 服务器。
    """
    def __init__(
        self,
        cfg: Optional[MusicGenPretrainedConfig] = None,
        # 远程生成器不需要本地加载模型，因此忽略 device_cfg
        **kwargs
    ) -> None:
        self.cfg = cfg or MusicGenPretrainedConfig()
        self._sample_rate = 32000  # MusicGen 默认采样率
        logger.info(f"[MusicGenRemote] Initialized. Remote URL: {settings.REMOTE_INFERENCE_URL}")

    @property
    def sample_rate(self) -> int:
        return self._sample_rate

    def generate_clip_en(
        self,
        prompt_en: str,
        duration_sec: float,
    ) -> np.ndarray:
        """
        通过 HTTP 请求将生成任务发送到远程 A10 服务器。
        """
        if not settings.REMOTE_INFERENCE_URL:
            raise RuntimeError("REMOTE_INFERENCE_URL is not configured.")

        logger.info(f"[MusicGenRemote] Sending request to remote GPU: {duration_sec}s, prompt: {prompt_en[:30]}...")
        
        payload = {
            "prompt_en": prompt_en,
            "duration_sec": duration_sec,
            "tokens_per_second": self.cfg.tokens_per_second
        }
        
        try:
            response = requests.post(
                f"{settings.REMOTE_INFERENCE_URL.rstrip('/')}/generate_clip", 
                json=payload,
                timeout=300, # 给予足够的超时时间
                proxies={"http": None, "https": None}  # 绕过本地代理，直接连接远程服务器
            )
            response.raise_for_status()
            
            data = response.json()
            waveform_bytes = base64.b64decode(data["waveform"])
            waveform = np.frombuffer(waveform_bytes, dtype=np.float32)
            
            # 恢复 shape 为 (channels, samples)，MusicGen 通常是 (1, N)
            shape = data.get("shape", [1, -1])
            if len(shape) == 1:
                return waveform.reshape(1, -1)
            return waveform.reshape(*shape)

        except Exception as e:
            logger.error(f"[MusicGenRemote] Remote generation failed: {e}")
            raise RuntimeError(f"远程生成失败: {e}")

