"""
Orquestrador: lista videos -> coleta comentarios -> classifica -> grava.

Cada funcao retorna stats pra voce acompanhar o que aconteceu.
"""

import logging
import os
import re
import time
import unicodedata
from typing import Optional

from . import db, instagram_collector, tiktok_collector, youtube_collector, classifier


# Paises lusofonos NAO-brasileiros — se um post claramente e deles, descarta.
# Pegamos pela hashtag ou mencoes explicitas.
_NON_BR_LUSOPHONE_HASHTAGS = {
    "angola", "angolaao", "ao",
    "mocambique", "moçambique", "mozambique", "mocambiquemz", "mz",
    "portugal", "portugalpt",
    "cabo verde", "caboverde", "cv",
    "guinebissau", "gw",
    "timorleste", "timor",
    "macau", "macaumo",
}

# Sinais fortes de cross-country lusofonia (post feito pra multi-audiencia lusofona)
_CROSS_LUSOPHONE_MARKERS = [
    re.compile(r"angola\s*ao\s*portugal", re.I),
    re.compile(r"mocambique\s*mz", re.I),
    re.compile(r"moçambique\s*mz", re.I),
    re.compile(r"#angolaao", re.I),
    re.compile(r"#portugalpt", re.I),
]


def _normalize(text: str) -> str:
    if not text:
        return ""
    nfkd = unicodedata.normalize("NFKD", text)
    no_accent = "".join(c for c in nfkd if not unicodedata.combining(c))
    return no_accent.lower()


def _extract_hashtags(text: str) -> list[str]:
    if not text:
        return []
    return [h.lower() for h in re.findall(r"#([\wÀ-ÿ]+)", text)]


def _is_topic_relevant(video: dict, topic_keywords: list[str], log) -> bool:
    """
    Verifica se o video e relevante pro nicho e NAO e conteudo lusofono estrangeiro.
    """
    caption = video.get("caption") or ""
    owner = video.get("owner_username") or ""
    combined = _normalize(caption + " " + owner)

    # 1) Rejeita cross-country lusofonia explicita
    for marker in _CROSS_LUSOPHONE_MARKERS:
        if marker.search(caption):
            log.info(f"[skip] cross-lusofonia detectada em {video.get('video_url','?')[:60]}")
            return False

    # 2) Rejeita se hashtags principais sao de pais nao-BR
    hashtags = _extract_hashtags(caption)
    non_br_hits = sum(1 for h in hashtags if _normalize(h) in _NON_BR_LUSOPHONE_HASHTAGS)
    if non_br_hits >= 2:
        log.info(f"[skip] {non_br_hits} hashtags nao-BR em {video.get('video_url','?')[:60]}")
        return False

    # 3) Se temos keywords de topico, exige ao menos 1 na caption/owner
    if topic_keywords:
        tk_norm = [_normalize(k) for k in topic_keywords]
        if not any(k in combined for k in tk_norm):
            log.info(f"[skip] off-topic ({caption[:50]}...) em {video.get('video_url','?')[:60]}")
            return False

    return True


def _derive_topic_keywords(query: str, nicho: str = "") -> list[str]:
    """Deriva keywords obrigatorias do topico a partir de query+nicho. Remove stopwords."""
    STOPWORDS = {"de", "da", "do", "em", "no", "na", "pra", "para", "com",
                 "ou", "e", "a", "o", "os", "as", "um", "uma"}
    text = f"{query} {nicho}".lower()
    words = re.findall(r"[a-zà-ú]{3,}", text)
    return list({w for w in words if w not in STOPWORDS})


