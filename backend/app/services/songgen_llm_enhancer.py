from __future__ import annotations

import json
import re
from dataclasses import dataclass

from openai import OpenAI

from app.core.config import settings

_STRUCTURE_TAG_RE = re.compile(r"\[(intro|outro|verse|chorus|bridge)[^\]]*\]", re.IGNORECASE)


@dataclass(frozen=True)
class SongGenLLMEnhanceResult:
    """
    - descriptions: comma-separated English tags for SongGeneration
    - lyrics: structured lyric string for SongGeneration gt_lyric
    - rewritten_prompt: optional rewritten Chinese prompt (we keep sending original prompt_zh by default)
    """

    descriptions: str | None
    lyrics: str | None
    rewritten_prompt: str | None


def _get_client() -> OpenAI | None:
    if not (settings.OPENAI_API_KEY and settings.OPENAI_API_BASE):
        return None
    return OpenAI(api_key=settings.OPENAI_API_KEY, base_url=settings.OPENAI_API_BASE)


def _strip_control_chars(s: str) -> str:
    # remove control chars but keep common punctuation
    return re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", " ", s)


def _collapse_spaces(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


def sanitize_user_lyrics(raw: str, *, max_chars: int) -> str:
    """
    Make user-provided lyrics robust:
    - normalize punctuation to '.' and ';'
    - normalize newlines/spaces
    - remove weird control chars
    - cap length
    """
    s = (raw or "").strip()
    if not s:
        return ""

    s = s.replace("\r\n", "\n").replace("\r", "\n")
    s = _strip_control_chars(s)

    # Normalize Chinese punctuation to English-style separators
    s = (
        s.replace("；", ";")
        .replace("，", ",")
        .replace("。", ".")
        .replace("！", "!")
        .replace("？", "?")
    )

    # Merge newlines into spaces (avoid breaking tokenization downstream)
    s = re.sub(r"\n+", " ", s)

    # Normalize semicolon spacing
    s = re.sub(r"\s*;\s*", " ; ", s)
    s = _collapse_spaces(s)

    if max_chars > 0 and len(s) > max_chars:
        s = s[:max_chars].rstrip()

    return s


def ensure_structured_lyrics(raw: str, *, duration_sec: int) -> str:
    """
    Ensure lyrics are in SongGeneration gt_lyric structured format.

    - If user/LLM already provides structure tags, keep them but ensure an outro segment exists.
    - If plain text, wrap into a stable template (avoid [inst]) to reduce "sudden stop".
    """
    s = (raw or "").strip()
    if not s:
        return ""

    # Already structured: keep but ensure an outro segment exists.
    if _STRUCTURE_TAG_RE.search(s):
        out = s.strip().rstrip(";").strip()
        if "[outro" not in out.lower():
            # pick outro length by duration
            outro = "[outro-medium]" if int(duration_sec) >= 120 else "[outro-short]"
            out = f"{out} ; {outro}"
        return out

    # Plain text: split into sentence-like parts and allocate into sections.
    # Keep units short-ish to avoid extremely long lines.
    parts = re.split(r"[。\r\n]+|[.!?]+", s)
    parts = [p.strip() for p in parts if p.strip()]
    if not parts:
        parts = [s]
    parts = parts[:18]

    def take(n: int, start: int) -> list[str]:
        if not parts:
            return []
        out = []
        for i in range(n):
            out.append(parts[(start + i) % len(parts)])
        return out

    # Map duration to a stable song form (no [inst]).
    d = int(duration_sec or 0)
    if d <= 75:
        # 60s: intro + verse + chorus + outro
        verse = take(4, 0)
        chorus = take(4, 4)
        outro = "[outro-short]"
        return (
            "[intro-short] ; "
            f"[verse] {'. '.join(verse)}. ; "
            f"[chorus] {'. '.join(chorus)}. ; "
            f"{outro}"
        )
    if d <= 105:
        # 90s: intro + verse + chorus + verse + chorus + outro
        verse1 = take(4, 0)
        chorus1 = take(4, 4)
        verse2 = take(4, 8)
        chorus2 = take(4, 12)
        outro = "[outro-short]"
        return (
            "[intro-short] ; "
            f"[verse] {'. '.join(verse1)}. ; "
            f"[chorus] {'. '.join(chorus1)}. ; "
            f"[verse] {'. '.join(verse2)}. ; "
            f"[chorus] {'. '.join(chorus2)}. ; "
            f"{outro}"
        )

    # 120s+: intro-medium + 2 verse + 3 chorus + bridge + outro-medium
    verse1 = take(4, 0)
    chorus1 = take(4, 4)
    verse2 = take(4, 8)
    chorus2 = take(4, 12)
    bridge = take(3, 16)
    chorus3 = chorus1 or take(4, 0)
    return (
        "[intro-medium] ; "
        f"[verse] {'. '.join(verse1)}. ; "
        f"[chorus] {'. '.join(chorus1)}. ; "
        f"[verse] {'. '.join(verse2)}. ; "
        f"[chorus] {'. '.join(chorus2)}. ; "
        f"[bridge] {'. '.join(bridge)}. ; "
        f"[chorus] {'. '.join(chorus3)}. ; "
        "[outro-medium]"
    )


def _safe_trim(s: str | None, *, max_chars: int) -> str | None:
    if not s:
        return None
    t = _collapse_spaces(_strip_control_chars(s.strip()))
    if max_chars > 0 and len(t) > max_chars:
        t = t[:max_chars].rstrip()
    return t or None


def enhance_for_songgen(
    *,
    prompt_zh: str,
    instrumental: bool,
    duration_sec: int,
    user_style: str | None,
    user_lyrics: str | None,
) -> SongGenLLMEnhanceResult:
    """
    Use Qwen2.5-7B-Instruct (OpenAI-compatible chat completions) to:
    - produce robust English `descriptions` tags for SongGeneration
    - if vocal and user_lyrics missing: generate ORIGINAL, structured lyrics (gt_lyric format)

    Hard constraints:
    - Return STRICT JSON only
    - Do NOT copy lyrics or claim artist names when user references famous songs/anime
    - Avoid negation like "no drums/no vocals" since some music models mis-handle it
    """
    client = _get_client()
    if client is None:
        return SongGenLLMEnhanceResult(descriptions=None, lyrics=None, rewritten_prompt=None)

    prompt_zh = (prompt_zh or "").strip()
    if not prompt_zh:
        return SongGenLLMEnhanceResult(descriptions=None, lyrics=None, rewritten_prompt=None)

    user_style = (user_style or "").strip() or None
    user_lyrics = (user_lyrics or "").strip() or None
    want_lyrics = (not instrumental) and (not user_lyrics)

    # Keep prompts short to reduce hallucination/cost
    prompt_zh = _safe_trim(prompt_zh, max_chars=int(getattr(settings, "SONGGEN_LLM_MAX_PROMPT_CHARS", 800))) or ""

    system = (
        "You are a prompt engineer for Tencent SongGeneration (LeVo).\n"
        "Convert the user's Chinese request into fields that SongGeneration understands.\n"
        "Return STRICT JSON only. No markdown, no extra text.\n\n"
        "Output JSON schema:\n"
        "{\n"
        '  \"descriptions\": \"comma-separated English tags\",\n'
        '  \"lyrics\": \"structured lyric string or null\",\n'
        '  \"rewritten_prompt\": \"optional improved Chinese prompt or null\"\n'
        "}\n\n"
        "Rules:\n"
        "- descriptions: STRICT 6-dimension English tags, comma-separated, in this order:\n"
        "  Gender, Timbre, Genre, Emotion, Instrument, the bpm is N.\n"
        "  Use 1-2 short tokens per dimension. If unknown, omit that dimension.\n"
        "- Avoid negation like 'no drums/no vocals'. Prefer positive instructions.\n"
        "- If user references a famous song/anime style: DO NOT copy lyrics, DO NOT mention artist names.\n"
        "  Translate into generic tags like 'western pop, acoustic guitar, duet, nostalgic, 2010s' etc.\n"
        "- If lyrics is requested: generate ORIGINAL lyrics and follow SongGeneration format:\n"
        "  - use [intro-medium], [verse], [chorus], [bridge], [outro-medium]\n"
        "  - sections separated by ' ; '\n"
        "  - within lyrical sections, sentences separated by '.'\n"
        "  - ensure the lyric ends with an outro segment\n"
        "  - choose structure length to fit duration: 60s=verse+chorus, 90s=verse+chorus+verse+chorus, 120s+=2verse+3chorus+bridge\n"
    )

    user_payload = {
        "user_request_zh": prompt_zh,
        "instrumental": bool(instrumental),
        "duration_sec": int(duration_sec),
        "user_style": user_style,
        "need_lyrics": bool(want_lyrics),
    }

    try:
        resp = client.chat.completions.create(
            model=settings.OPENAI_MODEL,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": json.dumps(user_payload, ensure_ascii=False)},
            ],
            temperature=0.6,
            max_tokens=700 if want_lyrics else 240,
            timeout=float(getattr(settings, "SONGGEN_LLM_TIMEOUT_SECONDS", 40)),
        )
    except Exception:
        return SongGenLLMEnhanceResult(descriptions=None, lyrics=None, rewritten_prompt=None)

    content = (resp.choices[0].message.content or "").strip() if resp and resp.choices else ""
    try:
        data = json.loads(content)
    except Exception:
        return SongGenLLMEnhanceResult(descriptions=None, lyrics=None, rewritten_prompt=None)

    descriptions = _safe_trim(data.get("descriptions"), max_chars=600) if isinstance(data, dict) else None
    rewritten_prompt = _safe_trim(data.get("rewritten_prompt"), max_chars=600) if isinstance(data, dict) else None

    lyrics: str | None = None
    if isinstance(data, dict) and isinstance(data.get("lyrics"), str):
        lyrics = sanitize_user_lyrics(
            data.get("lyrics") or "",
            max_chars=int(getattr(settings, "SONGGEN_LLM_MAX_LYRIC_CHARS", 1200)),
        )
        lyrics = lyrics or None

    return SongGenLLMEnhanceResult(descriptions=descriptions, lyrics=lyrics, rewritten_prompt=rewritten_prompt)


