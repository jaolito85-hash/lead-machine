#!/usr/bin/env python3
"""
LEAD MACHINE — Agent Instagram
Busca leads no Instagram via Apify (comentarios, hashtags, perfis).
Foco em descoberta — DMs ficam no lead_machine.py.

Uso:
  python agents/agent_instagram.py --query "harmonizacao facial" --city "Maringa-PR"
  python agents/agent_instagram.py --profiles "dracamilaguerreiro,royalface.maringa" --limit 30

Env vars (Paperclip):
  SEARCH_QUERY, CITY, NICHO, LIMIT, PROFILES, APIFY_TOKEN
"""

import sys
import time

from base import (
    build_arg_parser, calculate_score, classify_temp, create_lead, is_bot,
    load_env, load_leads, make_result, merge_leads, output_result,
    resolve_param, save_leads, setup_logger,
)


# Perfis padrao de clinicas (Maringa) — usados se nenhum profile for passado
DEFAULT_PROFILES = [
    "https://www.instagram.com/dr.viniciuslonghini/",
    "https://www.instagram.com/royalface.maringa/",
    "https://www.instagram.com/draflaviatomaroli/",
    "https://www.instagram.com/draisabelareder/",
    "https://www.instagram.com/clinicasekai/",
    "https://www.instagram.com/dracamilaguerreiro/",
    "https://www.instagram.com/fabrizziavassallo/",
    "https://www.instagram.com/drharmoniza/",
]


def scrape_instagram(apify_token: str, profiles: list, limit: int, query: str,
                     city: str, nicho: str, logger=None) -> list:
    """Busca leads via Apify instagram-scraper."""
    from apify_client import ApifyClient

    client = ApifyClient(apify_token)
    leads = []
    errors = []

    # Modo 1: Scraping de perfis especificos (comentarios de posts)
    if profiles:
        logger.info(f"Scraping {len(profiles)} perfis, limite {limit} posts cada")

        urls = []
        for p in profiles:
            p = p.strip()
            if not p.startswith("http"):
                p = f"https://www.instagram.com/{p.lstrip('@')}/"
            urls.append(p)

        run_input = {
            "directUrls": urls,
            "resultsType": "posts",
            "resultsLimit": limit,
            "addParentData": True,
        }

        try:
            logger.info("Chamando Apify apify/instagram-scraper...")
            run = client.actor("apify/instagram-scraper").call(run_input=run_input)
            dataset_id = run["defaultDatasetId"]
            items = list(client.dataset(dataset_id).iterate_items())
            logger.info(f"Posts baixados: {len(items)}")

            for post in items:
                owner = post.get("ownerUsername", "")
                post_url = post.get("url", "")
                caption = post.get("caption", "")

                for comment in post.get("latestComments", []):
                    text = comment.get("text", "")
                    user = comment.get("ownerUsername", "")

                    if not user or not text:
                        continue
                    if is_bot(text):
                        continue

                    score = calculate_score(text, city_match=bool(city))
                    if score == 0:
                        continue

                    lead = create_lead(
                        plataforma="instagram",
                        user=user,
                        texto=text,
                        url=post_url,
                        cidade=city,
                        nicho=nicho or query,
                        post_owner=owner,
                        score=score,
                        temp=classify_temp(score),
                    )
                    leads.append(lead)

        except Exception as e:
            err = f"Erro no scraping de perfis: {e}"
            logger.error(err)
            errors.append(err)

    # Modo 2: Busca por hashtag (se query fornecida e sem profiles)
    elif query:
        hashtag = query.replace(" ", "").lower()
        logger.info(f"Buscando hashtag #{hashtag}, limite {limit}")

        run_input = {
            "search": hashtag,
            "searchType": "hashtag",
            "resultsLimit": limit,
            "addParentData": True,
        }

        try:
            logger.info("Chamando Apify apify/instagram-scraper (hashtag)...")
            run = client.actor("apify/instagram-scraper").call(run_input=run_input)
            dataset_id = run["defaultDatasetId"]
            items = list(client.dataset(dataset_id).iterate_items())
            logger.info(f"Resultados de hashtag: {len(items)}")

            for post in items:
                owner = post.get("ownerUsername", "")
                post_url = post.get("url", "")
                caption = post.get("caption", "")

                # Verificar se post e relevante (menciona cidade se fornecida)
                if city and city.lower().split("-")[0].strip() not in (caption or "").lower():
                    continue

                # Dono do post pode ser um profissional/clinica
                if owner:
                    bio = post.get("ownerBio", "")
                    full_text = f"{caption} {bio}"
                    score = calculate_score(full_text, city_match=bool(city))
                    if score == 0:
                        score = 55  # Post na hashtag = interesse minimo

                    lead = create_lead(
                        plataforma="instagram",
                        user=owner,
                        texto=caption[:200] if caption else f"Post em #{hashtag}",
                        url=post_url,
                        cidade=city,
                        nicho=nicho or query,
                        score=score,
                        temp=classify_temp(score),
                    )
                    leads.append(lead)

                # Comentarios nos posts da hashtag
                for comment in post.get("latestComments", []):
                    text = comment.get("text", "")
                    user = comment.get("ownerUsername", "")

                    if not user or not text or is_bot(text):
                        continue

                    score = calculate_score(text, city_match=bool(city))
                    if score == 0:
                        continue

                    lead = create_lead(
                        plataforma="instagram",
                        user=user,
                        texto=text,
                        url=post_url,
                        cidade=city,
                        nicho=nicho or query,
                        post_owner=owner,
                        score=score,
                        temp=classify_temp(score),
                    )
                    leads.append(lead)

        except Exception as e:
            err = f"Erro na busca por hashtag: {e}"
            logger.error(err)
            errors.append(err)

    logger.info(f"Total leads encontrados: {len(leads)}")
    return leads, errors


