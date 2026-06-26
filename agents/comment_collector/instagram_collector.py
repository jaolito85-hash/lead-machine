"""
Coletor de comentarios do Instagram via Apify.

Dois modos de coleta de comentarios:

  1. PUBLICO (sem login) — apify/instagram-comment-scraper
     - Sem custo extra alem do plano Apify
     - LIMITE DURO de ~15 comentarios por post (top + replies)
     - Comentarios "enterrados" (likes baixos) ficam invisiveis

  2. AUTENTICADO (com sessionid) — omissive_zen/instagram-comment-scraper
     - Acionado quando INSTAGRAM_SESSIONID esta no ambiente
     - Pega ate 100% dos comentarios visiveis pra usuario logado
     - Custo: $0.00005 por start de actor — trivial
     - Cookie eh o sessionid extraido do browser (passado via env)

O selecao eh automatica: se INSTAGRAM_SESSIONID esta setado no env, usa o
modo autenticado. Senao, modo publico (degradacao graciosa).
"""

from base import apify_dataset_id
import logging
import os
import re
from typing import Iterable

from apify_client import ApifyClient


def _normalize_post_item(item: dict, fallback_owner: str = "") -> dict:
    return {
        "platform": "instagram",
        "video_url": item.get("url", ""),
        "video_id": item.get("shortCode") or item.get("id"),
        "owner_username": item.get("ownerUsername") or fallback_owner,
        "caption": item.get("caption", ""),
        "view_count": item.get("videoPlayCount") or item.get("videoViewCount"),
        "like_count": item.get("likesCount"),
        "comment_count": item.get("commentsCount"),
        "posted_at": item.get("timestamp"),
    }


def list_recent_posts(
    apify_token: str,
    profile_username: str,
    limit: int = 30,
    logger: logging.Logger | None = None,
) -> list[dict]:
    """
    Lista os posts mais recentes de um perfil no Instagram.
    Retorna dicts normalizados: {url, video_id, caption, view_count, ...}

    DICA: rode isso primeiro pra ver quais videos a Carol tem,
    depois escolha quais quer aprofundar nos comentarios.
    """
    log = logger or logging.getLogger(__name__)
    client = ApifyClient(apify_token)

    profile_url = f"https://www.instagram.com/{profile_username.lstrip('@')}/"
    log.info(f"[IG] Listando posts de {profile_url} (limite {limit})")

    run_input = {
        "directUrls": [profile_url],
        "resultsType": "posts",
        "resultsLimit": limit,
        "addParentData": False,
    }

    run = client.actor("apify/instagram-scraper").call(run_input=run_input)
    items = list(client.dataset(apify_dataset_id(run)).iterate_items())
    log.info(f"[IG] {len(items)} posts encontrados")

    return [_normalize_post_item(item, fallback_owner=profile_username) for item in items]


def search_posts_by_query(
    apify_token: str,
    query: str,
    limit: int = 20,
    logger: logging.Logger | None = None,
) -> list[dict]:
    """
    Busca posts no Instagram por hashtag/keyword via `apify/instagram-hashtag-scraper`
    (actor dedicado que retorna lista plana de posts com URLs).

    Normaliza a query removendo espacos e '#' (ex: 'harmonizacao facial' ->
    'harmonizacaofacial'). O actor tambem aceita varias hashtags; aqui passamos
    apenas a query principal e, se for duas palavras, tambem a hashtag unida.
    """
    log = logger or logging.getLogger(__name__)
    client = ApifyClient(apify_token)

    raw = query.lstrip("#").strip()
    # Aceita tokens de 2 letras pra nao descartar marcas tipo "le creuset" -> #lecreuset
    words = re.findall(r"[a-zà-ú0-9]{2,}", raw.lower())
    if not words:
        words = [raw.replace(" ", "").lower()]

    primary = "".join(words)
    hashtags = [primary]
    for w in words:
        if len(w) >= 5 and w not in hashtags:
            hashtags.append(w)
    hashtags = hashtags[:3]

    log.info(f"[IG] Search por hashtags: {['#' + h for h in hashtags]} (limite {limit})")

    run_input = {
        "hashtags": hashtags,
        "resultsLimit": limit,
    }

    run = client.actor("apify/instagram-hashtag-scraper").call(run_input=run_input)
    items = list(client.dataset(apify_dataset_id(run)).iterate_items())
    log.info(f"[IG] {len(items)} posts encontrados para {['#' + h for h in hashtags]}")

    return [_normalize_post_item(item) for item in items]


