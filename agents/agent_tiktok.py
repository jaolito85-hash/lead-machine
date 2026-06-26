#!/usr/bin/env python3
"""
LEAD MACHINE — Agent TikTok

Busca videos por keyword/cidade, baixa comentarios, filtra quem tem intencao
de compra (buscando_atendimento, perguntando_preco, perguntando_local) e
grava como lead em leads-db.json.

NAO cria lead do autor do video — autor ja fez / e divulgador.

Uso:
  python agents/agent_tiktok.py --query "harmonizacao facial" --city "Maringa-PR"

Env vars (runner/serve.py):
  SEARCH_QUERY, CITY, NICHO, LIMIT, APIFY_TOKEN,
  TIKTOK_MAX_VIDEOS (default 15), TIKTOK_MAX_COMMENTS_PER_VIDEO (default 300),
  TIKTOK_MIN_SCORE (default 60)
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
    """Se cidade foi pedida e o classifier detectou OUTRA cidade, descarta."""
    if not wanted_city:
        return False
    detected = (comment.get("city") or "").lower().strip()
    if not detected:
        return False  # sem cidade detectada = nao descarta (pode ser local)
    wanted_core = wanted_city.lower().split("-")[0].strip()
    return wanted_core not in detected and detected not in wanted_core


def comments_to_leads(comments: list, query: str, city: str, nicho: str,
                      min_score: int, logger) -> list:
    """Converte comentarios 'hot' (ja classificados) em leads unificados."""
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
        # Filtro de idioma: so aceita pt-BR (evita comentarios russos, ingleses, etc)
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

        # Cidade HONESTA: so preenche se o classifier detectou no texto.
        # Nao herda a cidade da query (evitar marcar russo como "Maringa-PR").
        detected_city = (c.get("city") or "").strip()
        lead_cidade = detected_city.title() if detected_city else ""

        lead = create_lead(
            plataforma="tiktok",
            user=author,
            texto=text,
            url=c.get("video_url") or "",
            cidade=lead_cidade,
            nicho=nicho or query,
            post_owner=c.get("video_owner") or "",
            nome=c.get("author_fullname") or "",
            author_url=c.get("author_url") or (f"https://www.tiktok.com/@{author}" if author else ""),
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
    parser = build_arg_parser("tiktok", "Scraper TikTok via Apify (comentarios)")
    args = parser.parse_args()

    env = load_env()
    logger = setup_logger("tiktok", verbose=args.verbose)

    query = resolve_param(args, "query", "SEARCH_QUERY", "")
    city = resolve_param(args, "city", "CITY", "")
    nicho = resolve_param(args, "nicho", "NICHO", "")
    limit = int(resolve_param(args, "limit", "LIMIT", "20"))
    apify_token = env.get("APIFY_TOKEN", "")

    max_videos = int(env.get("TIKTOK_MAX_VIDEOS", "15"))
    max_comments = int(env.get("TIKTOK_MAX_COMMENTS_PER_VIDEO", "300"))
    min_score = int(env.get("TIKTOK_MIN_SCORE", "60"))

    if not apify_token:
        logger.error("APIFY_TOKEN nao configurado")
        output_result(make_result("tiktok", status="error",
                                  errors=["APIFY_TOKEN nao configurado"]))
        sys.exit(1)

    if not query:
        query = nicho or "servico local"

    query_plan = social_query_variants(query, nicho, platform="tiktok")
    if not query_plan:
        query_plan = [query]
    run_plan = social_query_run_plan(query_plan, env)

    logger.info(f"Query original: {query} | Cidade: {city} | min_score: {min_score}")
    logger.info(f"Plano social TikTok: {query_plan}")
    if run_plan != query_plan:
        logger.info(
            f"Execucao TikTok desta rodada: {run_plan} "
            f"(1 query curta por execucao para evitar timeout)"
        )

    start = time.time()
    errors = []
    totals = {"videos_found": 0, "comments_collected": 0, "classified": 0, "hot_comments": 0}
    leads = []
    successful_queries = 0

    for q in run_plan:
        logger.info(f"Rodando query curta TikTok: '{q}'")
        try:
            result = pipeline.collect_by_query(
                apify_token=apify_token,
                platform="tiktok",
                query=q,
                city=city,
                max_videos=max_videos,
                max_comments_per_video=max_comments,
                logger=logger,
            )
        except Exception as e:
            msg = f"{q}: {e}"
            errors.append(msg)
            logger.error(f"Falha no pipeline TikTok ({q}): {e}", exc_info=True)
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
        output_result(make_result("tiktok", status="error", errors=errors or ["nenhuma query rodou"],
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
        agent="tiktok",
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