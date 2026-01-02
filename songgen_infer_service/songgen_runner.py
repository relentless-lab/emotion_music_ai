from __future__ import annotations

import asyncio
import json
import os
import re
from pathlib import Path
from typing import Optional

from .config import settings


_STRUCTURE_TAG_RE = re.compile(r"\[(intro|inst|outro|verse|chorus|bridge)[^\]]*\]", re.IGNORECASE)


def _pick_outro_tag(duration_sec: int) -> str:
    # Heuristic: longer clips benefit from a slightly longer outro
    try:
        d = int(duration_sec)
    except Exception:
        d = 0
    return "[outro-medium]" if d >= 120 else "[outro-short]"


def _default_instrumental_description(duration_sec: int) -> str:
    """
    Build a stable instrumental structure.

    Notes from upstream docs:
    - [inst] is less stable, prefer not using it.
    - intro/outro segments are purely instrumental.
    """
    outro = _pick_outro_tag(duration_sec)
    # For longer requests, give a slightly longer intro to reduce "cut-in" feel.
    if int(duration_sec) >= 120:
        return f"[intro-medium] ; {outro}"
    return f"[intro-short] ; {outro}"


def _ensure_outro_segment(text: str, *, duration_sec: int) -> str:
    """Ensure the structured lyric string ends with an outro segment."""
    s = (text or "").strip().rstrip(";").strip()
    if not s:
        return s
    if "[outro" not in s.lower():
        s = f"{s} ; {_pick_outro_tag(duration_sec)}"
    return s


def _normalize_plain_text_to_lyrics(text: str) -> list[str]:
    """
    Convert arbitrary user text into short sentence-like units.
    SongGeneration's input guide prefers '.' as lyric sentence separator.
    """
    s = (text or "").strip()
    if not s:
        return []

    # Split by common sentence separators (zh/en), keep units short-ish.
    parts = re.split(r"[。\r\n]+|[.!?]+", s)
    parts = [p.strip() for p in parts if p.strip()]
    if not parts:
        parts = [s]

    # Cap to avoid extremely long lines
    parts = parts[:12]
    return parts


def _normalize_lyrics(raw: str, *, duration_sec: int) -> str:
    """
    Make gt_lyric robust:
    - If user already uses structure tags ([verse]/[chorus]/...), keep it but ensure an outro.
    - If plain text, wrap it into a simple, stable structure:
      [intro-short] ; [verse] ... . ... . ; [chorus] ... . ... . ; [outro-short|medium]
    """
    text = (raw or "").strip()
    if not text:
        return ""

    if _STRUCTURE_TAG_RE.search(text):
        return _ensure_outro_segment(text, duration_sec=duration_sec)

    parts = _normalize_plain_text_to_lyrics(text)
    # Simple split: first 4 sentences verse, next 4 chorus, fallback by repetition.
    verse_parts = parts[:4]
    chorus_parts = parts[4:8] or parts[:2] or parts[:1]

    verse = ". ".join(verse_parts).strip()
    chorus = ". ".join(chorus_parts).strip()

    if verse and not verse.endswith("."):
        verse += "."
    if chorus and not chorus.endswith("."):
        chorus += "."

    outro = _pick_outro_tag(duration_sec)
    return f"[intro-short] ; [verse] {verse} ; [chorus] {chorus} ; {outro}"


