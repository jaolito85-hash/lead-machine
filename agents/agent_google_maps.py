#!/usr/bin/env python3
"""
LEAD MACHINE — Agent Google Maps
Busca negocios locais via Google Places API (New) + SerpAPI + Apify fallback.
Gera leads B2B (clinicas, profissionais, empresas).

Uso:
  python agents/agent_google_maps.py --query "clinica harmonizacao facial" --city "Maringa-PR"
  python agents/agent_google_maps.py --query "dentista" --city "Londrina-PR" --limit 20

Env vars (Paperclip):
  SEARCH_QUERY, CITY, NICHO, LIMIT, GOOGLE_PLACES_API_KEY, SERPAPI_API_KEY, APIFY_TOKEN
"""

import sys
import time

import requests

from base import (
    build_arg_parser, classify_temp, create_lead, load_env, load_leads,
    make_result, merge_leads, output_result, resolve_param, save_leads,
    setup_logger,
)


def score_business(biz: dict) -> int:
    """Score para negocio local baseado em completude de dados."""
    score = 40  # base: apareceu na busca

    if biz.get("telefone"):
        score += 20
    if biz.get("website"):
        score += 15
    rating = biz.get("rating", 0)
    if rating >= 4.5:
        score += 15
    elif rating >= 4.0:
        score += 10
    elif rating >= 3.5:
        score += 5
    reviews = biz.get("reviews_count", 0)
    if reviews >= 100:
        score += 10
    elif reviews >= 50:
        score += 7
    elif reviews >= 10:
        score += 3

    return min(score, 100)


def build_biz_evidencia(biz: dict) -> str:
    """Constroi evidencia para negocio."""
    parts = []
    if biz.get("rating"):
        parts.append(f"{biz['rating']} estrelas")
    if biz.get("reviews_count"):
        parts.append(f"{biz['reviews_count']} avaliacoes")
    if biz.get("website"):
        parts.append(f"site: {biz['website'][:50]}")
    if biz.get("endereco"):
        parts.append(biz["endereco"][:60])
    return " | ".join(parts) if parts else "Encontrado no Google Maps"


# ════════════════════════════════════════
# GOOGLE PLACES API (New)
# ════════════════════════════════════════

def search_google_places(api_key: str, query: str, city: str, limit: int,
                         logger=None) -> list:
    """Busca negocios via Google Places API (New) — Text Search."""
    url = "https://places.googleapis.com/v1/places:searchText"
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": api_key,
        "X-Goog-FieldMask": (
            "places.displayName,places.formattedAddress,places.nationalPhoneNumber,"
            "places.internationalPhoneNumber,places.websiteUri,places.rating,"
            "places.userRatingCount,places.googleMapsUri,places.shortFormattedAddress,"
            "places.types,places.id"
        ),
    }
    body = {
        "textQuery": f"{query} {city}",
        "languageCode": "pt-BR",
        "maxResultCount": min(limit, 20),  # API max is 20 per request
    }

    businesses = []
    try:
        logger.info(f"Google Places API: '{query} {city}'")
        resp = requests.post(url, json=body, headers=headers, timeout=30)
        resp.raise_for_status()
        data = resp.json()

        for place in data.get("places", []):
            biz = {
                "nome": place.get("displayName", {}).get("text", ""),
                "endereco": place.get("formattedAddress", ""),
                "telefone": (place.get("nationalPhoneNumber")
                             or place.get("internationalPhoneNumber", "")),
                "website": place.get("websiteUri", ""),
                "rating": place.get("rating", 0),
                "reviews_count": place.get("userRatingCount", 0),
                "maps_url": place.get("googleMapsUri", ""),
                "place_id": place.get("id", ""),
            }
            businesses.append(biz)

        logger.info(f"Google Places: {len(businesses)} negocios encontrados")

    except requests.exceptions.HTTPError as e:
        logger.error(f"Google Places API erro HTTP: {e}")
        if resp.status_code == 403:
            logger.error("Verifique se a Places API (New) esta ativada no Google Cloud")
    except Exception as e:
        logger.error(f"Google Places API erro: {e}")

    return businesses


# ════════════════════════════════════════
# SERPAPI (Fallback)
# ════════════════════════════════════════

def search_serpapi(api_key: str, query: str, city: str, limit: int,
                   logger=None) -> list:
    """Busca negocios via SerpAPI Google Maps."""
    url = "https://serpapi.com/search"
    params = {
        "engine": "google_maps",
        "q": f"{query} {city}",
        "hl": "pt-br",
        "type": "search",
        "api_key": api_key,
    }

    businesses = []
    try:
        logger.info(f"SerpAPI Google Maps: '{query} {city}'")
        resp = requests.get(url, params=params, timeout=30)
        resp.raise_for_status()
        data = resp.json()

        for place in data.get("local_results", [])[:limit]:
            biz = {
                "nome": place.get("title", ""),
                "endereco": place.get("address", ""),
                "telefone": place.get("phone", ""),
                "website": place.get("website", ""),
                "rating": place.get("rating", 0),
                "reviews_count": place.get("reviews", 0),
                "maps_url": place.get("link", ""),
                "place_id": place.get("place_id", ""),
            }
            businesses.append(biz)

        logger.info(f"SerpAPI: {len(businesses)} negocios encontrados")

    except Exception as e:
        logger.error(f"SerpAPI erro: {e}")

    return businesses


