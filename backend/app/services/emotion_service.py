# -*- coding: utf-8 -*-
"""
Emotion analysis helper using a fine-tuned MERT classifier.

权重路径读取 settings.MODEL_WEIGHTS_DIR（默认 model_weights），避免与 ORM 模型目录混放。
"""

from pathlib import Path
from typing import Dict, List, Tuple

import librosa
import numpy as np
import torch

from app.core.config import settings
from model_weights.mert_finetune import MERTForEmotionClassification

# ================== 基本配置 ==================

SAMPLE_RATE = 16000
CLIP_DURATION = 10.0  # 秒
STRIDE = 5.0  # 秒
NUM_CLASSES = 8

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

MODEL_CHECKPOINT = Path(settings.MODEL_WEIGHTS_DIR) / "mert_emotion_jamendo_8class_best.pth"

# ================== 四象限（VA）计算调参 ==================
#
# 目的：
# - 概率加权平均会产生“重心效应”，让 valence/arousal 更容易靠近 0.5（映射到前端 [-1,1] 就贴近 0）
# - 通过「概率锐化 + 去中心化拉伸」来让分布更“铺开”，但仍然完全基于 probs 与 EMOTION_TO_AV（不做随意加大 y）
#
# 防止 Codex 走偏：不要引入与概率/EMOTION_TO_AV 无关的偏移项；只允许锐化与中心拉伸 + clip。
#
# 建议范围（更稳）：gamma ∈ [1.0, 3.0]，scale ∈ [1.0, 1.6]
PROB_SHARPEN_GAMMA = 1.8  # p = p**gamma 后再归一化；gamma 越大越“偏向主导情绪”
VA_STRETCH_SCALE = 1.25  # v/a = 0.5 + (v/a - 0.5)*scale；scale 越大越“远离中心”

# 标签（顺序要和训练时一致）
EMOTION_LABELS_EN = [
    "energetic_inspiring",  # 0 能量/励志
    "happy_joyful",  # 1 欢快/快乐
    "healing_fateful",  # 2 治愈/宿命
    "romantic_tender",  # 3 浪漫/温柔
    "calm_peaceful",  # 4 平静/舒缓
    "sad_regretful",  # 5 悲伤/遗憾
    "mysterious_drama",  # 6 神秘/戏剧
    "epic_grand",  # 7 史诗/宏大
]

EMOTION_LABELS_CN = [
    "能量/励志",
    "欢快/快乐",
    "治愈/宿命",
    "浪漫/温柔",
    "平静/舒缓",
    "悲伤/遗憾",
    "神秘/戏剧",
    "史诗/宏大",
]

# 四象限映射：0~1 的愉悦度(valence)、唤醒度(arousal)
EMOTION_TO_AV = {
    0: (0.80, 0.80),  # 能量/励志
    1: (0.90, 0.70),  # 欢快/快乐
    2: (0.65, 0.45),  # 治愈/宿命
    3: (0.75, 0.40),  # 浪漫/温柔
    4: (0.70, 0.25),  # 平静/舒缓
    5: (0.25, 0.30),  # 悲伤/遗憾
    6: (0.45, 0.65),  # 神秘/戏剧
    7: (0.82, 0.90),  # 史诗/宏大
}

# 互斥情绪对
CONFLICT_PAIRS = [
    (0, 4),  # 能量/励志 vs 平静/舒缓
    (0, 5),  # 能量/励志 vs 悲伤/遗憾
    (1, 5),  # 欢快/快乐 vs 悲伤/遗憾
    (7, 4),  # 史诗/宏大 vs 平静/舒缓
]


# ================== 模型加载 ==================

_model: MERTForEmotionClassification | None = None


def get_model() -> MERTForEmotionClassification:
  global _model
  if _model is None:
    if not MODEL_CHECKPOINT.exists():
      raise FileNotFoundError(
          f"Model checkpoint not found: {MODEL_CHECKPOINT}. "
          "Please place the .pth file under the configured MODEL_WEIGHTS_DIR."
      )
    model = MERTForEmotionClassification(num_classes=NUM_CLASSES)
    state_dict = torch.load(MODEL_CHECKPOINT, map_location=DEVICE)
    model.load_state_dict(state_dict)
    model.to(DEVICE)
    model.eval()
    _model = model
    print(f"[emotion_service] Model loaded from {MODEL_CHECKPOINT} on {DEVICE}")
  return _model


# ================== 工具函数 ==================

