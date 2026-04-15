#!/usr/bin/env python3
"""
LEAD MACHINE — Agent Facebook
Busca leads no Facebook via Apify (paginas, posts, comentarios).

Uso:
  python agents/agent_facebook.py --query "harmonizacao facial" --city "Maringa-PR"
  python agents/agent_facebook.py --query "clinica estetica" --limit 20

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


def scrape_facebook_pages(apify_token: str, query: str, city: str, limit: int,
                          logger=None) -> tuple:
    """Busca paginas do Facebook via Apify."""
    from apify_client import ApifyClient

    client = ApifyClient(apify_token)
    leads = []
    errors = []

    # Actor 1: Facebook Pages Scraper
    try:
        logger.info(f"Apify facebook-pages-scraper: '{query} {city}'")
        run_input = {
            "startUrls": [],
            "searchQuery": f"{query} {city}",
            "maxPages": min(limit, 50),
            "scrapeAbout": True,
            "scrapePosts": True,
            "maxPosts": 10,
        }

        run = client.actor("apify/facebook-pages-scraper").call(run_input=run_input)
        items = list(client.dataset(run["defaultDatasetId"]).iterate_items())
        logger.info(f"Paginas encontradas: {len(items)}")

        for page in items:
            page_name = page.get("title") or page.get("name") or page.get("pageTitle", "")
            page_url = page.get("url") or page.get("pageUrl", "")

            # Dados da pagina como lead B2B (multiplos formatos possiveis)
            about = page.get("about", {}) if isinstance(page.get("about"), dict) else {}
            info = page.get("info", {}) if isinstance(page.get("info"), dict) else {}
            phone = page.get("phone", "") or about.get("phone", "") or info.get("phone", "")
            email = page.get("email", "") or about.get("email", "") or info.get("email", "")
            website = page.get("website", "") or about.get("website", "") or info.get("website", "")
            address = page.get("address", "") or about.get("address", "") or info.get("address", "")

            # Se nome vazio, tentar outros campos
            if not page_name:
                page_name = page.get("pageTitle") or page.get("pageName") or ""

            if page_name:
                score = 50  # Base: e uma pagina de negocio
                if phone:
                    score += 15
                if email:
                    score += 10
                if website:
                    score += 10
                likes = page.get("likes", 0)
                if likes and likes > 1000:
                    score += 10
                elif likes and likes > 100:
                    score += 5
                score = min(score, 100)

                evidencia = f"Pagina Facebook"
                if likes:
                    evidencia += f" | {likes} curtidas"
                if address:
                    evidencia += f" | {address[:50]}"

                lead = create_lead(
                    plataforma="facebook",
                    user=page_name,
                    texto=evidencia,
                    url=page_url,
                    cidade=city or address,
                    nicho=query,
                    nome=page_name,
                    score=score,
                    temp=classify_temp(score),
                    email=email or None,
                    telefone=phone or None,
                    extra={"website": website, "likes": likes},
                )
                leads.append(lead)

            # Comentarios nos posts da pagina = leads B2C
            posts = page.get("posts", [])
            if isinstance(posts, list):
                for post in posts:
                    post_text = post.get("text", "")
                    post_url_inner = post.get("url", page_url)

                    comments = post.get("comments", [])
                    if isinstance(comments, list):
                        for comment in comments:
                            c_text = comment.get("text", "")
                            c_user = comment.get("userName", comment.get("name", ""))

                            if not c_user or not c_text or is_bot(c_text):
                                continue

                            score = calculate_score(c_text, city_match=bool(city))
                            if score == 0:
                                continue

                            lead = create_lead(
                                plataforma="facebook",
                                user=c_user,
                                texto=c_text,
                                url=post_url_inner,
                                cidade=city,
                                nicho=query,
                                post_owner=page_name,
                                score=score,
                                temp=classify_temp(score),
                            )
                            leads.append(lead)

    except Exception as e:
        err = f"Erro no Facebook scraping: {e}"
        logger.error(err)
        errors.append(err)

    return leads, errors


def main():
    parser = build_arg_parser("facebook", "Scraper Facebook via Apify")
    args = parser.parse_args()

    env = load_env()
    logger = setup_logger("facebook", verbose=args.verbose)

    query = resolve_param(args, "query", "SEARCH_QUERY", "")
    city = resolve_param(args, "city", "CITY", "")
    nicho = resolve_param(args, "nicho", "NICHO", "")
    limit = int(resolve_param(args, "limit", "LIMIT", "20"))
    apify_token = env.get("APIFY_TOKEN", "")

    if not apify_token:
        logger.error("APIFY_TOKEN nao configurado")
        output_result(make_result("facebook", status="error",
                                  errors=["APIFY_TOKEN nao configurado"]))
        sys.exit(1)

    if not query:
        query = nicho or "negocio local"

    logger.info(f"Query: {query} | Cidade: {city} | Limite: {limit}")

    start = time.time()
    leads, errors = scrape_facebook_pages(apify_token, query, city, limit, logger)

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
        agent="facebook",
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