def collect_instagram_profile(
    apify_token: str,
    profile: str,
    max_videos: int = 20,
    max_comments_per_video: int = 500,
    logger: Optional[logging.Logger] = None,
) -> dict:
    """Pipeline completo para um perfil do Instagram."""
    log = logger or logging.getLogger(__name__)
    db.init_db()

    # 1. Listar posts recentes
    posts = instagram_collector.list_recent_posts(
        apify_token, profile, limit=max_videos, logger=log
    )
    if not posts:
        return {"platform": "instagram", "videos": 0, "comments": 0, "classified": 0}

    # 2. Salvar videos no banco
    video_id_by_url = {}
    for post in posts:
        url = post.get("video_url")
        if not url:
            continue
        internal_id = db.upsert_video(
            platform="instagram",
            video_url=url,
            video_id=post.get("video_id"),
            owner_username=post.get("owner_username"),
            caption=post.get("caption"),
            view_count=post.get("view_count"),
            like_count=post.get("like_count"),
            comment_count=post.get("comment_count"),
            posted_at=post.get("posted_at"),
        )
        video_id_by_url[url] = internal_id

    log.info(f"[IG] {len(video_id_by_url)} videos salvos no DB")

    # 3. Coletar comentarios de cada post
    urls = list(video_id_by_url.keys())
    comments = instagram_collector.fetch_comments(
        apify_token, urls,
        max_comments_per_post=max_comments_per_video,
        logger=log,
    )

    # 4. Salvar comentarios + classificar
    saved, classified = _save_and_classify(comments, video_id_by_url, log)

    return {
        "platform": "instagram",
        "videos": len(video_id_by_url),
        "comments": saved,
        "classified": classified,
    }


def collect_tiktok_profile(
    apify_token: str,
    profile: str,
    max_videos: int = 20,
    max_comments_per_video: int = 500,
    logger: Optional[logging.Logger] = None,
) -> dict:
    """Pipeline completo para um perfil do TikTok."""
    log = logger or logging.getLogger(__name__)
    db.init_db()

    # 1. Listar videos
    videos = tiktok_collector.list_recent_videos(
        apify_token, profile, limit=max_videos, logger=log
    )
    if not videos:
        return {"platform": "tiktok", "videos": 0, "comments": 0, "classified": 0}

    # 2. Salvar videos
    video_id_by_url = {}
    for v in videos:
        url = v.get("video_url")
        if not url:
            continue
        internal_id = db.upsert_video(
            platform="tiktok",
            video_url=url,
            video_id=v.get("video_id"),
            owner_username=v.get("owner_username"),
            caption=v.get("caption"),
            view_count=v.get("view_count"),
            like_count=v.get("like_count"),
            comment_count=v.get("comment_count"),
            posted_at=v.get("posted_at"),
        )
        video_id_by_url[url] = internal_id

    log.info(f"[TT] {len(video_id_by_url)} videos salvos no DB")

    # 3. Coletar comentarios
    urls = list(video_id_by_url.keys())
    comments = tiktok_collector.fetch_comments(
        apify_token, urls,
        max_comments_per_video=max_comments_per_video,
        logger=log,
    )

    # 4. Salvar + classificar
    saved, classified = _save_and_classify(comments, video_id_by_url, log)

    return {
        "platform": "tiktok",
        "videos": len(video_id_by_url),
        "comments": saved,
        "classified": classified,
    }