def slice_audio_with_times(
    y: np.ndarray,
    sr: int,
    clip_duration: float = CLIP_DURATION,
    stride: float = STRIDE,
) -> List[Tuple[float, float, float, np.ndarray]]:
  """
  把整段音频切成多个 [start_time, end_time, center_time, waveform]。
  center_time 用 segment 的 start，减少前端滞后感。
  """
  clip_samples = int(clip_duration * sr)
  stride_samples = int(stride * sr)
  total_len = len(y)

  segments = []

  if total_len < clip_samples:
    pad_len = clip_samples - total_len
    y_padded = np.pad(y, (0, pad_len), mode="constant")
    start_t = 0.0
    end_t = clip_duration
    center_t = start_t
    segments.append((start_t, end_t, center_t, y_padded))
    return segments

  for start_sample in range(0, total_len - clip_samples + 1, stride_samples):
    end_sample = start_sample + clip_samples
    seg = y[start_sample:end_sample]
    start_t = start_sample / sr
    end_t = end_sample / sr
    center_t = start_t
    segments.append((start_t, end_t, center_t, seg))

  return segments


def probs_to_intensity(probs: np.ndarray) -> float:
  probs = probs.astype(float)
  probs = probs / (probs.sum() + 1e-8)
  arousal_arr = np.array([EMOTION_TO_AV[i][1] for i in range(NUM_CLASSES)], dtype=float)
  intensity = float((probs * arousal_arr).sum())
  return intensity


def intensity_to_level(x: float) -> str:
  if x < 0.2:
    return "低"
  elif x < 0.4:
    return "中低"
  elif x < 0.6:
    return "中"
  elif x < 0.8:
    return "中高"
  else:
    return "高"


def volatility_from_series(series: np.ndarray) -> str:
  if len(series) < 2:
    return "低"
  diffs = np.abs(np.diff(series))
  mean_diff = float(diffs.mean())

  if mean_diff < 0.05:
    return "低"
  elif mean_diff < 0.12:
    return "中"
  elif mean_diff < 0.2:
    return "中高"
  else:
    return "高"


def resolve_conflicts(
    probs: np.ndarray,
    strong_thresh: float = 0.5,
    suppress_ratio: float = 0.3,
) -> np.ndarray:
  """
  对明显互斥的情绪做简单逻辑修正：
  - 如果互斥对中的某一类 >= strong_thresh，就把另外一类乘以 suppress_ratio。
  """
  p = probs.astype(float).copy()
  for i, j in CONFLICT_PAIRS:
    pi, pj = p[i], p[j]
    if pi < strong_thresh and pj < strong_thresh:
      continue

    if pi >= pj:
      p[j] *= suppress_ratio
    else:
      p[i] *= suppress_ratio

  p = p / (p.sum() + 1e-8)
  return p


def _normalize_probs(p: np.ndarray) -> np.ndarray:
  p = np.asarray(p, dtype=float)
  p = np.clip(p, 0.0, None)
  s = float(p.sum())
  if not np.isfinite(s) or s <= 0:
    return np.full_like(p, 1.0 / max(1, p.size), dtype=float)
  return p / s


def sharpen_probs(p: np.ndarray, gamma: float = PROB_SHARPEN_GAMMA) -> np.ndarray:
  """
  概率锐化：让强的更强、弱的更弱，降低“重心效应”。
  p = p**gamma -> normalize
  """
  p = _normalize_probs(p)
  g = float(gamma)
  if not np.isfinite(g) or g <= 0:
    g = 1.0
  p = np.power(p, g)
  return _normalize_probs(p)


def stretch_around_center(x: float, scale: float = VA_STRETCH_SCALE, center: float = 0.5) -> float:
  """
  去中心化/拉伸：将 x 以 center 为中心做线性拉伸，再 clip 到 [0,1]。
  x' = center + (x - center) * scale
  """
  s = float(scale)
  if not np.isfinite(s) or s <= 0:
    s = 1.0
  y = float(center + (float(x) - center) * s)
  if not np.isfinite(y):
    y = float(center)
  return float(np.clip(y, 0.0, 1.0))


# ================== 核心接口 ==================

