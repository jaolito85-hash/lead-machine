#!/usr/bin/env python3
"""
LEAD MACHINE - Agent YouTube

Busca videos por keyword, baixa comentarios, filtra quem tem intencao de
compra/dor (buscando_atendimento, perguntando_preco, perguntando_local) e
grava como lead em leads-db.json.

NAO cria lead do dono do canal — dono e advogado/influencer/divulgador.

Uso:
  python agents/agent_youtube.py --query "renegociacao divida rural" --city "Brasil"

Env vars (runner/serve.py):
  SEARCH_QUERY, CITY, NICHO, LIMIT, APIFY_TOKEN,
  YOUTUBE_MAX_VIDEOS (default 10), YOUTUBE_MAX_COMMENTS_PER_VIDEO (default 300),
  YOUTUBE_MIN_SCORE (default 60)
"""

import sys
import time

from base import (
    build_arg_parser, classify_temp, create_lead, is_bot,
    is_brazilian_portuguese, load_env, load_leads, make_result, merge_leads,
    output_result, resolve_param, save_leads, setup_logger,
)
from comment_collector import pipeline
from query_strategy import social_query_run_plan, social_query_variants


def _should_skip_city(comment: dict, wanted_city: str) -> bool:
    if not wanted_city:
        return False
    detected = (comment.get("city") or "").lower().strip()
    if not detected:
        return False
    wanted_core = wanted_city.lower().split("-")[0].strip()
    # Cidade vazia ou "Brasil" = busca nacional, nao filtra por cidade
    if wanted_core in ("brasil", "br", ""):
        return False
    return wanted_core not in detected and detected not in wanted_core


def comments_to_leads(comments: list, query: str, city: str, nicho: str,
                      min_score: int, logger) -> list:
    leads = []
    skipped_city = 0
    skipped_score = 0
    skipped_bot = 0
    skipped_lang = 0

    skipped_owner = 0
    for c in comments:
        author = (c.get("author_username") or "").strip().lstrip("@").lower()
        owner = (c.get("video_owner") or "").strip().lstrip("@").lower()
        text = (c.get("text") or "").strip()
        if not author or not text:
            continue
        if author == owner:
            skipped_owner += 1
            continue
        if is_bot(text):
            skipped_bot += 1
            continue
        if not is_brazilian_portuguese(text):
            skipped_lang += 1
            continue

        score = int(c.get("lead_score") or 0)
        if score < min_score:
            skipped_score += 1
            continue

        if _should_skip_city(c, city):
            skipped_city += 1
            continue

        detected_city = (c.get("city") or "").strip()
        lead_cidade = detected_city.title() if detected_city else ""

        author_url = c.get("author_url") or ""
        if not author_url and author:
            # Fallback: usa handle do YouTube
            author_url = f"https://www.youtube.com/@{author}"

        lead = create_lead(
            plataforma="youtube",
            user=author,
            texto=text,
            url=c.get("video_url") or "",
            cidade=lead_cidade,
            nicho=nicho or query,
            post_owner=c.get("video_owner") or "",
            nome=c.get("author_fullname") or "",
            author_url=author_url,
            score=min(100, max(0, score)),
            temp=classify_temp(score),
            tipo="pessoa",
            extra={
                "intent": c.get("intent"),
                "urgency": c.get("urgency"),
                "classifier": "comment_collector",
                "like_count": c.get("like_count") or 0,
            },
        )
        leads.append(lead)

    logger.info(
        f"Comentarios hot: {len(comments)} | "
        f"descartes: bot={skipped_bot}, lang!=pt={skipped_lang}, "
        f"score<{min_score}={skipped_score}, cidade={skipped_city} | "
        f"leads finais: {len(leads)}"
    )
    return leads


