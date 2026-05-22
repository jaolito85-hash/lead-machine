"""
LEAD MACHINE — Profile Discovery via Google

Quando o usuario quer leads de uma cidade especifica (ex: "botox Maringa-PR"),
nao da pra confiar em hashtag colada (#botoxmaringa quase nao existe). O Google
ja indexa as bios dos perfis profissionais e ranqueia perfis cuja bio menciona
a cidade — usamos isso como "indice geografico de graca".

Fluxo:
  1. Query SerpAPI: "{nicho} {cidade} site:{platform}.com"
  2. Parseia top resultados (URL do perfil, bio do snippet, follower count)
  3. Filtra perfis cuja bio menciona a cidade ou que estao na faixa de
     follower_count que indica negocio local (1k-500k).
  4. Cacheia em leads-export/discovered_profiles.json (TTL 7 dias) — evita
     gastar SerpAPI a cada execucao.

Uso isolado (CLI):
  python agents/profile_discovery.py --nicho "botox" --cidade "Maringa-PR" --platform instagram

Variaveis de ambiente:
  SERPAPI_API_KEY — obrigatorio
  PROFILE_DISCOVERY_TTL_DAYS — default 7
"""

import argparse
import hashlib
import json
import logging
import os
import re
import sys
import unicodedata
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

import requests

BASE_DIR = Path(__file__).resolve().parent.parent
CACHE_PATH = BASE_DIR / "leads-export" / "discovered_profiles.json"

# Marcas/contas que aparecem ranqueadas mas nao sao perfis locais
BLOCKED_HANDLES = {
    "instagram", "tiktok", "youtube", "google", "facebook",
    "explore", "p", "reels", "reel", "stories",  # paths internos do IG
    # marcas nacionais grandes que poluem search
    "oboticario", "natura", "nivea", "lorealparis", "avon", "vult",
    "racco", "eudora", "rubyrose.cosmeticos", "rubymakeup",
}

# URLs path patterns por plataforma -> regex pra extrair handle
_PLATFORM_HANDLE_PATTERNS = {
    "instagram": re.compile(r"^https?://(?:www\.)?instagram\.com/([^/?#]+)/?"),
    "tiktok": re.compile(r"^https?://(?:www\.)?tiktok\.com/@([^/?#]+)/?"),
    "youtube": re.compile(r"^https?://(?:www\.)?youtube\.com/(?:@|c/|channel/|user/)([^/?#]+)/?"),
}


def _normalize(text: str) -> str:
    if not text:
        return ""
    nfkd = unicodedata.normalize("NFKD", text)
    no_accent = "".join(c for c in nfkd if not unicodedata.combining(c))
    return no_accent.lower().strip()


def _city_core(cidade: str) -> str:
    """'Maringa-PR' -> 'maringa', 'Sao Paulo - SP' -> 'sao paulo'."""
    if not cidade:
        return ""
    core = cidade.split("-")[0].strip()
    # Remove UF que pode ter sido separada por espaco
    core = re.sub(r"\s+(?:[A-Z]{2})$", "", core)
    return _normalize(core)


def _make_cache_key(nicho: str, cidade: str, platform: str) -> str:
    raw = f"{_normalize(nicho)}|{_city_core(cidade)}|{platform.lower()}"
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:16]


def _load_cache() -> dict:
    if not CACHE_PATH.exists():
        return {}
    try:
        return json.loads(CACHE_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, IOError):
        return {}


def _save_cache(cache: dict) -> None:
    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    CACHE_PATH.write_text(
        json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8",
    )


def _is_stale(entry: dict, ttl_days: int) -> bool:
    ts = entry.get("discovered_at", "")
    try:
        dt = datetime.fromisoformat(ts)
    except (ValueError, TypeError):
        return True
    return datetime.now() - dt > timedelta(days=ttl_days)


def _extract_handle(url: str, platform: str) -> Optional[str]:
    if not url:
        return None
    pattern = _PLATFORM_HANDLE_PATTERNS.get(platform)
    if not pattern:
        return None
    m = pattern.match(url.strip())
    if not m:
        return None
    handle = m.group(1).strip().lstrip("@").rstrip("/")
    if not handle or handle.lower() in BLOCKED_HANDLES:
        return None
    return handle


_FOLLOWERS_RE = re.compile(r"(\d+(?:[.,]\d+)?)\s*([KkMm]?)\+?\s*followers", re.IGNORECASE)