def _pick_best_output_audio(
    paths: list[Path],
    *,
    instrumental: bool,
    vocal_only: bool,
    separate: bool,
) -> Path:
    """
    SongGeneration may write multiple files under audios/ depending on flags or script versions
    (e.g. mix + stems). We want:
    - instrumental: prefer bgm/instrumental track
    - vocal_only: prefer vocal/acap track
    - normal vocal song: prefer the full mix (avoid vocal-only stems)
    """
    if not paths:
        raise ValueError("no candidate audio paths")
    if len(paths) == 1:
        return paths[0]

    def score(p: Path) -> tuple[int, int, str]:
        name = p.name.lower()
        s = 0

        # Prefer "mix"/"full"/"song" when generating a normal vocal song
        if (not instrumental) and (not vocal_only) and (not separate):
            if any(k in name for k in ("mix", "full", "song", "all")):
                s += 50
            # Penalize vocal-only stems
            if any(k in name for k in ("vocal_only", "acap", "a_cappella", "a-cappella", "vocals_only")):
                s -= 80
            if any(k in name for k in ("vocal", "vocals")):
                s -= 30
            # Prefer a file name without obvious stem suffixes
            if not any(k in name for k in ("bgm", "inst", "instrument", "vocal", "vocals", "acap", "sep", "separate")):
                s += 10

        # Instrumental preference
        if instrumental:
            if any(k in name for k in ("bgm", "instrumental", "inst")):
                s += 50
            if any(k in name for k in ("vocal", "vocals", "acap", "a_cappella", "a-cappella")):
                s -= 80

        # Vocal-only preference
        if vocal_only:
            if any(k in name for k in ("vocal_only", "acap", "a_cappella", "a-cappella")):
                s += 60
            if any(k in name for k in ("vocal", "vocals")):
                s += 20
            if any(k in name for k in ("bgm", "instrumental", "inst")):
                s -= 60

        # If separate requested, still prefer a "mix/full" if present; otherwise pick a reasonable default.
        if separate:
            if any(k in name for k in ("mix", "full", "song", "all")):
                s += 20

        # Tie-breakers: prefer shorter names (often the main output), then lexicographic.
        return (s, -len(name), name)

    return sorted(paths, key=score, reverse=True)[0]


def _build_jsonl_line(
    *,
    idx: str,
    prompt: str,
    style: Optional[str],
    duration_sec: int,
    seed: Optional[int],
    separate: bool,
    instrumental: bool,
    vocal_only: bool,
    lyrics: Optional[str],
) -> str:
    """
    写入单条 jsonl。
    注：不同版本 songgeneration 的字段名可能略有不同，这里尽量保留通用字段。
    """
    prompt = (prompt or "").strip()
    style = (style or "").strip()
    lyrics = (lyrics or "").strip()

    # ✅ 纯音乐兜底结构（避免 prompt 为空时效果/稳定性差）
    if prompt:
        # 给模型一个明确的“收尾”暗示，减少突兀结尾
        description = prompt
        if instrumental and ("[outro" not in description.lower()):
            description = f"{description} ; {_pick_outro_tag(duration_sec)}"
    else:
        description = _default_instrumental_description(duration_sec)

    # ✅ 关键：某些版本 generate.py 强依赖 idx / gt_lyric，否则会 KeyError
    if instrumental:
        gt_lyric = ""
        # 强制把“无歌词”信号写进 style/type_info
        if style:
            type_info = f"{style}, purely instrumental, no vocals, no singing, no lyrics"
        else:
            type_info = "purely instrumental, no vocals, no singing, no lyrics"
    elif vocal_only:
        # 纯人声：歌词仍然有意义（a cappella），也做结构化兜底
        raw = lyrics or prompt
        gt_lyric = _normalize_lyrics(raw, duration_sec=duration_sec)
        type_info = style or "vocal only, a cappella"
    else:
        # vocal：优先使用 lyrics；没有就回退到 prompt
        raw = lyrics or prompt
        gt_lyric = _normalize_lyrics(raw, duration_sec=duration_sec)
        type_info = style or "vocal"

    payload = {
        "idx": idx,
        "gt_lyric": gt_lyric,
        # ✅ Official field name in SongGeneration repo (some versions primarily read this)
        # Keep as a plain comma-separated tag string.
        "descriptions": type_info,
        # 兼容一些版本读取 prompt/style/duration 的口径
        "prompt": prompt,
        "style": style,
        "duration_sec": int(duration_sec),
        "seed": seed,
        "separate": bool(separate),
        # 兼容一些版本读取 text.description/type_info 的口径
        "text": {
            "description": description,
            "type_info": type_info,
        },
    }
    return json.dumps(payload, ensure_ascii=False)