def main():
    parser = build_arg_parser("youtube", "Scraper YouTube via Apify (comentarios)")
    args = parser.parse_args()

    env = load_env()
    logger = setup_logger("youtube", verbose=args.verbose)

    query = resolve_param(args, "query", "SEARCH_QUERY", "")
    city = resolve_param(args, "city", "CITY", "")
    nicho = resolve_param(args, "nicho", "NICHO", "")
    apify_token = env.get("APIFY_TOKEN", "")

    max_videos = int(env.get("YOUTUBE_MAX_VIDEOS", "10"))
    max_comments = int(env.get("YOUTUBE_MAX_COMMENTS_PER_VIDEO", "300"))
    min_score = int(env.get("YOUTUBE_MIN_SCORE", "60"))

    if not apify_token:
        logger.error("APIFY_TOKEN nao configurado")
        output_result(make_result("youtube", status="error",
                                  errors=["APIFY_TOKEN nao configurado"]))
        sys.exit(1)

    if not query:
        query = nicho or "servico local"

    query_plan = social_query_variants(query, nicho, platform="youtube")
    if not query_plan:
        query_plan = [query]
    run_plan = social_query_run_plan(query_plan, env)

    logger.info(f"Query original: {query} | Cidade: {city} | min_score: {min_score}")
    logger.info(f"Plano social YouTube: {query_plan}")
    if run_plan != query_plan:
        logger.info(
            f"Execucao YouTube desta rodada: {run_plan} "
            f"(1 query curta por execucao para evitar timeout)"
        )

    start = time.time()
    errors = []
    totals = {"videos_found": 0, "comments_collected": 0, "classified": 0, "hot_comments": 0}
    leads = []
    successful_queries = 0

    for q in run_plan:
        logger.info(f"Rodando query curta YouTube: '{q}'")
        try:
            result = pipeline.collect_by_query(
                apify_token=apify_token,
                platform="youtube",
                query=q,
                city=city,
                max_videos=max_videos,
                max_comments_per_video=max_comments,
                logger=logger,
            )
        except Exception as e:
            msg = f"{q}: {e}"
            errors.append(msg)
            logger.error(f"Falha no pipeline YouTube ({q}): {e}", exc_info=True)
            continue

        successful_queries += 1
        hot_comments = result.get("hot_comments", [])
        totals["videos_found"] += result.get("videos_found", 0)
        totals["comments_collected"] += result.get("comments_collected", 0)
        totals["classified"] += result.get("classified", 0)
        totals["hot_comments"] += len(hot_comments)
        logger.info(
            f"Query '{q}': Videos={result.get('videos_found', 0)} | "
            f"Comentarios={result.get('comments_collected', 0)} | "
            f"Classificados={result.get('classified', 0)} | Hot={len(hot_comments)}"
        )
        leads.extend(comments_to_leads(hot_comments, q, city, nicho, min_score, logger))

    if successful_queries == 0:
        output_result(make_result("youtube", status="error", errors=errors or ["nenhuma query rodou"],
                                  query=query, city=city))
        sys.exit(1)

    new_count = 0
    total = 0
    if not args.dry_run and leads:
        existing = load_leads()
        all_leads, new_count = merge_leads(existing, leads, logger)
        save_leads(all_leads, logger)
        total = len(all_leads)
    elif args.dry_run:
        new_count = len(leads)
        total = new_count

    duration = round(time.time() - start, 1)
    logger.info(f"Concluido em {duration}s — {new_count} novos, {total} total")

    output_result(make_result(
        agent="youtube",
        leads_found=len(leads),
        leads_new=new_count,
        leads_total=total,
        query=query,
        city=city,
        errors=errors,
        extra={
            "duration_sec": duration,
            "query_plan": query_plan,
            "query_run_plan": run_plan,
            "queries_ok": successful_queries,
            "videos_found": totals["videos_found"],
            "comments_collected": totals["comments_collected"],
            "classified": totals["classified"],
            "hot_comments": totals["hot_comments"],
        },
    ))

    sys.exit(0)


if __name__ == "__main__":
    main()