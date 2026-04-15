#!/usr/bin/env python3
"""
LEAD MACHINE — Agent Enriquecedor
Enriquece leads existentes com email/telefone via Apollo.io + Hunter.io + Firecrawl.

Uso:
  python agents/agent_enricher.py --limit 20
  python agents/agent_enricher.py --filter quente --limit 10

Env vars (Paperclip):
  LIMIT, FILTER, APOLLO_API_KEY, HUNTER_API_KEY, FIRECRAWL_API_KEY, APIFY_TOKEN
"""

import sys
import time

import requests

from base import (
    build_arg_parser, load_env, load_leads, make_result, output_result,
    resolve_param, save_leads, setup_logger,
)


# ════════════════════════════════════════
# APOLLO.IO
# ════════════════════════════════════════

def enrich_apollo(api_key: str, nome: str, cidade: str, nicho: str = "",
                  logger=None) -> dict:
    """Busca contato via Apollo.io (header x-api-key, NAO na URL)."""
    url = "https://api.apollo.io/api/v1/mixed_people/search"
    headers = {
        "Content-Type": "application/json",
        "Cache-Control": "no-cache",
        "x-api-key": api_key,
    }

    # Montar busca
    body = {
        "per_page": 3,
        "page": 1,
    }

    # Buscar por nome da pessoa/empresa
    if nome:
        body["q_keywords"] = nome

    # Filtrar por cidade
    if cidade:
        city_clean = cidade.split("-")[0].strip()
        body["person_locations"] = [city_clean]

    # Filtrar por nicho/titulo
    if nicho:
        body["person_titles"] = [nicho]

    try:
        resp = requests.post(url, json=body, headers=headers, timeout=15)
        resp.raise_for_status()
        data = resp.json()

        people = data.get("people", [])
        if not people:
            return {}

        person = people[0]
        result = {}

        email = person.get("email")
        if email:
            result["email"] = email

        phone = person.get("phone_number")
        if not phone:
            phones = person.get("phone_numbers", [])
            if phones:
                phone = phones[0].get("sanitized_number", "")
        if phone:
            result["telefone"] = phone

        linkedin = person.get("linkedin_url")
        if linkedin:
            result["linkedin"] = linkedin

        org = person.get("organization", {})
        if org:
            result["empresa"] = org.get("name", "")

        return result

    except requests.exceptions.HTTPError as e:
        if logger:
            logger.warning(f"Apollo.io erro HTTP para '{nome}': {e}")
    except Exception as e:
        if logger:
            logger.warning(f"Apollo.io erro para '{nome}': {e}")

    return {}


# ════════════════════════════════════════
# HUNTER.IO
# ════════════════════════════════════════

def enrich_hunter(api_key: str, domain: str, logger=None) -> list:
    """Busca emails por dominio via Hunter.io."""
    url = "https://api.hunter.io/v2/domain-search"
    params = {
        "domain": domain,
        "api_key": api_key,
        "limit": 5,
    }

    try:
        resp = requests.get(url, params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()

        emails = []
        for email_data in data.get("data", {}).get("emails", []):
            email = email_data.get("value", "")
            if email:
                emails.append(email)

        return emails

    except Exception as e:
        if logger:
            logger.warning(f"Hunter.io erro para '{domain}': {e}")
    return []


# ════════════════════════════════════════
# FIRECRAWL
# ════════════════════════════════════════

def enrich_firecrawl(api_key: str, url: str, logger=None) -> dict:
    """Scrape website para extrair contatos via Firecrawl."""
    endpoint = "https://api.firecrawl.dev/v1/scrape"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }
    body = {
        "url": url,
        "formats": ["markdown"],
    }

    try:
        resp = requests.post(endpoint, json=body, headers=headers, timeout=30)
        resp.raise_for_status()
        data = resp.json()

        content = data.get("data", {}).get("markdown", "")
        if not content:
            return {}

        result = {}
        # Extrair emails do conteudo
        import re
        emails = re.findall(r'[\w.+-]+@[\w-]+\.[\w.-]+', content)
        if emails:
            # Filtrar emails genericos
            good_emails = [e for e in emails if not any(
                x in e.lower() for x in ["example", "test", "noreply", "no-reply"]
            )]
            if good_emails:
                result["email"] = good_emails[0]

        # Extrair telefones brasileiros
        phones = re.findall(
            r'(?:\+55\s?)?(?:\(?\d{2}\)?[\s.-]?)?\d{4,5}[\s.-]?\d{4}',
            content
        )
        if phones:
            result["telefone"] = phones[0].strip()

        # Extrair WhatsApp
        whatsapp = re.findall(
            r'(?:whatsapp|wpp|zap)[\s:]*[\+]?[\d\s\(\)\-\.]+',
            content, re.IGNORECASE
        )
        if whatsapp and "telefone" not in result:
            phone_match = re.findall(r'[\d\(\)\-\.\+\s]{8,}', whatsapp[0])
            if phone_match:
                result["telefone"] = phone_match[0].strip()

        return result

    except Exception as e:
        if logger:
            logger.warning(f"Firecrawl erro para '{url}': {e}")
    return {}


