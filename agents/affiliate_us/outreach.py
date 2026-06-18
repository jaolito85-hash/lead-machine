#!/usr/bin/env python3
"""
Geracao de mensagem de outreach (DM) pra um comprador.

Dado um sinal de intent (quem comentou querendo o produto), escreve uma DM
curta, humana e com disclosure de afiliado + o link da oferta correspondente.
Usada pelo endpoint POST /api/local/affiliate/{market}/draft do serve.py.
"""
import json
from pathlib import Path

ROOT = Path(__file__).parent.parent.parent


def _load_env() -> dict:
    env = {}
    f = ROOT / ".env"
    if f.exists():
        for line in f.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip().strip('"').strip("'")
    return env


def find_offer(market: str, product: str):
    """Retorna (link, network, disclosure) da oferta cujo product casa, ou defaults."""
    default_disc = "#publi — link de afiliado, posso receber comissao" if market == "br" \
        else "#ad — affiliate link, I may earn a commission"
    p = ROOT / "agents" / f"affiliate_{market}" / "offers.json"
    if not p.exists():
        return "", "", default_disc
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return "", "", default_disc
    disclosure = (data.get("compliance") or {}).get("disclosure_required") or default_disc
    prod_l = (product or "").strip().lower()
    for o in (data.get("offers") or []):
        if (o.get("product") or "").strip().lower() == prod_l:
            return (o.get("affiliate_link") or ""), (o.get("network") or ""), disclosure
    return "", "", disclosure


def _has_real_link(link: str) -> bool:
    return bool(link) and not link.upper().startswith("PLACEHOLDER")


def _fallback_dm(lang, author, product, link, disclosure):
    shown = link if _has_real_link(link) else ("[SEU LINK]" if lang == "pt" else "[YOUR LINK]")
    if lang == "en":
        msg = (f"Hey @{author}! Saw your comment about {product} — thought you might like "
               f"this one. Check it out:\n{shown}\n{disclosure}")
    else:
        msg = (f"Oi @{author}! Vi seu comentario sobre {product} — acho que voce vai curtir "
               f"esse aqui. Da uma olhada:\n{shown}\n{disclosure}")
    return msg


def generate_dm(market: str, signal: dict) -> dict:
    env = _load_env()
    key = env.get("OPENAI_API_KEY")
    model = env.get("OPENAI_MODEL", "gpt-4o-mini")

    product = signal.get("query") or signal.get("desired_category") or "esse produto"
    author = (signal.get("author") or "").replace("@", "")
    comment = signal.get("text") or ""
    lang = (signal.get("lang") or "").lower() or ("pt" if market == "br" else "en")
    link, network, disclosure = find_offer(market, product)
    has_link = _has_real_link(link)

    if not key:
        return {"message": _fallback_dm(lang, author, product, link, disclosure),
                "link": link, "network": network, "disclosure": disclosure,
                "has_link": has_link, "engine": "fallback"}

    lang_name = {"pt": "Brazilian Portuguese", "en": "English",
                 "es": "Spanish"}.get(lang, "the same language as the comment")
    shown_link = link if has_link else ("[SEU LINK DE AFILIADO]" if lang == "pt" else "[YOUR AFFILIATE LINK]")
    prompt = f"""Write a SHORT, friendly, human direct message (DM) in {lang_name} to @{author},
who publicly commented "{comment}" showing interest in "{product}".

Goal: genuinely recommend "{product}" and share an affiliate link.
Hard rules:
- 2-3 sentences MAX. Casual, warm, like a real person. NEVER spammy, no ALL CAPS, no hype words.
- Naturally reference what they said.
- NO health/medical claims, no "guaranteed", no false promises.
- End with the link on its own line, then the disclosure on its own line.
- Link: {shown_link}
- Disclosure (keep it, verbatim): {disclosure}

Return ONLY the message text, nothing else."""
    try:
        from openai import OpenAI
        client = OpenAI(api_key=key)
        resp = client.chat.completions.create(
            model=model, messages=[{"role": "user", "content": prompt}],
            temperature=0.7, max_tokens=220)
        msg = resp.choices[0].message.content.strip()
        return {"message": msg, "link": link, "network": network,
                "disclosure": disclosure, "has_link": has_link, "engine": model}
    except Exception as e:
        return {"message": _fallback_dm(lang, author, product, link, disclosure),
                "link": link, "network": network, "disclosure": disclosure,
                "has_link": has_link, "engine": f"fallback ({e})"}