async def _run_cmd(
    cmd: list[str],
    *,
    cwd: str,
    log_path: Path,
    timeout_seconds: int,
) -> None:
    log_path.parent.mkdir(parents=True, exist_ok=True)

    env = os.environ.copy()
    if settings.SONGGEN_ENV_BIN:
        env["PATH"] = f"{settings.SONGGEN_ENV_BIN}:{env.get('PATH', '')}"

    with log_path.open("ab") as f:
        f.write(b"\n\n===== RUN =====\n")
        f.write(("CWD: " + str(cwd) + "\n").encode("utf-8", errors="ignore"))
        if settings.SONGGEN_ENV_BIN:
            f.write(("ENV.PATH: " + env.get("PATH", "") + "\n").encode("utf-8", errors="ignore"))
        f.write(("CMD: " + " ".join(cmd) + "\n").encode("utf-8", errors="ignore"))
        f.flush()

        proc = await asyncio.create_subprocess_exec(
            *cmd,
            cwd=cwd,
            env=env,
            stdout=f,
            stderr=f,
        )
        try:
            await asyncio.wait_for(proc.wait(), timeout=timeout_seconds)
        except TimeoutError:
            proc.kill()
            raise RuntimeError(f"songgen job timeout after {timeout_seconds}s")

        if proc.returncode != 0:
            raise RuntimeError(f"songgen command failed with code={proc.returncode} (see logs.txt)")


async def run_songgen_job(
    *,
    job_dir: str,
    prompt: str,
    style: Optional[str],
    duration_sec: int,
    fmt: str,
    seed: Optional[int],
    separate: bool,
    instrumental: bool,
    vocal_only: bool,
    lyrics: Optional[str],
    timeout_seconds: int,
) -> str:
    """
    - 写 jsonl
    - 调用 bash generate.sh ...（参数结构不改）
    - 找到 audios/*.flac
    - 如需 wav，则 ffmpeg 转码，保留 flac
    - 返回最终音频文件路径（绝对路径）
    """
    fmt = (fmt or settings.SONGGEN_DEFAULT_FORMAT or "wav").lower()
    if fmt not in {"wav", "flac"}:
        raise ValueError("format must be wav or flac")

    job_path = Path(job_dir)
    job_path.mkdir(parents=True, exist_ok=True)

    input_jsonl = job_path / "input.jsonl"
    save_dir = job_path
    log_path = job_path / "logs.txt"

    idx = job_path.name
    line = _build_jsonl_line(
        idx=idx,
        prompt=prompt,
        style=style,
        duration_sec=duration_sec,
        seed=seed,
        separate=separate,
        instrumental=instrumental,
        vocal_only=vocal_only,
        lyrics=lyrics,
    )
    input_jsonl.write_text(line + "\n", encoding="utf-8")

    # 必须按此结构执行：bash generate.sh songgeneration_base_new <input_jsonl> <save_dir> --low_mem --not_use_flash_attn
    cmd = [
        "bash",
        "generate.sh",
        settings.SONGGEN_MODEL_NAME,
        str(input_jsonl),
        str(save_dir),
        "--low_mem",
        "--not_use_flash_attn",
    ]

    # ---- 关键：用官方 flags 硬控制输出形态（比提示词可靠）----
    # - instrumental -> --bgm（纯音乐）
    # - vocal_only   -> --vocal（纯人声）
    # - separate     -> --separate（分离人声/伴奏）
    # 注：互斥关系在 API 层已校验，这里按优先级附加即可。
    if instrumental:
        cmd.append("--bgm")
    elif vocal_only:
        cmd.append("--vocal")
    elif separate:
        cmd.append("--separate")

    await _run_cmd(cmd, cwd=settings.SONGGEN_WORKDIR, log_path=log_path, timeout_seconds=timeout_seconds)

    # 输出文件名不固定，必须 glob
    audios_dir = job_path / "audios"
    flacs = sorted(audios_dir.glob("*.flac"))
    if not flacs:
        raise RuntimeError(f"no output flac found under {job_path}/audios (see logs.txt)")

    flac_path = _pick_best_output_audio(
        flacs,
        instrumental=bool(instrumental),
        vocal_only=bool(vocal_only),
        separate=bool(separate),
    )
    try:
        with log_path.open("ab") as f:
            f.write(
                (
                    f"\nPICK_AUDIO: candidates={[p.name for p in flacs]} "
                    f"picked={flac_path.name} instrumental={bool(instrumental)} "
                    f"vocal_only={bool(vocal_only)} separate={bool(separate)}\n"
                ).encode("utf-8", errors="ignore")
            )
    except Exception:
        pass
    if fmt == "flac":
        # 可选：对 flac 也做淡出/裁剪（不转 wav）
        out_path = await _postprocess_audio(
            input_path=flac_path,
            job_path=job_path,
            log_path=log_path,
            timeout_seconds=timeout_seconds,
            duration_sec=duration_sec,
            fade_out=bool(getattr(settings, "SONGGEN_FADE_OUT", True)),
            fade_out_seconds=float(getattr(settings, "SONGGEN_FADE_OUT_SECONDS", 4.0)),
            trim_to_duration=bool(getattr(settings, "SONGGEN_TRIM_TO_DURATION", True)),
            codec="flac",
        )
        return str(out_path)

    # 转码 wav，保留 flac
    wav_path = flac_path.with_suffix(".wav")
    ffmpeg_cmd = ["ffmpeg", "-y", "-i", str(flac_path), str(wav_path)]
    await _run_cmd(ffmpeg_cmd, cwd=str(job_path), log_path=log_path, timeout_seconds=timeout_seconds)
    if not wav_path.exists():
        raise RuntimeError("ffmpeg conversion failed: wav not found (see logs.txt)")

    out_path = await _postprocess_audio(
        input_path=wav_path,
        job_path=job_path,
        log_path=log_path,
        timeout_seconds=timeout_seconds,
        duration_sec=duration_sec,
        fade_out=bool(getattr(settings, "SONGGEN_FADE_OUT", True)),
        fade_out_seconds=float(getattr(settings, "SONGGEN_FADE_OUT_SECONDS", 4.0)),
        trim_to_duration=bool(getattr(settings, "SONGGEN_TRIM_TO_DURATION", True)),
        codec="pcm_s16le",
    )
    return str(out_path)


