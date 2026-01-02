from __future__ import annotations

import numpy as np


def crossfade_concat(
    segments: list[np.ndarray],
    sample_rate: int,
    overlap_sec: float = 2.0,
) -> np.ndarray:
    """
    将多段音频做淡入淡出后拼接成一段。
    每段 shape=(channels, samples)，采样率一致。
    """
    if not segments:
        raise ValueError("segments 不能为空")

    if len(segments) == 1:
        return segments[0]

    ch = segments[0].shape[0]
    overlap_samples = int(overlap_sec * sample_rate)

    # 校验
    for i, seg in enumerate(segments):
        if seg.shape[0] != ch:
            raise ValueError(f"第 {i} 段的声道数不一致")
        if seg.shape[1] <= overlap_samples * 2:
            raise ValueError(
                f"segment {i} 太短（长度 {seg.shape[1]}），"
                f"不足以做 {overlap_sec}s 的交叉淡入淡出"
            )

    output = segments[0].copy()

    # 构造淡入/淡出窗
    fade_out = np.linspace(1.0, 0.0, overlap_samples, dtype=np.float32)
    fade_in = np.linspace(0.0, 1.0, overlap_samples, dtype=np.float32)

    for seg in segments[1:]:
        tail = output[:, -overlap_samples:]
        head = seg[:, :overlap_samples]

        mixed = tail * fade_out + head * fade_in

        output[:, -overlap_samples:] = mixed
        output = np.concatenate([output, seg[:, overlap_samples:]], axis=1)

    return output
