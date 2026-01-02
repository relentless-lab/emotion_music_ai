from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class SongGenStyleSuggestion:
    tags: list[str]


def _dedup_tags(tags: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for t in tags:
        key = (t or "").strip().lower()
        if not key:
            continue
        if key in seen:
            continue
        seen.add(key)
        out.append(t.strip())
    return out


def _contains_any(text: str, patterns: list[str]) -> bool:
    s = text or ""
    return any(p in s for p in patterns)


def _extract_bpm(text: str) -> int | None:
    s = text or ""
    # Examples:
    # - BPM120 / bpm 120 / 120bpm / 节拍120 / 速度120
    m = re.search(r"(?i)\b(?:bpm|tempo)\s*[:=]?\s*(\d{2,3})\b", s)
    if not m:
        m = re.search(r"\b(\d{2,3})\s*(?:bpm|BPM)\b", s)
    if not m:
        m = re.search(r"(?:节拍|速度)\s*[:=]?\s*(\d{2,3})", s)
    if not m:
        return None
    try:
        bpm = int(m.group(1))
    except Exception:
        return None
    # keep reasonable ranges
    if 40 <= bpm <= 220:
        return bpm
    return None


def _extract_negative_phrases(text: str) -> list[str]:
    """
    Extract simple negative constraints like:
    - 不要鼓点/别要鼓/无鼓/没有鼓
    - 不要贝斯/无贝斯/没有低音
    Return a list of normalized English tags like "no drums".
    """
    s = (text or "").strip()
    if not s:
        return []

    neg = []

    def has_neg(keyword: str) -> bool:
        # very lightweight; avoid over-engineering
        return (
            f"不要{keyword}" in s
            or f"别{keyword}" in s
            or f"无{keyword}" in s
            or f"没有{keyword}" in s
            or f"不需要{keyword}" in s
        )

    if has_neg("鼓") or has_neg("鼓点") or has_neg("架子鼓"):
        neg.append("no drums")
    if has_neg("贝斯") or has_neg("低音") or has_neg("bass"):
        neg.append("no bass")
    if has_neg("人声") or has_neg("唱") or has_neg("歌词") or has_neg("主唱"):
        neg.append("no vocals")
    if has_neg("说唱") or has_neg("rap"):
        neg.append("no rap")
    if has_neg("电子") or has_neg("合成器"):
        neg.append("no synth")

    return neg


def _is_negated(text: str, keyword: str) -> bool:
    """
    Detect simple local negation patterns around a keyword, e.g.:
    - 不要{keyword} / 别{keyword} / 无{keyword} / 没有{keyword} / 不需要{keyword}
    """
    s = text or ""
    k = keyword or ""
    if not s or not k:
        return False
    return (
        (f"不要{k}" in s)
        or (f"别{k}" in s)
        or (f"无{k}" in s)
        or (f"没有{k}" in s)
        or (f"不需要{k}" in s)
    )


def _match_any_not_negated(text: str, keywords: list[str]) -> bool:
    s = text or ""
    for kw in keywords:
        if not kw:
            continue
        if kw in s and not _is_negated(s, kw):
            return True
    return False


def suggest_songgen_style_tags(prompt_zh: str) -> SongGenStyleSuggestion:
    """
    Deterministic extractor: map common CN keywords to stable English tags.
    This does NOT guarantee the model will follow, but it significantly improves consistency.
    """
    s = (prompt_zh or "").strip()
    if not s:
        return SongGenStyleSuggestion(tags=[])

    tags: list[str] = []

    # ---- season / vibe ----
    if "春" in s or "春天" in s or "春日" in s:
        tags += ["spring"]
    if "夏" in s or "夏天" in s or "夏日" in s:
        tags += ["summer"]
    if "秋" in s or "秋天" in s or "秋日" in s:
        tags += ["autumn"]
    if "冬" in s or "冬天" in s or "冬日" in s:
        tags += ["winter"]

    if _contains_any(s, ["治愈", "疗愈", "治療", "治療系", "温暖", "温柔"]):
        tags += ["healing", "warm", "gentle"]
    if _contains_any(s, ["宁静", "安静", "平静", "舒缓", "放松"]):
        tags += ["calm", "relaxing", "soft"]
    if _contains_any(s, ["忧伤", "伤感", "悲伤", "落寞"]):
        tags += ["sad", "melancholic"]
    if _contains_any(s, ["快乐", "开心", "明亮", "阳光", "轻快"]):
        tags += ["happy", "uplifting", "bright"]
    if _contains_any(s, ["浪漫", "甜蜜", "爱情", "心动"]):
        tags += ["romantic"]
    if _contains_any(s, ["史诗", "恢弘", "壮阔", "宏大"]):
        tags += ["epic", "grand"]
    if _contains_any(s, ["神秘", "诡异", "悬疑", "阴森"]):
        tags += ["mysterious", "dark"]
    if _contains_any(s, ["热血", "燃", "激昂", "能量", "动感"]):
        tags += ["energetic"]

    # ---- tempo hints ----
    if _contains_any(s, ["慢板", "慢速", "舒缓", "慢一点", "缓慢"]):
        tags += ["slow"]
    if _contains_any(s, ["中速", "适中"]):
        tags += ["mid-tempo"]
    if _contains_any(s, ["快板", "快速", "节奏感强", "更快"]):
        tags += ["fast"]
    bpm = _extract_bpm(s)
    if bpm:
        tags += [f"the bpm is {bpm}"]

    # ---- instruments ----
    instrument_map: list[tuple[list[str], str]] = [
        (["钢琴", "钢琴曲", "钢琴奏鸣"], "piano"),
        (["小提琴"], "violin"),
        (["中提琴"], "viola"),
        (["大提琴"], "cello"),
        (["低音提琴", "倍大提琴"], "double bass"),
        (["吉他"], "guitar"),
        (["电吉他"], "electric guitar"),
        (["萨克斯", "萨克斯风"], "saxophone"),
        (["小号", "号角"], "trumpet"),
        (["长号"], "trombone"),
        (["圆号", "法国号"], "french horn"),
        (["单簧管", "黑管"], "clarinet"),
        (["双簧管"], "oboe"),
        (["巴松"], "bassoon"),
        (["长笛"], "flute"),
        (["竖琴"], "harp"),
        (["鼓", "架子鼓", "鼓点"], "drums"),
        (["打击乐", "打击", "敲击"], "percussion"),
        (["贝斯", "低音"], "bass"),
        (["合成器", "电子"], "synth"),
        (["弦乐", "弦乐团"], "strings"),
        (["人声", "女声", "男声", "主唱", "歌手", "吟唱"], "vocals"),
        (["合唱", "和声"], "choir"),

        # Chinese traditional instruments
        (["古筝"], "guzheng"),
        (["二胡"], "erhu"),
        (["琵琶"], "pipa"),
        (["笛子", "竹笛"], "dizi"),
        (["古琴"], "guqin"),
    ]

    instruments_found: list[str] = []
    for kws, tag in instrument_map:
        # Do not add positive instrument tags when user explicitly negates it (e.g. "不要鼓点/不要人声")
        if _match_any_not_negated(s, kws):
            instruments_found.append(tag)
            tags.append(tag)

    # ---- arrangement ----
    if _contains_any(s, ["二重奏", "二重唱", "二重"]):
        tags += ["duet"]
    if _contains_any(s, ["三重奏", "三重"]):
        tags += ["trio"]
    if _contains_any(s, ["四重奏", "四重"]):
        tags += ["quartet"]
    if _contains_any(s, ["合奏", "协奏", "交响", "管弦", "乐团"]):
        tags += ["ensemble"]
    if _contains_any(s, ["古典", "室内乐", "交响"]):
        tags += ["classical"]
    if _contains_any(s, ["爵士"]):
        tags += ["jazz"]
    if _contains_any(s, ["流行"]):
        tags += ["pop"]
    if _contains_any(s, ["摇滚"]):
        tags += ["rock"]
    if _contains_any(s, ["电子乐", "电音", "EDM"]):
        tags += ["electronic"]
    if _contains_any(s, ["氛围", "环境", "空灵", "冥想"]):
        tags += ["ambient"]
    if _contains_any(s, ["电影感", "史诗感", "配乐", "影视"]):
        tags += ["cinematic"]
    if _contains_any(s, ["lofi", "低保真", "低保真(Lo-fi)", "Lo-fi", "lo-fi"]):
        tags += ["lo-fi"]

    # ---- emphasize violin presence for common complaint case ----
    # If user asked for piano+violin, strongly hint violin-led duet.
    if "piano" in instruments_found and "violin" in instruments_found:
        if _contains_any(s, ["合奏", "二重奏", "协奏", "合奏曲", "奏鸣"]):
            tags += ["piano and violin", "violin lead", "duet"]

    # ---- negative constraints ----
    tags += _extract_negative_phrases(s)

    # ---- cleanup ----
    # Strip characters that sometimes break tag parsing if user pasted weird punctuation.
    cleaned = []
    for t in tags:
        t2 = re.sub(r"\s+", " ", (t or "").strip())
        t2 = t2.strip(",")
        if t2:
            cleaned.append(t2)

    return SongGenStyleSuggestion(tags=_dedup_tags(cleaned))


def merge_style_tags(*, base_style: str | None, extra_tags: list[str]) -> str:
    """
    Merge user-provided style (comma-separated) with extracted tags, deduping case-insensitively.
    """
    base = (base_style or "").strip()
    tags: list[str] = []
    if base:
        tags += [t.strip() for t in base.split(",") if t.strip()]
    tags += list(extra_tags or [])
    tags = _dedup_tags(tags)
    return ", ".join(tags)