def fetch_comments(
    apify_token: str,
    post_urls: Iterable[str],
    max_comments_per_post: int = 500,
    logger: logging.Logger | None = None,
) -> list[dict]:
    """
    Para cada URL de post, baixa os comentarios. Roteamento automatico:
      - Se INSTAGRAM_SESSIONID setado: omissive_zen/instagram-comment-scraper
        (autenticado, traz ~100% dos comments)
      - Senao: apify/instagram-comment-scraper (publico, ate ~15/post)

    Retorna lista plana de comentarios normalizados:
      {video_url, external_id, author_username, author_fullname, text,
       like_count, reply_count, posted_at, is_reply}
    """
    log = logger or logging.getLogger(__name__)
    urls = [u for u in post_urls if u]
    if not urls:
        log.warning("[IG] Nenhuma URL fornecida")
        return []

    mode = os.environ.get("IG_COMMENTS_MODE", "public").strip().lower()
    sessionid = os.environ.get("INSTAGRAM_SESSIONID", "").strip()
    if mode in {"auth", "authed", "authenticated", "autenticado"} and sessionid:
        return _fetch_comments_authed(
            apify_token, urls, max_comments_per_post, sessionid, log,
        )
    if sessionid and mode == "public":
        log.info("[IG] INSTAGRAM_SESSIONID presente, mas IG_COMMENTS_MODE=public; usando coleta publica em batch")
    return _fetch_comments_public(apify_token, urls, max_comments_per_post, log)


_VALID_POST_URL = re.compile(
    r"^https?://(?:www\.)?instagram\.com/(?:[\w.-]+/)?(?:p|reel)/[\w-]+",
)


def _fetch_comments_public(
    apify_token: str, urls: list[str], max_comments_per_post: int, log: logging.Logger,
) -> list[dict]:
    """Fluxo publico — apify/instagram-comment-scraper. Ate ~15/post."""
    valid_urls = [u for u in urls if _VALID_POST_URL.match(u)]
    if len(valid_urls) < len(urls):
        log.info(f"[IG] {len(urls) - len(valid_urls)} URLs filtradas (formato invalido para comment scraper)")
    if not valid_urls:
        log.warning("[IG] Nenhuma URL valida para coletar comentarios")
        return []

    client = ApifyClient(apify_token)
    log.info(f"[IG] Coletando comentarios PUBLICO de {len(valid_urls)} posts (max {max_comments_per_post}/post)")

    run_input = {
        "directUrls": valid_urls,
        "resultsLimit": max_comments_per_post,
        "isNewestComments": False,
    }
    run = client.actor("apify/instagram-comment-scraper").call(run_input=run_input)
    items = list(client.dataset(apify_dataset_id(run)).iterate_items())
    log.info(f"[IG] {len(items)} comentarios baixados (publico)")

    comments = []
    for item in items:
        text = (item.get("text") or "").strip()
        author = item.get("ownerUsername") or (item.get("owner") or {}).get("username")
        if not text or not author:
            continue
        comments.append({
            "platform": "instagram",
            "video_url": item.get("postUrl") or item.get("url"),
            "external_id": item.get("id") or item.get("commentId"),
            "author_username": author,
            "author_fullname": item.get("ownerFullName") or (item.get("owner") or {}).get("full_name"),
            "author_url": f"https://www.instagram.com/{author}/",
            "text": text,
            "like_count": item.get("likesCount", 0),
            "reply_count": item.get("repliesCount", 0),
            "posted_at": item.get("timestamp"),
            "is_reply": bool(item.get("parentCommentId") or item.get("isReply")),
        })
    log.info(f"[IG] {len(comments)} comentarios validos de {len(items)} items retornados")
    return comments


def _fetch_comments_authed(
    apify_token: str, urls: list[str], max_comments_per_post: int,
    sessionid: str, log: logging.Logger,
) -> list[dict]:
    """Fluxo autenticado — omissive_zen/instagram-comment-scraper. Roda 1 chamada por URL."""
    client = ApifyClient(apify_token)
    log.info(f"[IG] Coletando comentarios AUTENTICADO de {len(urls)} posts (max {max_comments_per_post}/post)")

    all_comments: list[dict] = []
    for i, url in enumerate(urls, 1):
        try:
            run = client.actor("omissive_zen/instagram-comment-scraper").call(
                run_input={
                    "postUrl": url,
                    "sessionCookie": sessionid,
                    "maxComments": max_comments_per_post,
                },
                timeout_secs=int(os.environ.get("IG_COMMENT_ACTOR_TIMEOUT", "90")),
            )
            items = list(client.dataset(apify_dataset_id(run)).iterate_items())
            log.info(f"[IG] [{i}/{len(urls)}] {len(items)} comments em {url}")
        except Exception as e:
            log.warning(f"[IG] [{i}/{len(urls)}] erro em {url}: {e}")
            continue

        for item in items:
            author = (item.get("author") or "").strip().lstrip("@")
            if not author:
                continue
            all_comments.append({
                "platform": "instagram",
                "video_url": item.get("postUrl") or url,
                # omissive_zen nao expoe id de comentario — geramos sintetico estavel
                "external_id": f"oz:{url}:{author}:{(item.get('text') or '')[:80]}",
                "author_username": author,
                "author_fullname": item.get("authorFullName") or "",
                "author_url": f"https://www.instagram.com/{author}/" if author else None,
                "text": item.get("text") or "",
                "like_count": item.get("likesCount") or item.get("likes") or 0,
                "reply_count": item.get("replyCount") or 0,
                "posted_at": item.get("date"),
                "is_reply": bool(item.get("isReply") or item.get("parentCommentId")),
            })

    log.info(f"[IG] {len(all_comments)} comentarios baixados (autenticado, somando todos posts)")
    return all_comments