def _parse_followers(snippet: str) -> Optional[int]:
    """Extrai contagem de followers do snippet do Google ('13.7K+ followers')."""
    if not snippet:
        return None
    m = _FOLLOWERS_RE.search(snippet)
    if not m:
        return None
    n_str, suffix = m.group(1), m.group(2).upper()
    try:
        n = float(n_str.replace(",", "."))
    except ValueError:
        return None
    mult = {"K": 1_000, "M": 1_000_000, "": 1}.get(suffix, 1)
    return int(n * mult)


def _bio_mentions_city(bio: str, city_core: str) -> bool:
    if not bio or not city_core:
        return False
    return city_core in _normalize(bio)


def discover_profiles(
    nicho: str,
    cidade: str,
    platform: str = "instagram",
    limit: int = 10,
    ttl_days: Optional[int] = None,
    force_refresh: bool = False,
    logger: Optional[logging.Logger] = None,
) -> list[dict]:
    """Descobre perfis locais via Google + SerpAPI. Retorna lista de dicts:

    {handle, url, title, bio, followers, source_rank, city_match}

    Cacheia por (nicho, cidade, platform) por TTL dias.
    """
    log = logger or logging.getLogger(__name__)
    ttl = ttl_days or int(os.environ.get("PROFILE_DISCOVERY_TTL_DAYS", "7"))

    if platform not in _PLATFORM_HANDLE_PATTERNS:
        raise ValueError(f"Platform nao suportada: {platform!r}")

    key = _make_cache_key(nicho, cidade, platform)
    cache = _load_cache()
    cached = cache.get(key)
    if cached and not force_refresh and not _is_stale(cached, ttl):
        log.info(
            f"[discovery] cache HIT pra '{nicho}' x '{cidade}' x {platform} "
            f"({len(cached.get('profiles', []))} perfis)"
        )
        return cached.get("profiles", [])[:limit]

    api_key = os.environ.get("SERPAPI_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("SERPAPI_API_KEY nao configurada no .env")

    query = f"{nicho} {cidade} site:{platform}.com"
    log.info(f"[discovery] SerpAPI query: {query!r}")

    params = {
        "engine": "google",
        "q": query,
        "api_key": api_key,
        "num": 20,
        "hl": "pt-br",
        "gl": "br",
    }
    r = requests.get("https://serpapi.com/search.json", params=params, timeout=30)
    r.raise_for_status()
    data = r.json()

    organic = data.get("organic_results") or []
    log.info(f"[discovery] {len(organic)} resultados orgânicos do Google")

    city_core = _city_core(cidade)
    candidates: list[dict] = []
    seen_handles = set()

    for rank, item in enumerate(organic):
        link = item.get("link", "")
        handle = _extract_handle(link, platform)
        if not handle or handle in seen_handles:
            continue
        seen_handles.add(handle)

        title = item.get("title", "")
        snippet = item.get("snippet", "")
        bio_text = f"{title} {snippet}"
        followers = _parse_followers(snippet)
        city_match = _bio_mentions_city(bio_text, city_core)

        candidates.append({
            "handle": handle,
            "url": link,
            "title": title,
            "bio": snippet,
            "followers": followers,
            "source_rank": rank,
            "city_match": city_match,
        })

    # Filtros de qualidade. Se nada bater os filtros restritos, devolve top do
    # Google que ja faz ranqueamento decente.
    strict = [
        p for p in candidates
        if p["city_match"] or (p["followers"] and 1000 <= p["followers"] <= 500_000)
    ]
    if strict:
        profiles = strict
        log.info(f"[discovery] {len(profiles)}/{len(candidates)} perfis passaram filtros")
    else:
        profiles = candidates[:limit]
        log.info(f"[discovery] nenhum perfil passou filtros estritos, devolvendo top {len(profiles)} do Google")

    # Cache
    cache[key] = {
        "key_human": f"{nicho}|{cidade}|{platform}",
        "discovered_at": datetime.now().isoformat(timespec="seconds"),
        "ttl_days": ttl,
        "profiles": profiles,
    }
    _save_cache(cache)

    return profiles[:limit]


def main():
    parser = argparse.ArgumentParser(prog="profile_discovery")
    parser.add_argument("--nicho", required=True)
    parser.add_argument("--cidade", required=True)
    parser.add_argument("--platform", default="instagram",
                        choices=["instagram", "tiktok", "youtube"])
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--force-refresh", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(message)s")
    log = logging.getLogger("discovery-cli")

    # Carrega .env -> os.environ
    sys.path.insert(0, str(Path(__file__).parent))
    from base import load_env
    load_env()

    profiles = discover_profiles(
        args.nicho, args.cidade, args.platform,
        limit=args.limit, force_refresh=args.force_refresh, logger=log,
    )
    print(json.dumps(profiles, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
