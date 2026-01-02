from __future__ import annotations

from functools import lru_cache
from typing import Any

try:
    from transformers import pipeline
except ImportError:
    pipeline = None  # transformers 未安装时占位，便于本地开发


class TranslationNotAvailable(RuntimeError):
    """在缺少 transformers 或模型时调用翻译会抛出该异常。"""


@lru_cache()
def _get_zh_en_translator() -> Any:
    """
    构建一个中->英翻译的 pipeline。
    使用轻量模型 Helsinki-NLP/opus-mt-zh-en。
    """
    if pipeline is None:
        raise TranslationNotAvailable(
            "transformers 未安装，无法构建翻译模型；"
            "请在部署环境安装 requirements.txt 中的依赖后再调用。"
        )

    translator = pipeline(
        task="translation",
        model="Helsinki-NLP/opus-mt-zh-en",
        device=-1,  # 翻译用 CPU 即可
    )
    return translator


def zh2en(text: str) -> str:
    """将中文 prompt 翻译成英文。"""
    if not text.strip():
        return text

    translator = _get_zh_en_translator()
    result = translator(text, max_length=256)[0]["translation_text"]
    return result
