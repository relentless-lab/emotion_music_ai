from typing import Any, Dict, Optional

from openai import AsyncOpenAI

from app.core.config import settings


def _get_client() -> Optional[AsyncOpenAI]:
  """Initialize OpenAI-compatible async client; return None if not configured."""
  if not settings.OPENAI_API_KEY:
    return None
  return AsyncOpenAI(api_key=settings.OPENAI_API_KEY, base_url=settings.OPENAI_API_BASE)


async def summarize_emotion(analysis: Dict[str, Any]) -> str:
  """
  Generate a short Chinese summary for emotion analysis results using an LLM.
  Falls back to a placeholder when LLM is not configured or call fails.
  """
  client = _get_client()
  if client is None:
    return "（占位）整体上，这段音乐以积极情绪为主，情绪起伏平稳，适合做背景音乐。"

  prompt = (
      "你是音乐情绪分析助手。下面是某段音乐的情绪分析结果（JSON）：\n\n"
      f"{analysis}\n\n"
      "请用简体中文写一段不超过 200 字的情绪总结，面向普通用户，不提及技术细节或 JSON。"
  )

  try:
    resp = await client.chat.completions.create(  # type: ignore[call-arg]
        model=settings.OPENAI_MODEL,
        messages=[
            {"role": "system", "content": "你是一个专业的音乐情绪分析助手。"},
            {"role": "user", "content": prompt},
        ],
        temperature=0.7,
        max_tokens=300,
    )
  except Exception:
    return "（占位）整体上，这段音乐以积极情绪为主"
  return resp.choices[0].message.content.strip() if resp and resp.choices else ""


async def build_album_cover_prompt(user_music_prompt: str) -> str:
  """
  将“音乐描述”转换为适合图片生成模型（Qwen-image）的英文封面描述 Prompt。
  - 不提及乐器/音乐/声音
  - 只关注画面、氛围、季节、颜色
  - 统一为现代、电影感的专辑封面风格
  """
  client = _get_client()
  base_fallback = (
      "A modern cinematic album cover, soft dreamy colors, abstract landscape, "
      "warm and hopeful atmosphere, high quality digital art, no text, no logo"
  )
  if client is None:
    return base_fallback

  system_prompt = (
      "You are an assistant that converts music descriptions into album cover image prompts.\n\n"
      "Rules:\n"
      "- DO NOT mention musical instruments\n"
      "- DO NOT mention sound, music, or audio\n"
      "- Focus only on visual scene, atmosphere, emotions, season, and color\n"
      "- The style must be consistent: modern, artistic, cinematic album cover\n"
      "- Minimalist composition, no text, no logo, no watermark\n"
      "- The image should look like a professional music album cover\n\n"
      "Output a single English prompt suitable for an image generation model."
  )

  try:
    resp = await client.chat.completions.create(  # type: ignore[call-arg]
        model=settings.OPENAI_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_music_prompt},
        ],
        temperature=0.6,
        max_tokens=280,
    )
  except Exception:
    return base_fallback

  content = resp.choices[0].message.content.strip() if resp and resp.choices else ""
  return content or base_fallback


async def build_music_title(user_music_prompt: str) -> str:
  """
  根据用户输入生成一个更像 Suno 的“歌曲标题”（简短中文）。
  - 输出单行标题，不要引号，不要“标题：”
  - 尽量 4~12 个汉字，避免过长
  """
  client = _get_client()
  if client is None:
    return (user_music_prompt or "").strip()[:12] or "AI 生成作品"

  system_prompt = (
      "你是音乐标题生成助手。\n"
      "请根据用户的音乐描述生成一个简短、有画面感的中文歌曲标题。\n"
      "要求：\n"
      "- 只输出标题本身（单行）\n"
      "- 不要加引号，不要加前缀如“标题：”\n"
      "- 4~12 个汉字为佳，避免过长\n"
  )

  try:
    resp = await client.chat.completions.create(  # type: ignore[call-arg]
        model=settings.OPENAI_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": (user_music_prompt or "").strip()},
        ],
        temperature=0.7,
        max_tokens=40,
    )
  except Exception:
    return (user_music_prompt or "").strip()[:12] or "AI 生成作品"

  title = resp.choices[0].message.content.strip() if resp and resp.choices else ""
  # Post-process: remove wrapping quotes and common prefixes
  title = title.strip().strip('"').strip("“”").strip()
  for prefix in ("标题：", "歌名：", "Title:", "title:"):
    if title.lower().startswith(prefix.lower()):
      title = title[len(prefix):].strip()
  return title[:24] or (user_music_prompt or "").strip()[:12] or "AI 生成作品"