# ════════════════════════════════════════
# APIFY (Fallback)
# ════════════════════════════════════════

def search_apify_google_maps(apify_token: str, query: str, city: str, limit: int,
                              logger=None) -> list:
    """Busca negocios via Apify compass/crawler-google-places."""
    from apify_client import ApifyClient

    client = ApifyClient(apify_token)
    businesses = []

    try:
        logger.info(f"Apify crawler-google-places: '{query} {city}'")
        run_input = {
            "searchStringsArray": [f"{query} {city}"],
            "maxCrawledPlacesPerSearch": limit,
            "language": "pt-BR",
            "includeReviews": False,
        }

        run = client.actor("compass/crawler-google-places").call(run_input=run_input)
        items = list(client.dataset(run["defaultDatasetId"]).iterate_items())

        for place in items:
            biz = {
                "nome": place.get("title", ""),
                "endereco": place.get("address", ""),
                "telefone": place.get("phone", ""),
                "website": place.get("website", ""),
                "rating": place.get("totalScore", 0),
                "reviews_count": place.get("reviewsCount", 0),
                "maps_url": place.get("url", ""),
                "place_id": place.get("placeId", ""),
            }
            businesses.append(biz)

        logger.info(f"Apify Google Maps: {len(businesses)} negocios encontrados")

    except Exception as e:
        logger.error(f"Apify Google Maps erro: {e}")

    return businesses


def main():
    parser = build_arg_parser("google_maps", "Scraper Google Maps (negocios locais)")
    args = parser.parse_args()

    env = load_env()
    logger = setup_logger("google_maps", verbose=args.verbose)

    # Resolver parametros
    query = resolve_param(args, "query", "SEARCH_QUERY", "")
    city = resolve_param(args, "city", "CITY", "")
    nicho = resolve_param(args, "nicho", "NICHO", "")
    limit = int(resolve_param(args, "limit", "LIMIT", "20"))

    google_key = env.get("GOOGLE_PLACES_API_KEY", "")
    serpapi_key = env.get("SERPAPI_API_KEY", "")
    apify_token = env.get("APIFY_TOKEN", "")

    if not query:
        query = nicho or "negocio local"

    if not any([google_key, serpapi_key, apify_token]):
        logger.error("Nenhuma API key configurada (Google Places, SerpAPI ou Apify)")
        output_result(make_result("google_maps", status="error",
                                  errors=["Nenhuma API key configurada"]))
        sys.exit(1)

    logger.info(f"Query: {query} | Cidade: {city} | Limite: {limit}")

    # Buscar negocios (cascata de fallback)
    start = time.time()
    businesses = []
    errors = []

    if google_key:
        businesses = search_google_places(google_key, query, city, limit, logger)

    if not businesses and serpapi_key:
        logger.info("Google Places sem resultados, tentando SerpAPI...")
        businesses = search_serpapi(serpapi_key, query, city, limit, logger)

    if not businesses and apify_token:
        logger.info("SerpAPI sem resultados, tentando Apify...")
        businesses = search_apify_google_maps(apify_token, query, city, limit, logger)

    if not businesses:
        errors.append("Nenhum negocio encontrado em nenhuma fonte")
        logger.warning("Nenhum negocio encontrado")

    # Converter negocios em leads
    leads = []
    for biz in businesses:
        score = score_business(biz)
        evidencia = build_biz_evidencia(biz)

        lead = create_lead(
            plataforma="google",
            user=biz["nome"],
            texto=evidencia,
            url=biz.get("maps_url", ""),
            cidade=city or biz.get("endereco", ""),
            nicho=nicho or query,
            nome=biz["nome"],
            score=score,
            temp=classify_temp(score),
            telefone=biz.get("telefone") or None,
            tipo="empresa",
            extra={
                "website": biz.get("website", ""),
                "endereco": biz.get("endereco", ""),
                "rating": biz.get("rating", 0),
                "reviews_count": biz.get("reviews_count", 0),
            },
        )
        leads.append(lead)

    logger.info(f"Leads B2B criados: {len(leads)}")

    # Merge com DB
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

    output_result(make_result(
        agent="google_maps",
        leads_found=len(leads),
        leads_new=new_count,
        leads_total=total,
        query=query,
        city=city,
        errors=errors,
        extra={"duration_sec": duration, "source": "google_places" if google_key else "serpapi" if serpapi_key else "apify"},
    ))

    sys.exit(1 if errors and not leads else 0)


if __name__ == "__main__":
    main()
