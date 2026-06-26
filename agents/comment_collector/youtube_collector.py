"""
Coletor de comentarios do YouTube via Apify.

Actors usados:
  1. streamers/youtube-scraper          — busca videos por keyword
  2. streamers/youtube-comments-scraper — coleta comentarios de cada video

Por que YouTube? Para nichos B2C "explicativos" (juridico, agro, financas)
o YT costuma render mais que IG: vídeos longos com comentarios profundos
("passei por isso, BB me ferrou em 2023..."). Comentaristas sao
o lead — o canal/dono do video e quase sempre advogado/influencer.
"""

from base import apify_dataset_id
import logging
from typing import Iterable

from apify_client import ApifyClient


def _normalize_video_item(item: dict) -> dict:
    """Aceita variacoes de schema do streamers/youtube-scraper."""
    video_id = item.get("id") or item.get("videoId")
    url = (
        item.get("url")
        or item.get("videoUrl")
        or (f"https://www.youtube.com/watch?v={video_id}" if video_id else "")
    )
    return {
        "platform": "youtube",
        "video_url": url,
        "video_id": video_id,
        "owner_username": (
            item.get("channelName")
            or item.get("channelUsername")
            or item.get("author")
            or ""
        ),
        "caption": (item.get("title") or "") + "\n\n" + (item.get("description") or ""),
        "view_count": item.get("viewCount") or item.get("views"),
        "like_count": item.get("likes") or item.get("likeCount"),
        "comment_count": item.get("commentsCount") or item.get("numberOfComments"),
        "posted_at": item.get("date") or item.get("uploadDate") or item.get("publishedAt"),
    }


def search_videos_by_query(
    apify_token: str,
    query: str,
    limit: int = 20,
    logger: logging.Logger | None = None,
) -> list[dict]:
    """Busca videos no YouTube por keyword via streamers/youtube-scraper."""
    log = logger or logging.getLogger(__name__)
    client = ApifyClient(apify_token)

    log.info(f"[YT] Search por query: '{query}' (limite {limit})")

    run_input = {
        "searchKeywords": query,
        "maxResults": limit,
        "maxResultsShorts": 0,
        "maxResultStreams": 0,
    }

    run = client.actor("streamers/youtube-scraper").call(run_input=run_input)
    items = list(client.dataset(apify_dataset_id(run)).iterate_items())
    log.info(f"[YT] {len(items)} videos encontrados para '{query}'")

    normalized = [_normalize_video_item(it) for it in items]
    # Descarta items sem URL valida (alguns scrapers devolvem metadata de canal)
    return [v for v in normalized if v.get("video_url", "").startswith("http")]


def fetch_comments(
    apify_token: str,
    video_urls: Iterable[str],
    max_comments_per_video: int = 300,
    logger: logging.Logger | None = None,
) -> list[dict]:
    """Para cada URL de video do YouTube, baixa os comentarios."""
    log = logger or logging.getLogger(__name__)
    client = ApifyClient(apify_token)

    urls = [u for u in video_urls if u]
    if not urls:
        log.warning("[YT] Nenhuma URL fornecida")
        return []

    log.info(f"[YT] Coletando comentarios de {len(urls)} videos (max {max_comments_per_video}/video)")

    run_input = {
        "startUrls": [{"url": u} for u in urls],
        "maxComments": max_comments_per_video,
        "includeReplies": True,
    }

    run = client.actor("streamers/youtube-comments-scraper").call(run_input=run_input)
    items = list(client.dataset(apify_dataset_id(run)).iterate_items())
    log.info(f"[YT] {len(items)} comentarios baixados")

    comments = []
    for item in items:
        # Schema real do streamers/youtube-comments-scraper:
        #   cid, replyToCid, publishedTimeText, comment, author (com @),
        #   voteCount, replyCount, videoId, pageUrl, title
        video_url = (
            item.get("pageUrl")
            or (
                f"https://www.youtube.com/watch?v={item.get('videoId')}"
                if item.get("videoId") else None
            )
        )
        author_raw = (item.get("author") or "").strip()
        # author vem como "@handle" ou "Nome do Canal"
        username = author_raw.lstrip("@") if author_raw.startswith("@") else author_raw
        author_url = f"https://www.youtube.com/@{username}" if author_raw.startswith("@") else None

        comments.append({
            "platform": "youtube",
            "video_url": video_url,
            "external_id": item.get("cid"),
            "author_username": username,
            "author_fullname": author_raw,
            "author_url": author_url,
            "text": item.get("comment") or "",
            "like_count": item.get("voteCount") or 0,
            "reply_count": item.get("replyCount") or 0,
            "posted_at": item.get("publishedTimeText"),
            "is_reply": bool(item.get("replyToCid")),
        })
    return comments