def collect_by_query(
    apify_token: str,
    platform: str,
    query: str,
    city: str = "",
    max_videos: int = 20,
    max_comments_per_video: int = 500,
    logger: Optional[logging.Logger] = None,
) -> dict:
    """
    Pipeline busca-por-keyword: lista videos/posts por query, baixa comentarios,
    classifica e retorna os comentarios enriquecidos (NAO grava em leads-db aqui —
    quem chama decide se vira lead).

    Retorna:
      {
        "platform": "tiktok"|"instagram",
        "videos_found": int,
        "comments_collected": int,
        "classified": int,
        "hot_comments": list[dict]   # comentarios com intent de compra + contexto do video
      }

    Cada item em hot_comments tem:
      author_username, author_fullname, author_url, text, video_url, video_owner,
      intent, urgency, lead_score, city (detectada no texto), ...
    """
    log = logger or logging.getLogger(__name__)
    db.init_db()

    # 1. Busca videos/posts por query
    if platform == "tiktok":
        videos = tiktok_collector.search_videos_by_query(
            apify_token, query, limit=max_videos, logger=log,
        )
    elif platform == "instagram":
        videos = instagram_collector.search_posts_by_query(
            apify_token, query, limit=max_videos, logger=log,
        )
    elif platform == "youtube":
        videos = youtube_collector.search_videos_by_query(
            apify_token, query, limit=max_videos, logger=log,
        )
    else:
        raise ValueError(f"platform invalido: {platform!r}")

    if not videos:
        return {
            "platform": platform, "videos_found": 0,
            "comments_collected": 0, "classified": 0, "hot_comments": [],
        }

    # 1.5) Filtro de relevancia: remove videos off-topic ou de lusofonia estrangeira
    topic_keywords = _derive_topic_keywords(query)
    total_before = len(videos)
    videos = [v for v in videos if _is_topic_relevant(v, topic_keywords, log)]
    skipped = total_before - len(videos)
    if skipped:
        log.info(f"[{platform}] {skipped}/{total_before} videos descartados (off-topic ou lusofonia nao-BR)")

    if not videos:
        log.info(f"[{platform}] nenhum video relevante apos filtros de topico. Ajuste query.")
        return {
            "platform": platform, "videos_found": 0,
            "comments_collected": 0, "classified": 0, "hot_comments": [],
        }

    # 1.6) Descarta posts com 0 comentarios — evita chamar comment scraper a toa
    min_comments = int(os.environ.get("IG_MIN_COMMENTS_PER_POST", "1"))
    before_cc = len(videos)
    videos = [
        v for v in videos
        if (v.get("comment_count") or 0) >= min_comments
        or v.get("comment_count") is None  # desconhecido = tenta
    ]
    skipped_cc = before_cc - len(videos)
    if skipped_cc:
        log.info(f"[{platform}] {skipped_cc}/{before_cc} posts com <{min_comments} comentarios descartados")

    if not videos:
        log.info(f"[{platform}] nenhum post com comentarios suficientes")
        return {
            "platform": platform, "videos_found": 0,
            "comments_collected": 0, "classified": 0, "hot_comments": [],
        }

    # 2. Persiste videos no DB e coleta comentarios
    video_id_by_url = {}
    video_meta_by_url = {}
    for v in videos:
        url = v.get("video_url")
        if not url:
            continue
        internal_id = db.upsert_video(
            platform=platform,
            video_url=url,
            video_id=v.get("video_id"),
            owner_username=v.get("owner_username"),
            caption=v.get("caption"),
            view_count=v.get("view_count"),
            like_count=v.get("like_count"),
            comment_count=v.get("comment_count"),
            posted_at=v.get("posted_at"),
        )
        video_id_by_url[url] = internal_id
        video_meta_by_url[url] = v

    log.info(f"[{platform}] {len(video_id_by_url)} videos salvos no DB para query='{query}'")

    # 3. Baixa comentarios
    urls = list(video_id_by_url.keys())
    if platform == "tiktok":
        comments = tiktok_collector.fetch_comments(
            apify_token, urls,
            max_comments_per_video=max_comments_per_video, logger=log,
        )
    elif platform == "youtube":
        comments = youtube_collector.fetch_comments(
            apify_token, urls,
            max_comments_per_video=max_comments_per_video, logger=log,
        )
    else:
        comments = instagram_collector.fetch_comments(
            apify_token, urls,
            max_comments_per_post=max_comments_per_video, logger=log,
        )

    # 4. Salva comentarios crus + classifica
    saved, classified = _save_and_classify(comments, video_id_by_url, log)

    # 5. Recupera comentarios classificados recentes com metadados de video
    #    pra caller converter em leads. So retorna quem tem intent relevante.
    hot = _fetch_hot_comments_by_video_ids(
        list(video_id_by_url.values()), video_meta_by_url, platform, log,
    )

    return {
        "platform": platform,
        "videos_found": len(video_id_by_url),
        "comments_collected": saved,
        "classified": classified,
        "hot_comments": hot,
    }


