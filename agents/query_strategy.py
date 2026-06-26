"""
Query strategy for social/comment lead collection.

TikTok and YouTube perform better with short, high-signal searches than with
long SEO-style queries. This module centralizes that rule so dashboard,
runner and direct agent calls do not depend on memory or manual discipline.
"""

import re
import unicodedata


STOPWORDS = {
    "a", "o", "as", "os", "de", "da", "do", "das", "dos", "em", "no", "na",
    "nos", "nas", "para", "pra", "por", "com", "e", "ou", "que", "quem",
    "como", "onde", "quando", "preciso", "leads", "lead", "pessoas",
    "clientes", "interessadas", "interessados", "buscar", "encontrar",
    "brasil", "nacional",
}


SOCIAL_PLATFORMS = {"tiktok", "youtube", "instagram"}


def normalize_text(text: str) -> str:
    if not text:
        return ""
    nfkd = unicodedata.normalize("NFKD", text)
    no_accents = "".join(c for c in nfkd if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", no_accents.lower()).strip()


def _dedupe(items: list[str]) -> list[str]:
    seen = set()
    out = []
    for item in items:
        q = re.sub(r"\s+", " ", (item or "").strip().lower())
        if q and q not in seen:
            seen.add(q)
            out.append(q)
    return out


def _rural_credit_variants(text: str) -> list[str]:
    norm = normalize_text(text)
    if not any(k in norm for k in ("credito rural", "divida rural", "pronaf", "custeio agricola")):
        return []
    return [
        "divida rural",
        "credito rural",
        "renegociacao divida rural",
        "pronaf divida",
        "alongamento divida rural",
    ]


def _generic_variants(query: str, nicho: str = "") -> list[str]:
    source = normalize_text(f"{query} {nicho}")
    words = [w for w in re.findall(r"[a-z0-9]{3,}", source) if w not in STOPWORDS]
    if not words:
        return [normalize_text(query)]

    variants = []
    base = " ".join(words[:3])
    if base:
        variants.append(base)
    if len(words) >= 2:
        variants.append(" ".join(words[:2]))
    if len(words) >= 4:
        variants.append(" ".join(words[1:4]))
    if len(words) >= 5:
        variants.append(" ".join(words[2:5]))
    return variants


def social_query_variants(query: str, nicho: str = "", platform: str = "", max_variants: int = 5) -> list[str]:
    """
    Expand a long command/query into short social searches.

    For social platforms, long queries are narrowed into multiple short searches.
    For non-social platforms, keep the original query.
    """
    platform = (platform or "").lower()
    original = normalize_text(query or nicho)
    if platform and platform not in SOCIAL_PLATFORMS:
        return [original] if original else []

    combined = f"{query or ''} {nicho or ''}"
    variants = _rural_credit_variants(combined) or _generic_variants(query, nicho)
    if original and len(original.split()) <= 3:
        variants.insert(0, original)
    variants = _dedupe(variants)
    return variants[:max_variants]


def social_query_run_plan(query_plan: list[str], env: dict | None = None) -> list[str]:
    """
    Choose how many short queries this process should execute.

    Default is one short query per run. This matches the fast TikTok/YouTube
    workflow and avoids subprocess timeouts. Use
    SOCIAL_QUERY_EXPANSION_MODE=batch for manual/offline batch runs.
    """
    if not query_plan:
        return []

    env = env or {}
    mode = str(env.get("SOCIAL_QUERY_EXPANSION_MODE", "single")).strip().lower()
    default_limit = len(query_plan) if mode in {"batch", "all"} else 1
    raw_limit = str(env.get("SOCIAL_QUERY_MAX_VARIANTS", "")).strip()

    try:
        limit = int(raw_limit) if raw_limit else default_limit
    except ValueError:
        limit = default_limit

    limit = max(1, min(limit, len(query_plan)))
    return query_plan[:limit]