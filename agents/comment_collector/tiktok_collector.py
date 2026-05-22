"""
Coletor de comentarios do TikTok via Apify.

Actors usados:
  1. clockworks/free-tiktok-scraper       — lista videos de um perfil
  2. clockworks/tiktok-comments-scraper   — pega comentarios de cada video

DICA: comentarios de TikTok costumam ser mais diretos que Instagram
("onde fica?", "quanto custa?"). Volume costuma ser menor mas inten\u00e7\u00e3o maior.
"""

import logging
from typing import Iterable

from apify_client import ApifyClient


def _normalize_video_item(item: dict, fallback_owner: str = "") -> dict:
    return {
        "platform": "tiktok",
        "video_url": item.get("webVideoUrl") or item.get("videoUrl"),
        "video_id": item.get("id"),
        "owner_username": (
            item.get("authorMeta", {}).get("name")
            or item.get("authorUsername")
            or fallback_owner
        ),
        "caption": item.get("text", ""),
        "view_count": item.get("playCount"),
        "like_count": item.get("diggCount"),
        "comment_count": item.get("commentCount"),
        "posted_at": item.get("createTimeISO") or item.get("createTime"),
    }


def list_recent_videos(
    apify_token: str,
    profile_username: str,
    limit: int = 30,
    logger: logging.Logger | None = None,
) -> list[dict]:
    """Lista videos recentes do perfil no TikTok."""
    log = logger or logging.getLogger(__name__)
    client = ApifyClient(apify_token)

    handle = profile_username.lstrip("@")
    profile_url = f"https://www.tiktok.com/@{handle}"
    log.info(f"[TT] Listando videos de {profile_url} (limite {limit})")

    run_input = {
        "profiles": [handle],
        "resultsPerPage": limit,
        "shouldDownloadVideos": False,
        "shouldDownloadCovers": False,
    }

    run = client.actor("clockworks/free-tiktok-scraper").call(run_input=run_input)
    items = list(client.dataset(run["defaultDatasetId"]).iterate_items())
    log.info(f"[TT] {len(items)} videos encontrados")

    return [_normalize_video_item(item, fallback_owner=handle) for item in items]


def search_videos_by_query(
    apify_token: str,
    query: str,
    limit: int = 20,
    logger: logging.Logger | None = None,
) -> list[dict]:
    """Busca videos no TikTok por keyword (nao por perfil)."""
    log = logger or logging.getLogger(__name__)
    client = ApifyClient(apify_token)

    log.info(f"[TT] Search por query: '{query}' (limite {limit})")

    run_input = {
        "searchQueries": [query],
        "resultsPerPage": min(limit, 50),
        "shouldDownloadVideos": False,
        "shouldDownloadCovers": False,
    }

    run = client.actor("clockworks/free-tiktok-scraper").call(run_input=run_input)
    items = list(client.dataset(run["defaultDatasetId"]).iterate_items())
    log.info(f"[TT] {len(items)} videos encontrados para '{query}'")

    return [_normalize_video_item(item) for item in items]


def fetch_comments(
    apify_token: str,
    video_urls: Iterable[str],
    max_comments_per_video: int = 500,
    logger: logging.Logger | None = None,
) -> list[dict]:
    """Para cada URL de video do TikTok, baixa os comentarios."""
    log = logger or logging.getLogger(__name__)
    client = ApifyClient(apify_token)

    urls = [u for u in video_urls if u]
    if not urls:
        log.warning("[TT] Nenhuma URL fornecida")
        return []

    log.info(f"[TT] Coletando comentarios de {len(urls)} videos (max {max_comments_per_video}/video)")

    run_input = {
        "postURLs": urls,
        "commentsPerPost": max_comments_per_video,
        "maxRepliesPerComment": 5,
    }

    run = client.actor("clockworks/tiktok-comments-scraper").call(run_input=run_input)
    items = list(client.dataset(run["defaultDatasetId"]).iterate_items())
    log.info(f"[TT] {len(items)} comentarios baixados")

    comments = []
    for item in items:
        username = (
            item.get("uniqueId")
            or item.get("user", {}).get("uniqueId")
            or item.get("username")
        )
        comments.append({
            "platform": "tiktok",
            "video_url": item.get("videoWebUrl") or item.get("postUrl"),
            "external_id": item.get("cid") or item.get("id"),
            "author_username": username,
            "author_fullname": (
                item.get("nickname")
                or item.get("user", {}).get("nickname")
            ),
            "author_url": f"https://www.tiktok.com/@{username}" if username else None,
            "text": item.get("text", ""),
            "like_count": item.get("diggCount", 0),
            "reply_count": item.get("replyCommentTotal", 0),
            "posted_at": item.get("createTimeISO"),
            "is_reply": bool(item.get("replyToReplyId") or item.get("replyId")),
        })
    return comments
