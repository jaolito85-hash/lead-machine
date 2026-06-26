#!/usr/bin/env python3
"""
LEAD MACHINE — Agent Instagram

Busca posts por hashtag/keyword, baixa comentarios, filtra quem tem intencao
de compra (buscando_atendimento, perguntando_preco, perguntando_local) e
grava como lead em leads-db.json.

NAO cria lead do dono do post — dono ja e profissional/divulgador.

Uso:
  python agents/agent_instagram.py --query "harmonizacao facial" --city "Maringa-PR"
  python agents/agent_instagram.py --profiles "dracamilaguerreiro,royalface.maringa" --limit 30

Env vars (runner/serve.py):
  SEARCH_QUERY, CITY, NICHO, LIMIT, PROFILES, APIFY_TOKEN,
  IG_DISCOVERY_LIMIT (default 3), IG_MAX_VIDEOS_PER_PROFILE (default 3),
  IG_MAX_TOTAL_POSTS (default 9), IG_MAX_COMMENTS_PER_POST (default 40),
  IG_MIN_SCORE (default 60)
"""

import sys
import time

from base import (
    build_arg_parser, calculate_score, classify_temp, create_lead, is_bot,
    is_brazilian_portuguese, load_env, load_leads, make_result, merge_leads,
    output_result, resolve_param, save_leads, setup_logger,
    apify_dataset_id
)
from comment_collector import pipeline
import profile_discovery
from query_strategy import social_query_run_plan, social_query_variants


DEFAULT_PROFILES = [
    "dr.viniciuslonghini",
    "royalface.maringa",
    "draflaviatomaroli",
    "draisabelareder",
    "clinicasekai",
    "dracamilaguerreiro",
    "fabrizziavassallo",
    "drharmoniza",
]

_NATIONAL_CITIES = {"brasil", "br", "nacional", "todo brasil", "brazil"}


def _is_national_city(city: str) -> bool:
    return city.strip().lower() in _NATIONAL_CITIES


def _should_skip_city(detected_city: str, wanted_city: str) -> bool:
    if not wanted_city or _is_national_city(wanted_city):
        return False
    det = (detected_city or "").lower().strip()
    if not det:
        return False
    core = wanted_city.lower().split("-")[0].strip()
    return core not in det and det not in core


def comments_to_leads(hot_comments: list, query: str, city: str, nicho: str,
                      min_score: int, logger) -> list:
    leads = []
    skipped_city = 0
    skipped_score = 0
    skipped_bot = 0
    skipped_lang = 0
    skipped_owner = 0

    for c in hot_comments:
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

        if _should_skip_city(c.get("city", ""), city):
            skipped_city += 1
            continue

        detected_city = (c.get("city") or "").strip()
        lead_cidade = detected_city.title() if detected_city else ""

        lead = create_lead(
            plataforma="instagram",
            user=author,
            texto=text,
            url=c.get("video_url") or "",
            cidade=lead_cidade,
            nicho=nicho or query,
            post_owner=c.get("video_owner") or "",
            nome=c.get("author_fullname") or "",
            author_url=c.get("author_url") or (f"https://www.instagram.com/{author}/" if author else ""),
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
        f"Hot={len(hot_comments)} | descartes: bot={skipped_bot}, "
        f"lang!=pt={skipped_lang}, score<{min_score}={skipped_score}, "
        f"cidade={skipped_city}, dono_perfil={skipped_owner} | leads={len(leads)}"
    )
    return leads


def legacy_profile_scrape(apify_token: str, profiles: list, limit: int,
                          city: str, nicho: str, query: str, min_score: int,
                          logger) -> tuple[list, list]:
    from apify_client import ApifyClient

    client = ApifyClient(apify_token)
    urls = []
    for p in profiles:
        p = p.strip()
        if not p.startswith("http"):
            p = f"https://www.instagram.com/{p.lstrip('@')}/"
        urls.append(p)

    errors = []
    leads = []

    run_input = {
        "directUrls": urls,
        "resultsType": "posts",
        "resultsLimit": limit,
        "addParentData": True,
    }
    try:
        logger.info(f"Chamando apify/instagram-scraper (legacy profiles): {len(urls)} perfis")
        run = client.actor("apify/instagram-scraper").call(run_input=run_input)
        items = list(client.dataset(apify_dataset_id(run)).iterate_items())

        for post in items:
            owner = post.get("ownerUsername", "")
            post_url = post.get("url", "")
            for comment in post.get("latestComments", []):
                text = comment.get("text", "")
                user = comment.get("ownerUsername", "")
                if not user or not text or is_bot(text):
                    continue
                if not is_brazilian_portuguese(text):
                    continue
                score = calculate_score(text, city_match=bool(city))
                if score < min_score:
                    continue
                lead = create_lead(
                    plataforma="instagram",
                    user=user,
                    texto=text,
                    url=post_url,
                    cidade="",
                    nicho=nicho or query,
                    post_owner=owner,
                    author_url=f"https://www.instagram.com/{user}/",
                    score=score,
                    temp=classify_temp(score),
                    tipo="pessoa",
                )
                leads.append(lead)
    except Exception as e:
        logger.error(f"Erro no scraping legacy: {e}", exc_info=True)
        errors.append(str(e))

    return leads, errors


