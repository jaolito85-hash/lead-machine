#!/usr/bin/env python3
"""
LEAD MACHINE — Agent TikTok
Busca leads no TikTok via Apify (videos, comentarios, perfis).

Uso:
  python agents/agent_tiktok.py --query "harmonizacao facial" --city "Maringa-PR"
  python agents/agent_tiktok.py --query "botox antes e depois" --limit 20

Env vars (Paperclip):
  SEARCH_QUERY, CITY, NICHO, LIMIT, APIFY_TOKEN
"""

import sys
import time

from base import (
    build_arg_parser, calculate_score, classify_temp, create_lead, is_bot,
    load_env, load_leads, make_result, merge_leads, output_result,
    resolve_param, save_leads, setup_logger,
)


def scrape_tiktok(apify_token: str, query: str, city: str, nicho: str,
                  limit: int, logger=None) -> tuple:
    """Busca leads no TikTok via Apify."""
    from apify_client import ApifyClient

    client = ApifyClient(apify_token)
    leads = []
    errors = []

    # Buscar videos por keyword
    try:
        logger.info(f"Apify clockworks/free-tiktok-scraper: '{query}'")
        run_input = {
            "searchQueries": [query],
            "resultsPerPage": min(limit, 30),
            "shouldDownloadCovers": False,
            "shouldDownloadVideos": False,
        }

        run = client.actor("clockworks/free-tiktok-scraper").call(run_input=run_input)
        items = list(client.dataset(run["defaultDatasetId"]).iterate_items())
        logger.info(f"Videos encontrados: {len(items)}")

        for video in items:
            author = video.get("authorMeta", {})
            author_name = author.get("name", "")
            author_nick = author.get("nickName", author_name)
            video_url = video.get("webVideoUrl", "")
            video_text = video.get("text", "")
            stats = video.get("videoMeta", {})
            play_count = video.get("playCount", 0)
            comment_count = video.get("commentCount", 0)

            # Dono do video como lead (pode ser profissional)
            if author_name:
                bio = author.get("signature", "")
                full_text = f"{video_text} {bio}"

                # Verificar relevancia com cidade
                if city:
                    city_lower = city.lower().split("-")[0].strip()
                    if city_lower not in full_text.lower():
                        # Video sem mencao a cidade — score mais baixo
                        pass

                score = 55  # Base: postou sobre o tema
                if bio and any(k in bio.lower() for k in ["clinica", "dr", "dra", "estetica", "dentista"]):
                    score = 75  # E profissional
                if play_count and play_count > 10000:
                    score += 5
                score = min(score, 100)

                lead = create_lead(
                    plataforma="tiktok",
                    user=author_name,
                    texto=video_text[:200] if video_text else f"Video sobre {query}",
                    url=video_url,
                    cidade=city,
                    nicho=nicho or query,
                    nome=author_nick or author_name,
                    score=score,
                    temp=classify_temp(score),
                    extra={
                        "followers": author.get("fans", 0),
                        "play_count": play_count,
                    },
                )
                leads.append(lead)

            # Comentarios do video
            comments = video.get("comments", [])
            if isinstance(comments, list):
                for comment in comments:
                    c_text = comment.get("text", "")
                    c_user = comment.get("uniqueId", comment.get("nickName", ""))

                    if not c_user or not c_text or is_bot(c_text):
                        continue

                    score = calculate_score(c_text, city_match=bool(city))
                    if score == 0:
                        continue

                    lead = create_lead(
                        plataforma="tiktok",
                        user=c_user,
                        texto=c_text,
                        url=video_url,
                        cidade=city,
                        nicho=nicho or query,
                        post_owner=author_name,
                        score=score,
                        temp=classify_temp(score),
                    )
                    leads.append(lead)

    except Exception as e:
        err = f"Erro no TikTok scraping: {e}"
        logger.error(err)
        errors.append(err)

    return leads, errors


def main():
    parser = build_arg_parser("tiktok", "Scraper TikTok via Apify")
    args = parser.parse_args()

    env = load_env()
    logger = setup_logger("tiktok", verbose=args.verbose)

    query = resolve_param(args, "query", "SEARCH_QUERY", "")
    city = resolve_param(args, "city", "CITY", "")
    nicho = resolve_param(args, "nicho", "NICHO", "")
    limit = int(resolve_param(args, "limit", "LIMIT", "20"))
    apify_token = env.get("APIFY_TOKEN", "")

    if not apify_token:
        logger.error("APIFY_TOKEN nao configurado")
        output_result(make_result("tiktok", status="error",
                                  errors=["APIFY_TOKEN nao configurado"]))
        sys.exit(1)

    if not query:
        query = nicho or "servico local"

    logger.info(f"Query: {query} | Cidade: {city} | Limite: {limit}")

    start = time.time()
    leads, errors = scrape_tiktok(apify_token, query, city, nicho, limit, logger)

    logger.info(f"Total leads encontrados: {len(leads)}")

    if not args.dry_run:
        existing = load_leads()
        all_leads, new_count = merge_leads(existing, leads, logger)
        save_leads(all_leads, logger)
        total = len(all_leads)
    else:
        new_count = len(leads)
        total = new_count

    duration = round(time.time() - start, 1)
    logger.info(f"Concluido em {duration}s — {new_count} novos, {total} total")

    output_result(make_result(
        agent="tiktok",
        leads_found=len(leads),
        leads_new=new_count,
        leads_total=total,
        query=query,
        city=city,
        errors=errors,
        extra={"duration_sec": duration},
    ))

    sys.exit(1 if errors and not leads else 0)


if __name__ == "__main__":
    main()