def _fetch_hot_comments_by_video_ids(
    video_internal_ids: list[int],
    video_meta_by_url: dict,
    platform: str,
    log,
) -> list[dict]:
    """Busca no DB comentarios com intent de compra + metadados do video pai."""
    if not video_internal_ids:
        return []

    hot_intents = ("buscando_atendimento", "perguntando_preco",
                   "apostador_ativo", "perguntando_local")
    placeholders = ",".join("?" * len(video_internal_ids))
    intent_placeholders = ",".join("?" * len(hot_intents))

    with db.get_conn() as conn:
        rows = conn.execute(
            f"""
            SELECT
                c.id, c.video_id, c.author_username, c.author_fullname, c.author_url,
                c.text, c.like_count, c.posted_at,
                v.video_url, v.owner_username AS video_owner,
                cl.intent, cl.urgency, cl.lead_score, cl.city, cl.state
            FROM comments c
            JOIN videos v ON v.id = c.video_id
            JOIN classifications cl ON cl.comment_id = c.id
            WHERE c.video_id IN ({placeholders})
              AND cl.intent IN ({intent_placeholders})
              AND c.text IS NOT NULL AND length(trim(c.text)) >= 3
            ORDER BY cl.lead_score DESC, c.like_count DESC
            """,
            (*video_internal_ids, *hot_intents),
        ).fetchall()

    log.info(f"[{platform}] {len(rows)} comentarios com intent de compra encontrados")
    return [dict(r) for r in rows]


def _save_and_classify(comments: list[dict], video_id_by_url: dict, log) -> tuple[int, int]:
    """Helper interno: salva comentarios novos e classifica."""
    saved = 0
    classified = 0

    for c in comments:
        url = c.get("video_url")
        video_internal_id = video_id_by_url.get(url)
        if not video_internal_id:
            # Pode acontecer se o Apify retornar URL ligeiramente diferente
            continue

        comment_id = db.insert_comment(
            video_id=video_internal_id,
            platform=c.get("platform"),
            external_id=c.get("external_id"),
            author_username=c.get("author_username"),
            author_fullname=c.get("author_fullname"),
            author_url=c.get("author_url"),
            text=c.get("text", ""),
            like_count=c.get("like_count", 0),
            reply_count=c.get("reply_count", 0),
            posted_at=c.get("posted_at"),
            is_reply=c.get("is_reply", False),
        )

        if comment_id is None:
            # Comentario ja existia (UNIQUE constraint), pula
            continue

        saved += 1

        # Classificar
        text = c.get("text", "")
        if not text.strip():
            continue
        try:
            result = classifier.classify(text, logger=log)
            db.upsert_classification(comment_id, **result)
            classified += 1
        except Exception as e:
            log.warning(f"Erro classificando comentario {comment_id}: {e}")

    log.info(f"Salvos: {saved} novos comentarios | Classificados: {classified}")
    return saved, classified