def main():
    parser = build_arg_parser("instagram", "Scraper Instagram via Apify (comentarios)")
    args = parser.parse_args()

    env = load_env()
    logger = setup_logger("instagram", verbose=args.verbose)

    query = resolve_param(args, "query", "SEARCH_QUERY", "")
    city = resolve_param(args, "city", "CITY", "")
    nicho = resolve_param(args, "nicho", "NICHO", "")
    limit = int(resolve_param(args, "limit", "LIMIT", "30"))
    profiles_str = resolve_param(args, "profiles", "PROFILES", "")
    apify_token = env.get("APIFY_TOKEN", "")

    max_videos = int(env.get("IG_MAX_VIDEOS", "10"))
    max_comments = int(env.get("IG_MAX_COMMENTS_PER_POST", "40"))
    min_score = int(env.get("IG_MIN_SCORE", "60"))
    discovery_limit = int(env.get("IG_DISCOVERY_LIMIT", env.get("DISCOVERY_LIMIT", "3")))
    max_videos_per_profile = int(env.get("IG_MAX_VIDEOS_PER_PROFILE", "3"))
    max_total_posts = int(env.get("IG_MAX_TOTAL_POSTS", "9"))

    if not apify_token:
        logger.error("APIFY_TOKEN nao configurado")
        output_result(make_result("instagram", status="error",
                                  errors=["APIFY_TOKEN nao configurado"]))
        sys.exit(1)

    profiles = []
    if profiles_str:
        profiles = [p.strip() for p in profiles_str.split(",") if p.strip()]

    start = time.time()
    leads = []
    errors = []
    extras = {}

    if query:
        logger.info(f"Query original: {query} | Cidade: {city} | min_score: {min_score}")
        discovered = []
        is_national = _is_national_city(city) or not city

        use_discovery = (
            not is_national
            and city
            and env.get("SERPAPI_API_KEY", "").strip()
            and env.get("PROFILE_DISCOVERY", "1").strip().lower() not in ("0", "false", "no")
        )
        if use_discovery:
            try:
                discovered = profile_discovery.discover_profiles(
                    nicho=nicho or query,
                    cidade=city,
                    platform="instagram",
                    limit=discovery_limit,
                    logger=logger,
                )
            except Exception as e:
                logger.warning(f"Discovery falhou ({e}), caindo pra hashtag search")

        if discovered:
            logger.info(f"Discovery: {len(discovered)} perfis locais — coletando comentarios")
            try:
                result = pipeline.collect_by_profiles(
                    apify_token=apify_token,
                    platform="instagram",
                    profiles=[p["handle"] for p in discovered],
                    city=city,
                    max_videos_per_profile=max_videos_per_profile,
                    max_total_videos=max_total_posts,
                    max_comments_per_video=max_comments,
                    logger=logger,
                )
            except Exception as e:
                logger.error(f"Falha no pipeline Instagram (discovery): {e}", exc_info=True)
                output_result(make_result("instagram", status="error", errors=[str(e)],
                                          query=query, city=city))
                sys.exit(1)

            logger.info(
                f"Posts={result['videos_found']} | Comentarios={result['comments_collected']} "
                f"| Classificados={result['classified']} | Hot={len(result['hot_comments'])}"
            )
            leads = comments_to_leads(result["hot_comments"], query, city, nicho,
                                      min_score, logger)
            extras = {
                "videos_found": result["videos_found"],
                "comments_collected": result["comments_collected"],
                "hot_comments": len(result["hot_comments"]),
                "used_discovery": True,
                "discovered_profiles": [p["handle"] for p in discovered],
            }
        else:
            query_plan = social_query_variants(query, nicho, platform="instagram")
            if not query_plan:
                query_plan = [query]
            run_plan = social_query_run_plan(query_plan, env)

            logger.info(f"Plano social Instagram: {query_plan}")
            if run_plan != query_plan:
                logger.info(
                    f"Execucao IG desta rodada: {run_plan} "
                    f"(1 query curta por execucao para evitar timeout)"
                )

            totals = {"videos_found": 0, "comments_collected": 0,
                      "classified": 0, "hot_comments": 0}
            successful_queries = 0

            for q in run_plan:
                logger.info(f"Rodando query curta Instagram: '{q}'")
                try:
                    result = pipeline.collect_by_query(
                        apify_token=apify_token,
                        platform="instagram",
                        query=q,
                        city=city,
                        max_videos=max_videos,
                        max_comments_per_video=max_comments,
                        logger=logger,
                    )
                except Exception as e:
                    errors.append(f"{q}: {e}")
                    logger.error(f"Falha no pipeline Instagram ({q}): {e}", exc_info=True)
                    continue

                successful_queries += 1
                hot_comments = result.get("hot_comments", [])
                totals["videos_found"] += result.get("videos_found", 0)
                totals["comments_collected"] += result.get("comments_collected", 0)
                totals["classified"] += result.get("classified", 0)
                totals["hot_comments"] += len(hot_comments)
                logger.info(
                    f"Query '{q}': Posts={result.get('videos_found', 0)} | "
                    f"Comentarios={result.get('comments_collected', 0)} | "
                    f"Classificados={result.get('classified', 0)} | Hot={len(hot_comments)}"
                )
                leads.extend(comments_to_leads(hot_comments, q, city, nicho,
                                               min_score, logger))

            if successful_queries == 0 and errors:
                output_result(make_result("instagram", status="error",
                                          errors=errors or ["nenhuma query rodou"],
                                          query=query, city=city))
                sys.exit(1)

            # Fallback: hashtag retornou 0 comentarios → tenta perfis conhecidos
            fallback_profiles = profiles or DEFAULT_PROFILES
            if totals["comments_collected"] == 0 and not leads and fallback_profiles:
                logger.info(
                    f"Hashtag search sem comentarios — fallback para {len(fallback_profiles)} perfis"
                )
                try:
                    fb_result = pipeline.collect_by_profiles(
                        apify_token=apify_token,
                        platform="instagram",
                        profiles=fallback_profiles,
                        city=city,
                        max_videos_per_profile=max_videos_per_profile,
                        max_total_videos=max_total_posts,
                        max_comments_per_video=max_comments,
                        logger=logger,
                    )
                    fb_hot = fb_result.get("hot_comments", [])
                    totals["videos_found"] += fb_result.get("videos_found", 0)
                    totals["comments_collected"] += fb_result.get("comments_collected", 0)
                    totals["classified"] += fb_result.get("classified", 0)
                    totals["hot_comments"] += len(fb_hot)
                    leads.extend(comments_to_leads(fb_hot, query, city, nicho,
                                                   min_score, logger))
                except Exception as e:
                    logger.warning(f"Fallback perfis falhou: {e}")
                    errors.append(f"fallback_profiles: {e}")

            extras = {
                "videos_found": totals["videos_found"],
                "comments_collected": totals["comments_collected"],
                "hot_comments": totals["hot_comments"],
                "used_discovery": False,
                "query_plan": query_plan,
                "query_run_plan": run_plan,
                "queries_ok": successful_queries,
                "used_profile_fallback": totals["comments_collected"] > 0 and successful_queries > 0,
            }
    else:
        if not profiles:
            profiles = DEFAULT_PROFILES
            logger.info("Sem query/profiles — usando DEFAULT_PROFILES")
        leads, errors = legacy_profile_scrape(
            apify_token, profiles, limit, city, nicho, query,
            min_score, logger,
        )
        extras = {"profiles_count": len(profiles), "mode": "legacy_profiles"}

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
        logger.info("DRY RUN — nao salvou no DB")

    duration = round(time.time() - start, 1)
    logger.info(f"Concluido em {duration}s — {new_count} novos, {total} total")
    extras["duration_sec"] = duration

    output_result(make_result(
        agent="instagram",
        leads_found=len(leads),
        leads_new=new_count,
        leads_total=total,
        query=query or "(profiles)",
        city=city,
        errors=errors,
        extra=extras,
    ))

    sys.exit(0)


if __name__ == "__main__":
    main()