def main():
    parser = build_arg_parser("instagram", "Scraper Instagram via Apify")
    args = parser.parse_args()

    env = load_env()
    logger = setup_logger("instagram", verbose=args.verbose)

    # Resolver parametros
    query = resolve_param(args, "query", "SEARCH_QUERY", "")
    city = resolve_param(args, "city", "CITY", "")
    nicho = resolve_param(args, "nicho", "NICHO", "")
    limit = int(resolve_param(args, "limit", "LIMIT", "30"))
    profiles_str = resolve_param(args, "profiles", "PROFILES", "")
    apify_token = env.get("APIFY_TOKEN", "")

    if not apify_token:
        logger.error("APIFY_TOKEN nao configurado")
        output_result(make_result("instagram", status="error",
                                  errors=["APIFY_TOKEN nao configurado"]))
        sys.exit(1)

    # Resolver profiles
    profiles = []
    if profiles_str:
        profiles = [p.strip() for p in profiles_str.split(",") if p.strip()]
    elif not query:
        profiles = DEFAULT_PROFILES
        logger.info("Usando perfis padrao (clinicas Maringa)")

    logger.info(f"Query: {query or '(sem query)'}")
    logger.info(f"Cidade: {city or '(sem filtro)'}")
    logger.info(f"Profiles: {len(profiles)} | Limite: {limit}")

    # Scraping
    start = time.time()
    leads, errors = scrape_instagram(apify_token, profiles, limit, query, city, nicho, logger)

    # Merge com DB existente
    if not args.dry_run:
        existing = load_leads()
        all_leads, new_count = merge_leads(existing, leads, logger)
        save_leads(all_leads, logger)
        total = len(all_leads)
    else:
        new_count = len(leads)
        total = new_count
        logger.info("DRY RUN — nao salvou no DB")

    duration = round(time.time() - start, 1)
    logger.info(f"Concluido em {duration}s — {new_count} novos, {total} total")

    # Output JSON para Paperclip
    output_result(make_result(
        agent="instagram",
        leads_found=len(leads),
        leads_new=new_count,
        leads_total=total,
        query=query or "(profiles)",
        city=city,
        errors=errors,
        extra={"duration_sec": duration, "profiles_count": len(profiles)},
    ))

    sys.exit(1 if errors and not leads else 0)


if __name__ == "__main__":
    main()
