#!/usr/bin/env python3
"""
LEAD MACHINE — Agent Twitter/X
Busca leads no X (Twitter) via Apify. Marcado como FRAGIL — error handling reforçado.

Uso:
  python agents/agent_twitter.py --query "harmonizacao facial maringa"
  python agents/agent_twitter.py --query "quero botox" --city "Maringa-PR" --limit 20

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

# Keywords de bot especificos do Twitter
TWITTER_BOT_KEYWORDS = [
    "dm me", "link in bio", "check out", "follow me", "free trial",
    "limited offer", "click here", "subscribe", "curso gratis",
    "ganhe seguidores", "compre agora",
]


def scrape_twitter(apify_token: str, query: str, city: str, nicho: str,
                   limit: int, logger=None) -> tuple:
    """Busca leads no Twitter/X via Apify. Actor fragil — trata erros."""
    from apify_client import ApifyClient

    client = ApifyClient(apify_token)
    leads = []
    errors = []

    search_query = query
    if city:
        city_clean = city.split("-")[0].strip()
        search_query = f"{query} {city_clean}"

    try:
        logger.info(f"Apify apidojo/tweet-scraper: '{search_query}'")
        run_input = {
            "searchTerms": [search_query],
            "maxItems": min(limit * 3, 100),
            "sort": "Latest",
            "tweetLanguage": "pt",
        }

        run = client.actor("apidojo/tweet-scraper").call(
            run_input=run_input,
            timeout_secs=180,  # 3 min max — actor fragil
        )
        items = list(client.dataset(run["defaultDatasetId"]).iterate_items())
        logger.info(f"Tweets encontrados: {len(items)}")

        for tweet in items:
            text = tweet.get("full_text", tweet.get("text", ""))
            user = tweet.get("author", tweet.get("user", {}))
            if isinstance(user, dict):
                username = user.get("screen_name", user.get("userName", ""))
                user_name = user.get("name", "")
            else:
                username = str(user)
                user_name = username
            tweet_url = tweet.get("url", tweet.get("tweetUrl", ""))

            if not username or not text:
                continue

            # Filtrar bots (padrao + Twitter-specific)
            if is_bot(text):
                continue
            txt_lower = text.lower()
            if any(bk in txt_lower for bk in TWITTER_BOT_KEYWORDS):
                continue

            # Verificar relevancia
            score = calculate_score(text, city_match=bool(city))

            # Tweet mencionando o tema sem keywords = interesse minimo
            if score == 0:
                query_words = query.lower().split()
                if any(w in txt_lower for w in query_words if len(w) > 3):
                    score = 45  # Mencionou o tema

            if score == 0:
                continue

            # Boost se usuario tem bio relevante
            user_bio = user.get("description", "")
            if user_bio and any(k in user_bio.lower() for k in
                               ["clinica", "dr", "dra", "dentista", "estetica"]):
                score = min(score + 10, 100)

            lead = create_lead(
                plataforma="x",
                user=username,
                texto=text[:280],
                url=tweet_url,
                cidade=city,
                nicho=nicho or query,
                nome=user_name or username,
                score=score,
                temp=classify_temp(score),
                extra={
                    "followers": user.get("followers_count", 0),
                },
            )
            leads.append(lead)

        # Limitar ao pedido
        leads = leads[:limit]

    except Exception as e:
        err = f"Erro no Twitter scraping: {e}"
        logger.error(err)
        logger.warning("Twitter/X scraper e FRAGIL — falhas sao esperadas")
        errors.append(err)

    return leads, errors


def main():
    parser = build_arg_parser("twitter", "Scraper X/Twitter via Apify (fragil)")
    args = parser.parse_args()

    env = load_env()
    logger = setup_logger("twitter", verbose=args.verbose)

    query = resolve_param(args, "query", "SEARCH_QUERY", "")
    city = resolve_param(args, "city", "CITY", "")
    nicho = resolve_param(args, "nicho", "NICHO", "")
    limit = int(resolve_param(args, "limit", "LIMIT", "20"))
    apify_token = env.get("APIFY_TOKEN", "")

    if not apify_token:
        logger.error("APIFY_TOKEN nao configurado")
        output_result(make_result("twitter", status="error",
                                  errors=["APIFY_TOKEN nao configurado"]))
        sys.exit(1)

    if not query:
        query = nicho or "servico local"

    logger.info(f"Query: {query} | Cidade: {city} | Limite: {limit}")
    logger.warning("AVISO: Twitter/X scraper e FRAGIL — pode falhar")

    start = time.time()
    leads, errors = scrape_twitter(apify_token, query, city, nicho, limit, logger)

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
        agent="twitter",
        leads_found=len(leads),
        leads_new=new_count,
        leads_total=total,
        query=query,
        city=city,
        errors=errors,
        extra={"duration_sec": duration, "fragile": True},
    ))

    # Twitter fragil — nao falhar se teve resultados parciais
    sys.exit(1 if errors and not leads else 0)


if __name__ == "__main__":
    main()