async def _postprocess_audio(
    *,
    input_path: Path,
    job_path: Path,
    log_path: Path,
    timeout_seconds: int,
    duration_sec: int,
    fade_out: bool,
    fade_out_seconds: float,
    trim_to_duration: bool,
    codec: str,
) -> Path:
    """
    后处理：裁剪到 duration_sec（当输出更长时），并在结尾淡出，改善“突然断掉”。

    注意：如果模型输出比 duration_sec 短，无法凭空补齐（除非 padding 静音）；这里保持原长度 + 淡出。
    """
    if not input_path.exists():
        return input_path

    # 如果什么都不做，直接返回
    if (not fade_out) and (not trim_to_duration):
        return input_path

    out_path = job_path / "audios" / f"{job_path.name}{input_path.suffix}"
    if out_path.resolve() == input_path.resolve():
        # 避免覆盖输入文件导致 ffmpeg 失败
        out_path = input_path.with_name(input_path.stem + "_post" + input_path.suffix)

    ffmpeg_cmd: list[str] = ["ffmpeg", "-y", "-i", str(input_path)]

    # 只裁剪“过长”的情况很难在不读时长的前提下判断；这里直接按请求时长裁剪。
    # 若输出更短，ffmpeg 会按实际长度结束，不会报错。
    if trim_to_duration and duration_sec > 0:
        ffmpeg_cmd += ["-t", str(int(duration_sec))]

    filters: list[str] = []
    if fade_out and fade_out_seconds and float(fade_out_seconds) > 0:
        # 关键：必须指定 st（start time），否则 ffmpeg 会从 0 秒开始淡出，导致“前几秒有声，后面全静音”
        # 我们按目标时长在末尾淡出：st = max(0, duration_sec - fade_out_seconds)
        d = float(fade_out_seconds)
        st = max(0.0, float(max(0, int(duration_sec))) - d)
        filters.append(f"afade=t=out:st={st:.3f}:d={d:.3f}")

    if filters:
        ffmpeg_cmd += ["-af", ",".join(filters)]

    # codec：wav 用 pcm_s16le；flac 用 flac
    if codec:
        ffmpeg_cmd += ["-c:a", codec]

    ffmpeg_cmd.append(str(out_path))

    await _run_cmd(ffmpeg_cmd, cwd=str(job_path), log_path=log_path, timeout_seconds=timeout_seconds)
    if out_path.exists():
        return out_path
    return input_path