# ════════════════════════════════════════
# APIFY CONTACT SCRAPER
# ════════════════════════════════════════

def enrich_apify_contact(apify_token: str, url: str, logger=None) -> dict:
    """Extrai contatos de website via Apify contact-info-scraper."""
    from apify_client import ApifyClient

    client = ApifyClient(apify_token)
    try:
        run_input = {
            "startUrls": [{"url": url}],
            "maxRequestsPerCrawl": 5,
        }
        run = client.actor("vdrmota/contact-info-scraper").call(run_input=run_input)
        items = list(client.dataset(run["defaultDatasetId"]).iterate_items())

        result = {}
        for item in items:
            emails = item.get("emails", [])
            if emails and "email" not in result:
                result["email"] = emails[0]
            phones = item.get("phones", [])
            if phones and "telefone" not in result:
                result["telefone"] = phones[0]

        return result

    except Exception as e:
        if logger:
            logger.warning(f"Apify contact-scraper erro para '{url}': {e}")
    return {}


# ════════════════════════════════════════
# MAIN
# ════════════════════════════════════════

def main():
    parser = build_arg_parser("enricher", "Enriquecedor de leads (Apollo + Hunter + Firecrawl)")
    parser.add_argument("--filter", "-f", help="Filtrar por temp: quente, morno, frio (ou env FILTER)")
    args = parser.parse_args()

    env = load_env()
    logger = setup_logger("enricher", verbose=args.verbose)

    # APIs disponiveis
    apollo_key = env.get("APOLLO_API_KEY", "")
    hunter_key = env.get("HUNTER_API_KEY", "")
    firecrawl_key = env.get("FIRECRAWL_API_KEY", "")
    apify_token = env.get("APIFY_TOKEN", "")

    limit = int(resolve_param(args, "limit", "LIMIT", "20"))
    temp_filter = resolve_param(args, "filter", "FILTER", "")

    apis = []
    if apollo_key:
        apis.append("Apollo.io")
    if hunter_key:
        apis.append("Hunter.io")
    if firecrawl_key:
        apis.append("Firecrawl")
    if apify_token:
        apis.append("Apify Contact")

    if not apis:
        logger.error("Nenhuma API de enriquecimento configurada")
        output_result(make_result("enricher", status="error",
                                  errors=["Nenhuma API configurada"]))
        sys.exit(1)

    logger.info(f"APIs disponiveis: {', '.join(apis)}")
    logger.info(f"Limite: {limit} leads | Filtro: {temp_filter or 'todos'}")

    # Carregar leads
    leads = load_leads()
    if not leads:
        logger.warning("Nenhum lead no banco")
        output_result(make_result("enricher", leads_total=0))
        sys.exit(0)

    # Filtrar leads que precisam de enriquecimento
    to_enrich = []
    for lead in leads:
        # Ja tem email E telefone? Skip
        if lead.get("email") and lead.get("telefone"):
            continue
        # Filtro de temperatura
        if temp_filter and lead.get("temp") != temp_filter:
            continue
        to_enrich.append(lead)

    # Priorizar por score (quentes primeiro)
    to_enrich.sort(key=lambda l: l.get("score", 0), reverse=True)
    to_enrich = to_enrich[:limit]

    logger.info(f"Leads para enriquecer: {len(to_enrich)} (de {len(leads)} total)")

    start = time.time()
    enriched_count = 0
    errors = []

    for i, lead in enumerate(to_enrich):
        nome = lead.get("nome", "")
        cidade = lead.get("cidade", "")
        nicho = lead.get("nicho", "")
        website = lead.get("website", "")
        url = lead.get("url", "")
        plataforma = lead.get("plataforma", "")

        logger.info(f"[{i+1}/{len(to_enrich)}] Enriquecendo: {nome or lead.get('user', '?')}")

        contact_found = False

        # 1. Apollo.io — buscar por nome + cidade
        if apollo_key and not lead.get("email"):
            result = enrich_apollo(apollo_key, nome, cidade, nicho, logger)
            if result:
                if result.get("email") and not lead.get("email"):
                    lead["email"] = result["email"]
                    contact_found = True
                if result.get("telefone") and not lead.get("telefone"):
                    lead["telefone"] = result["telefone"]
                    contact_found = True
                if result.get("linkedin"):
                    lead["linkedin"] = result["linkedin"]
                logger.info(f"  Apollo: {result}")

        # 2. Hunter.io — buscar por dominio (se tem website)
        if hunter_key and not lead.get("email") and website:
            import re
            domain_match = re.search(r'https?://(?:www\.)?([^/]+)', website)
            if domain_match:
                domain = domain_match.group(1)
                emails = enrich_hunter(hunter_key, domain, logger)
                if emails:
                    lead["email"] = emails[0]
                    contact_found = True
                    logger.info(f"  Hunter: {emails[0]}")

        # 3. Firecrawl — scrape do website
        if firecrawl_key and website and (not lead.get("email") or not lead.get("telefone")):
            result = enrich_firecrawl(firecrawl_key, website, logger)
            if result:
                if result.get("email") and not lead.get("email"):
                    lead["email"] = result["email"]
                    contact_found = True
                if result.get("telefone") and not lead.get("telefone"):
                    lead["telefone"] = result["telefone"]
                    contact_found = True
                logger.info(f"  Firecrawl: {result}")

        # 4. Apify contact scraper — fallback
        if apify_token and website and not lead.get("email") and not lead.get("telefone"):
            result = enrich_apify_contact(apify_token, website, logger)
            if result:
                if result.get("email") and not lead.get("email"):
                    lead["email"] = result["email"]
                    contact_found = True
                if result.get("telefone") and not lead.get("telefone"):
                    lead["telefone"] = result["telefone"]
                    contact_found = True
                logger.info(f"  Apify Contact: {result}")

        # Atualizar etapa se encontrou contato
        if contact_found:
            enriched_count += 1
            if lead.get("etapa") in ("descoberto", "qualificado"):
                lead["etapa"] = "enriquecido"

        # Rate limiting: 1 segundo entre requests
        if i < len(to_enrich) - 1:
            time.sleep(1)

    # Salvar
    if not args.dry_run:
        save_leads(leads, logger)

    duration = round(time.time() - start, 1)
    logger.info(f"Concluido em {duration}s — {enriched_count}/{len(to_enrich)} enriquecidos")

    output_result(make_result(
        agent="enricher",
        leads_found=len(to_enrich),
        leads_new=enriched_count,
        leads_total=len(leads),
        errors=errors,
        extra={
            "duration_sec": duration,
            "enriched": enriched_count,
            "apis_used": apis,
        },
    ))

    sys.exit(0)


if __name__ == "__main__":
    main()