def collect_by_profiles(
    apify_token: str,
    platform: str,
    profiles: list,
    city: str = "",
    max_videos_per_profile: int = 8,
    max_total_videos: int | None = None,
    max_comments_per_video: int = 200,
    logger: Optional[logging.Logger] = None,
) -> dict:
    """
    Pipeline busca-por-lista-de-perfis: lista posts/videos recentes de cada
    perfil, baixa comentarios, classifica e retorna comentarios enriquecidos.

    Usado pelo fluxo de discovery: o profile_discovery devolve perfis locais
    (ex: "@royalface.maringa") e este pipeline coleta comentarios de cada um
    sem precisar de hashtag/keyword.

    profiles: lista de strings (handles) ou dicts {"handle": ...}
    Retorna mesmo formato de collect_by_query.
    """
    log = logger or logging.getLogger(__name__)
    db.init_db()

    # Normaliza profiles -> lista de handles
    handles = []
    for p in profiles:
        if isinstance(p, str):
            h = p
        elif isinstance(p, dict):
            h = p.get("handle") or p.get("username") or ""
        else:
            continue
        h = h.strip().lstrip("@")
        if h and h not in handles:
            handles.append(h)

    if not handles:
        return {
            "platform": platform, "videos_found": 0,
            "comments_collected": 0, "classified": 0, "hot_comments": [],
        }

    log.info(f"[{platform}] coletando posts de {len(handles)} perfis: {handles}")

    # 1. Lista posts/videos de cada perfil
    video_id_by_url = {}
    video_meta_by_url = {}
    min_comments = int(os.environ.get("IG_MIN_COMMENTS_PER_POST", "1"))

    for handle in handles:
        if max_total_videos and len(video_id_by_url) >= max_total_videos:
            break
        try:
            if platform == "instagram":
                posts = instagram_collector.list_recent_posts(
                    apify_token, handle, limit=max_videos_per_profile, logger=log,
                )
            elif platform == "tiktok":
                posts = tiktok_collector.list_recent_videos(
                    apify_token, handle, limit=max_videos_per_profile, logger=log,
                )
            else:
                raise ValueError(f"platform invalido: {platform!r}")
        except Exception as e:
            log.warning(f"[{platform}] erro listando perfil @{handle}: {e}")
            continue

        for post in posts or []:
            if max_total_videos and len(video_id_by_url) >= max_total_videos:
                break
            if platform == "instagram":
                comment_count = post.get("comment_count")
                if comment_count is not None and int(comment_count or 0) < min_comments:
                    continue
            url = post.get("video_url")
            if not url:
                continue
            internal_id = db.upsert_video(
                platform=platform,
                video_url=url,
                video_id=post.get("video_id"),
                owner_username=post.get("owner_username") or handle,
                caption=post.get("caption"),
                view_count=post.get("view_count"),
                like_count=post.get("like_count"),
                comment_count=post.get("comment_count"),
                posted_at=post.get("posted_at"),
            )
            video_id_by_url[url] = internal_id
            video_meta_by_url[url] = post

    if not video_id_by_url:
        log.info(f"[{platform}] nenhum post coletado dos perfis")
        return {
            "platform": platform, "videos_found": 0,
            "comments_collected": 0, "classified": 0, "hot_comments": [],
        }

    cap_msg = f" (cap total {max_total_videos})" if max_total_videos else ""
    log.info(f"[{platform}] {len(video_id_by_url)} posts salvos no DB de {len(handles)} perfis{cap_msg}")

    # 2. Baixa comentarios em batch
    urls = list(video_id_by_url.keys())
    if platform == "tiktok":
        comments = tiktok_collector.fetch_comments(
            apify_token, urls,
            max_comments_per_video=max_comments_per_video, logger=log,
        )
    else:
        comments = instagram_collector.fetch_comments(
            apify_token, urls,
            max_comments_per_post=max_comments_per_video, logger=log,
        )

    # 3. Salva + classifica
    saved, classified = _save_and_classify(comments, video_id_by_url, log)

    # 4. Recupera hot
    hot = _fetch_hot_comments_by_video_ids(
        list(video_id_by_url.values()), video_meta_by_url, platform, log,
    )

    return {
        "platform": platform,
        "videos_found": len(video_id_by_url),
        "comments_collected": saved,
        "classified": classified,
        "hot_comments": hot,
    }


def reclassify_pending(batch_size: int = 200, logger: Optional[logging.Logger] = None) -> int:
    """
    Reprocessa comentarios que foram salvos mas nao tem classificacao
    (caso o classifier tenha falhado durante a coleta).
    """
    log = logger or logging.getLogger(__name__)
    pending = db.get_unclassified_comments(limit=batch_size)
    log.info(f"Reclassificando {len(pending)} comentarios pendentes")

    done = 0
    for c in pending:
        text = c.get("text", "")
        if not text.strip():
            continue
        try:
            result = classifier.classify(text, logger=log)
            db.upsert_classification(c["id"], **result)
            done += 1
        except Exception as e:
            log.warning(f"Erro classificando {c['id']}: {e}")

    return done