def analyze_music(file_path: str) -> Dict:
  model = get_model()

  y, sr = librosa.load(file_path, sr=SAMPLE_RATE, mono=True)
  duration = len(y) / SAMPLE_RATE

  seg_infos = slice_audio_with_times(y, sr=SAMPLE_RATE)

  segment_results: List[Dict] = []
  all_probs: List[np.ndarray] = []

  max_samples = int(CLIP_DURATION * SAMPLE_RATE)

  for (start_t, end_t, center_t, seg_wave) in seg_infos:
    if len(seg_wave) > max_samples:
      seg_wave = seg_wave[:max_samples]
    elif len(seg_wave) < max_samples:
      seg_wave = np.pad(seg_wave, (0, max_samples - len(seg_wave)), mode="constant")

    x = torch.from_numpy(seg_wave).float().unsqueeze(0).to(DEVICE)

    with torch.no_grad():
      logits = model(x)  # [1, 8]
      probs = torch.sigmoid(logits)[0].cpu().numpy()  # [8]

    probs = probs / (probs.sum() + 1e-8)
    # 做一次互斥修正，避免高潮段「高能量 + 高平静」这类情况
    probs = resolve_conflicts(probs, strong_thresh=0.5, suppress_ratio=0.3)

    all_probs.append(probs)

    dominant_idx = int(probs.argmax())
    intensity = probs_to_intensity(probs)
    intensity_level = intensity_to_level(intensity)

    segment_results.append(
        {
            "start": float(start_t),
            "end": float(end_t),
            "center": float(center_t),
            "probs": probs.tolist(),
            "dominant_idx": dominant_idx,
            "dominant_label_en": EMOTION_LABELS_EN[dominant_idx],
            "dominant_label_cn": EMOTION_LABELS_CN[dominant_idx],
            "intensity": float(intensity),
            "intensity_level": intensity_level,
        }
    )

  if not all_probs:
    return {
        "labels_en": EMOTION_LABELS_EN,
        "labels_cn": EMOTION_LABELS_CN,
        "segments": [],
        "overall_distribution": {},
        "quadrant": {
            "valence": 0.5,
            "arousal": 0.5,
            "dominant_label_en": None,
            "dominant_label_cn": None,
        },
        "stats": {
            "avg_intensity": 0.0,
            "avg_intensity_level": "低",
            "intensity_volatility": "低",
            "duration": float(duration),
        },
    }

  all_probs_arr = np.stack(all_probs, axis=0)  # [N, 8]
  mean_probs = all_probs_arr.mean(axis=0)
  mean_probs = _normalize_probs(mean_probs)

  overall_distribution = {EMOTION_LABELS_EN[i]: float(mean_probs[i]) for i in range(NUM_CLASSES)}

  valence_arr = np.array([EMOTION_TO_AV[i][0] for i in range(NUM_CLASSES)], dtype=float)
  arousal_arr = np.array([EMOTION_TO_AV[i][1] for i in range(NUM_CLASSES)], dtype=float)

  # A. 概率锐化（必须）
  sharp_probs = sharpen_probs(mean_probs, gamma=PROB_SHARPEN_GAMMA)
  # 锐化后再做加权平均
  raw_valence = float((sharp_probs * valence_arr).sum())
  raw_arousal = float((sharp_probs * arousal_arr).sum())

  # B. 去中心化/拉伸（必须）
  overall_valence = stretch_around_center(raw_valence, scale=VA_STRETCH_SCALE, center=0.5)
  overall_arousal = stretch_around_center(raw_arousal, scale=VA_STRETCH_SCALE, center=0.5)

  dom_idx = int(mean_probs.argmax())

  intensities = np.array([seg["intensity"] for seg in segment_results], dtype=float)
  avg_intensity = float(intensities.mean())
  avg_intensity_level = intensity_to_level(avg_intensity)
  volatility = volatility_from_series(intensities)

  # 方便验收：给出 segments arousal（用 intensity 近似，计算口径一致）
  seg_arousal_mean = float(np.nanmean(intensities)) if intensities.size else 0.0
  seg_arousal_var = float(np.nanvar(intensities)) if intensities.size else 0.0

  if settings.DEBUG:
    def _fmt(arr: np.ndarray) -> str:
      return np.array2string(np.asarray(arr, dtype=float), precision=4, separator=", ", suppress_small=False)

    print("[emotion_service][VA] mean_probs =", _fmt(mean_probs), "sum=", float(mean_probs.sum()))
    print("[emotion_service][VA] sharp_probs=", _fmt(sharp_probs), "sum=", float(sharp_probs.sum()), "gamma=", PROB_SHARPEN_GAMMA)
    print(
        "[emotion_service][VA] raw(v,a)=",
        f"({raw_valence:.4f},{raw_arousal:.4f})",
        "-> stretched/clip scale=",
        VA_STRETCH_SCALE,
        f" => (v,a)=({overall_valence:.4f},{overall_arousal:.4f})",
    )
    print(
        "[emotion_service][VA] segment arousal(mean,var)=",
        f"({seg_arousal_mean:.4f},{seg_arousal_var:.6f})",
        "N=",
        int(intensities.size),
    )

  result: Dict = {
      "labels_en": EMOTION_LABELS_EN,
      "labels_cn": EMOTION_LABELS_CN,
      "segments": segment_results,
      "overall_distribution": overall_distribution,
      "quadrant": {
          "valence": overall_valence,
          "arousal": overall_arousal,
          "dominant_label_en": EMOTION_LABELS_EN[dom_idx],
          "dominant_label_cn": EMOTION_LABELS_CN[dom_idx],
      },
      "stats": {
          "avg_intensity": avg_intensity,
          "avg_intensity_level": avg_intensity_level,
          "intensity_volatility": volatility,
          "segment_arousal_mean": seg_arousal_mean,
          "segment_arousal_var": seg_arousal_var,
          "duration": float(duration),
      },
  }
  return result


if __name__ == "__main__":
  test_path = "test_music.wav"
  if Path(test_path).exists():
    out = analyze_music(test_path)
    import json
    print(json.dumps(out, ensure_ascii=False, indent=2))
  else:
    print("请在项目根目录放一个 test_music.wav 再运行测试")
