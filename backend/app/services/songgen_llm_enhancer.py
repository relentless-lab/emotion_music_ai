from __future__ import annotations

import json
import re
from dataclasses import dataclass

from openai import OpenAI

from app.core.config import settings


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
        "- descriptions: concise English tags (genre, mood, instruments, arrangement, tempo/BPM if known).\n"
        "- Avoid negation like 'no drums/no vocals'. Prefer positive instructions.\n"
        "- If user references a famous song/anime style: DO NOT copy lyrics, DO NOT mention artist names.\n"
        "  Translate into generic tags like 'western pop, acoustic guitar, duet, nostalgic, 2010s' etc.\n"
        "- If lyrics is requested: generate ORIGINAL lyrics and follow SongGeneration format:\n"
        "  - use [verse], [chorus], [bridge], and optionally [intro-short]/[outro-short]\n"
        "  - sections separated by ' ; '\n"
        "  - within lyrical sections, sentences separated by '.'\n"
        "  - keep length reasonable for duration\n"
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


