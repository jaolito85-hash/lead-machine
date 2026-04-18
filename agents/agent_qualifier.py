#!/usr/bin/env python3
"""
LEAD MACHINE — Agent Qualificador
Re-score e classifica leads com logica multi-fator + cross-platform.

Uso:
  python agents/agent_qualifier.py
  python agents/agent_qualifier.py --limit 50 --filter frio

Env vars (Paperclip):
  LIMIT, FILTER
"""

import sys
import time
from collections import defaultdict

from base import (
    INTEREST_KEYWORDS, build_arg_parser, classify_temp, load_env, load_leads,
    make_result, output_result, resolve_param, save_leads, setup_logger,
)
import telegram_notifier
from datetime import datetime


def qualify_lead(lead: dict, cross_platform: dict) -> dict:
    """
    Re-score um lead com logica multi-fator:
    - Texto/evidencia (keywords de interesse)
    - Completude de contato (tem email/telefone?)
    - Presenca cross-platform
    - Rating/reviews (para leads B2B)
    - Temperatura atual
    """
    score = 0
    reasons = []

    text = (lead.get("texto_original") or lead.get("text") or "").lower()
    plataforma = lead.get("plataforma", "")

    # ── Fator 1: Intencao no texto (0-85 pts) — sinal DOMINANTE para B2C ──
    direct_intent = ["quero", "agenda", "agendar", "gostaria", "me indica",
                     "indicacao", "como faco"]
    price_intent = ["valor", "preco", "quanto custa", "quanto", "orcamento",
                    "parcela", "convenio"]
    soft_intent = ["sonho", "queria", "interessada", "interessado", "recomenda",
                   "alguem conhece"]

    if any(k in text for k in direct_intent):
        score += 85
        reasons.append("intencao direta")
    elif any(k in text for k in price_intent):
        score += 85
        reasons.append("consulta de preco")
    elif any(k in text for k in soft_intent):
        score += 60
        reasons.append("interesse indireto")
    elif any(k in text for k in INTEREST_KEYWORDS):
        score += 50
        reasons.append("keywords de interesse")

    # ── Fator 2: Completude de contato (0-10 pts) — bonus ──
    if lead.get("email"):
        score += 5
        reasons.append("tem email")
    if lead.get("telefone"):
        score += 5
        reasons.append("tem telefone")

    # ── Fator 3: Dados do negocio — B2B (0-80 pts para Google) ──
    if plataforma == "google":
        # Leads B2B sao negocios reais — base alta
        score = max(score, 50)  # Minimo morno: e um negocio real encontrado
        reasons.append("negocio Google Maps")

        rating = lead.get("rating", 0)
        reviews = lead.get("reviews_count", 0)
        if rating >= 4.5:
            score += 15
            reasons.append(f"rating {rating}")
        elif rating >= 4.0:
            score += 8
        elif rating >= 3.5:
            score += 3
        if reviews >= 100:
            score += 10
            reasons.append(f"{reviews} avaliacoes")
        elif reviews >= 50:
            score += 7
        elif reviews >= 10:
            score += 3
        if lead.get("website"):
            score += 5
            reasons.append("tem website")

    # ── Fator 4: Cross-platform (0-10 pts) ──
    user_key = (lead.get("user") or lead.get("nome") or "").lower().strip()
    if user_key and user_key in cross_platform:
        platforms = cross_platform[user_key]
        if len(platforms) > 1:
            score += 10
            reasons.append(f"presente em {len(platforms)} plataformas")

    # ── Fator 5: Penalidades ──
    # Texto muito curto
    if len(text.strip()) < 10 and score > 0:
        score = max(score - 5, 30)

    # Emojis sem substancia (so emojis, sem palavras)
    import re
    words_only = re.sub(r'[^\w\s]', '', text).strip()
    if len(words_only) < 5 and score > 30:
        score = max(score - 10, 25)

    # Cap at 100
    score = min(score, 100)

    return {
        "score": score,
        "temp": classify_temp(score),
        "reasons": reasons,
    }


def build_cross_platform_map(leads: list) -> dict:
    """
    Mapeia usuarios que aparecem em multiplas plataformas.
    Retorna: { "nome_lower": set("instagram", "google", ...) }
    """
    user_platforms = defaultdict(set)
    for lead in leads:
        user_key = (lead.get("user") or lead.get("nome") or "").lower().strip()
        if user_key:
            user_platforms[user_key].add(lead.get("plataforma", "unknown"))
    return user_platforms


def main():
    parser = build_arg_parser("qualifier", "Qualificador de leads (re-scoring)")
    parser.add_argument("--filter", "-f", help="Filtrar por temp: quente, morno, frio (ou env FILTER)")
    parser.add_argument("--requalify", action="store_true",
                        help="Re-qualificar mesmo leads ja qualificados")
    args = parser.parse_args()

    env = load_env()
    logger = setup_logger("qualifier", verbose=args.verbose)

    limit = int(resolve_param(args, "limit", "LIMIT", "100"))
    temp_filter = resolve_param(args, "filter", "FILTER", "")

    # Carregar leads
    leads = load_leads()
    if not leads:
        logger.warning("Nenhum lead no banco")
        output_result(make_result("qualifier", leads_total=0))
        sys.exit(0)

    logger.info(f"Total leads no banco: {len(leads)}")

    # Filtrar leads para qualificar
    to_qualify = []
    for lead in leads:
        # Ja qualificado? Skip (a menos que --requalify)
        if lead.get("qualified") and not args.requalify:
            continue
        # Filtro de temperatura
        if temp_filter and lead.get("temp") != temp_filter:
            continue
        to_qualify.append(lead)

    to_qualify = to_qualify[:limit]
    logger.info(f"Leads para qualificar: {len(to_qualify)}")

    # Construir mapa cross-platform
    cross_platform = build_cross_platform_map(leads)

    start = time.time()
    stats = {"quente": 0, "morno": 0, "frio": 0}
    upgraded = 0
    downgraded = 0
    new_hot_leads = []  # leads que ficaram quentes agora e ainda nao foram notificados

    for i, lead in enumerate(to_qualify):
        old_temp = lead.get("temp", "")
        old_score = lead.get("score", 0)

        result = qualify_lead(lead, cross_platform)

        lead["score"] = result["score"]
        lead["temp"] = result["temp"]
        lead["qualified"] = True

        # Atualizar etapa
        if lead.get("etapa") == "descoberto":
            lead["etapa"] = "qualificado"

        # Tracking
        stats[result["temp"]] += 1
        if result["score"] > old_score:
            upgraded += 1
        elif result["score"] < old_score:
            downgraded += 1

        # Detecta leads que viraram quentes e ainda nao foram notificados
        if result["temp"] == "quente" and not lead.get("notified_at"):
            new_hot_leads.append(lead)

        if args.verbose:
            logger.debug(
                f"  [{i+1}] {lead.get('nome', '?')}: "
                f"{old_score}→{result['score']} ({old_temp}→{result['temp']}) "
                f"[{', '.join(result['reasons'])}]"
            )

    # ── Notificacoes Telegram ──
    notified = 0
    if new_hot_leads and telegram_notifier.is_configured():
        logger.info(f"Notificando {len(new_hot_leads)} novos leads quentes no Telegram...")
        for lead in new_hot_leads:
            if telegram_notifier.notify_hot_lead(lead):
                lead["notified_at"] = datetime.now().isoformat()
                notified += 1
        if notified > 0:
            telegram_notifier.notify_batch_summary({
                "novos_quentes": notified,
                "quentes": stats["quente"],
                "mornos": stats["morno"],
                "frios": stats["frio"],
                "duration_sec": round(time.time() - start, 1),
            })
    elif new_hot_leads and not telegram_notifier.is_configured():
        logger.info(f"{len(new_hot_leads)} leads quentes novos - Telegram nao configurado (skip).")

    # Salvar
    if not args.dry_run:
        save_leads(leads, logger)

    duration = round(time.time() - start, 1)

    logger.info(f"Qualificacao concluida em {duration}s")
    logger.info(f"  Quentes: {stats['quente']} | Mornos: {stats['morno']} | Frios: {stats['frio']}")
    logger.info(f"  Score subiu: {upgraded} | Score desceu: {downgraded}")

    output_result(make_result(
        agent="qualifier",
        leads_found=len(to_qualify),
        leads_new=0,
        leads_total=len(leads),
        extra={
            "duration_sec": duration,
            "qualified": len(to_qualify),
            "quentes": stats["quente"],
            "mornos": stats["morno"],
            "frios": stats["frio"],
            "upgraded": upgraded,
            "downgraded": downgraded,
            "notified_telegram": notified,
        },
    ))

    sys.exit(0)


if __name__ == "__main__":
    main()
