"""
LEAD MACHINE — Automacao Completa
Scraping de leads + Envio de DM + Agendamento automatico

Fluxo:
  1. Apify scrape Instagram (comentarios de clinicas)
  2. Filtra leads reais (quem pergunta preco, diz que quer)
  3. Remove bots e spam
  4. Envia DM automatico pelo Instagram
  5. Salva tudo em JSON (CRM)
  6. Roda em loop (heartbeat a cada X minutos)

Uso:
  python agents/lead_machine.py --scrape              # so buscar leads
  python agents/lead_machine.py --send                # so enviar DMs
  python agents/lead_machine.py --full                # buscar + enviar
  python agents/lead_machine.py --loop 60             # rodar a cada 60 min
"""

import json
import time
import os
import sys
import argparse
from datetime import datetime
from pathlib import Path

# ─── CONFIG ───
BASE_DIR = Path(__file__).parent.parent
ENV_PATH = BASE_DIR / ".env"
LEADS_DB = BASE_DIR / "leads-export" / "leads-db.json"
SENT_DB = BASE_DIR / "leads-export" / "sent-db.json"
LOG_FILE = BASE_DIR / "leads-export" / "automation.log"

# Perfis de clinicas de Maringa pra monitorar
CLINIC_PROFILES = [
    "https://www.instagram.com/dr.viniciuslonghini/",
    "https://www.instagram.com/royalface.maringa/",
    "https://www.instagram.com/draflaviatomaroli/",
    "https://www.instagram.com/draisabelareder/",
    "https://www.instagram.com/clinicasekai/",
    "https://www.instagram.com/dracamilaguerreiro/",
    "https://www.instagram.com/fabrizziavassallo/",
    "https://www.instagram.com/drharmoniza/",
]

# Palavras que indicam interesse REAL
INTEREST_KEYWORDS = [
    "quero", "quanto custa", "preco", "valor", "agenda", "agendar",
    "queria", "sonho", "gostaria", "interessada", "interessado",
    "onde fica", "como faco", "parcela", "convenio", "orcamento",
    "aceita", "qual o", "quanto", "informacao", "contato",
    "whatsapp", "telefone", "atende",
]

# Palavras que indicam bot/spam
BOT_KEYWORDS = [
    "solucao", "crescimento", "perfil", "seguidores", "direct com uma",
    "ajudar no crescimento", "agencia", "marketing digital", "impulsionar",
]

# Mensagem padrao
DEFAULT_MSG = """Oi {nome}! Tudo bem?

Vi que voce se interessou por harmonizacao facial aqui em Maringa!

Trabalho com clinicas referencia na cidade e temos condicoes especiais essa semana.

Quer que eu te mande mais informacoes? Sem compromisso!"""


def load_env():
    """Carrega variaveis do .env"""
    env = {}
    if ENV_PATH.exists():
        for line in ENV_PATH.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip()
    return env


def log(msg, level="INFO"):
    """Loga no console e no arquivo"""
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    entry = f"[{ts}] [{level}] {msg}"
    print(entry)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(entry + "\n")


def load_db(path):
    """Carrega banco JSON"""
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return []


def save_db(path, data):
    """Salva banco JSON"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


# ════════════════════════════════════════
# FASE 1: SCRAPING (Apify)
# ════════════════════════════════════════

def scrape_leads(apify_token, profiles=None, limit=30):
    """Busca leads no Instagram via Apify"""
    from apify_client import ApifyClient

    client = ApifyClient(apify_token)
    profiles = profiles or CLINIC_PROFILES

    log(f"Iniciando scraping de {len(profiles)} perfis...")
    log(f"Limite: {limit} posts por perfil")

    # Rodar Instagram Scraper
    run_input = {
        "directUrls": profiles,
        "resultsType": "posts",
        "resultsLimit": limit,
        "addParentData": True,
    }

    log("Chamando Apify instagram-scraper...")
    run = client.actor("apify/instagram-scraper").call(run_input=run_input)

    dataset_id = run["defaultDatasetId"]
    log(f"Scraping concluido! Dataset: {dataset_id}")

    # Baixar resultados
    items = list(client.dataset(dataset_id).iterate_items())
    log(f"Posts baixados: {len(items)}")

    # Extrair comentarios
    all_comments = []
    for post in items:
        owner = post.get("ownerUsername", "?")
        post_url = post.get("url", "")
        for c in post.get("latestComments", []):
            text = c.get("text", "")
            user = c.get("ownerUsername", "?")
            all_comments.append({
                "user": user,
                "text": text,
                "post_owner": owner,
                "post_url": post_url,
            })

    log(f"Comentarios extraidos: {len(all_comments)}")

    # Filtrar leads (interesse real)
    leads = []
    for c in all_comments:
        txt = c["text"].lower()

        # Verificar se e bot/spam
        is_bot = any(bk in txt for bk in BOT_KEYWORDS)
        if is_bot:
            continue

        # Verificar se demonstra interesse
        is_interested = any(kw in txt for kw in INTEREST_KEYWORDS)
        if is_interested:
            # Classificar
            if any(k in txt for k in ["quero", "agenda", "gostaria", "sonho"]):
                score = 90
            elif any(k in txt for k in ["valor", "preco", "quanto", "orcamento"]):
                score = 85
            else:
                score = 70

            leads.append({
                "id": f"L-{len(leads)+1:05d}",
                "user": c["user"],
                "text": c["text"],
                "post_owner": c["post_owner"],
                "post_url": c["post_url"],
                "score": score,
                "temp": "quente" if score >= 80 else "morno",
                "sent": False,
                "sent_at": None,
                "scraped_at": datetime.now().isoformat(),
            })

    log(f"Leads qualificados: {len(leads)} (de {len(all_comments)} comentarios)")

    # Deduplicar com banco existente
    existing = load_db(LEADS_DB)
    existing_users = {l["user"] for l in existing}
    new_leads = [l for l in leads if l["user"] not in existing_users]

    log(f"Leads NOVOS (nao duplicados): {len(new_leads)}")

    # Salvar
    all_leads = existing + new_leads
    save_db(LEADS_DB, all_leads)
    log(f"Total no banco: {len(all_leads)} leads")

    return new_leads


# ════════════════════════════════════════
# FASE 2: ENVIO DE DM (Instagram)
# ════════════════════════════════════════

def send_dms(ig_user, ig_pass, message_template=None, limit=10, delay=30):
    """Envia DMs para leads nao contactados"""
    from instagrapi import Client

    msg_template = message_template or DEFAULT_MSG

    log(f"Iniciando envio de DMs via @{ig_user}...")

    # Login no Instagram
    cl = Client()
    cl.delay_range = [2, 5]  # delay entre acoes (anti-ban)

    log("Fazendo login no Instagram...")
    cl.login(ig_user, ig_pass)
    log("Login OK!")

    # Carregar leads nao enviados
    leads = load_db(LEADS_DB)
    pending = [l for l in leads if not l.get("sent")]
    log(f"Leads pendentes de envio: {len(pending)}")

    sent_count = 0
    for lead in pending[:limit]:
        try:
            username = lead["user"]
            nome = username.split(".")[0].split("_")[0].title()
            msg = msg_template.replace("{nome}", nome)

            log(f"Enviando DM para @{username}...")

            # Buscar user_id
            user_id = cl.user_id_from_username(username)
            # Enviar DM
            cl.direct_send(msg, [user_id])

            lead["sent"] = True
            lead["sent_at"] = datetime.now().isoformat()
            sent_count += 1

            log(f"DM enviada para @{username}! ({sent_count}/{limit})")

            # Delay entre mensagens (anti-ban)
            if sent_count < limit:
                wait = delay + (hash(username) % 15)  # delay variavel
                log(f"Aguardando {wait}s antes do proximo envio...")
                time.sleep(wait)

        except Exception as e:
            log(f"ERRO ao enviar para @{lead['user']}: {e}", "ERROR")
            continue

    # Salvar estado atualizado
    save_db(LEADS_DB, leads)
    log(f"Envio concluido! {sent_count} DMs enviadas.")

    return sent_count


# ════════════════════════════════════════
# FASE 3: HEARTBEAT / LOOP
# ════════════════════════════════════════

def heartbeat(env, interval_min=60):
    """Roda o ciclo completo em loop"""
    apify_token = env.get("APIFY_TOKEN")
    ig_user = env.get("INSTAGRAM_USERNAME")
    ig_pass = env.get("INSTAGRAM_PASSWORD")

    if not apify_token:
        log("ERRO: APIFY_TOKEN nao configurado no .env", "ERROR")
        return

    cycle = 0
    while True:
        cycle += 1
        log(f"{'='*50}")
        log(f"HEARTBEAT #{cycle} — {datetime.now().strftime('%d/%m/%Y %H:%M')}")
        log(f"{'='*50}")

        # FASE 1: Scraping
        try:
            new_leads = scrape_leads(apify_token)
            log(f"Scraping OK — {len(new_leads)} novos leads")
        except Exception as e:
            log(f"ERRO no scraping: {e}", "ERROR")
            new_leads = []

        # FASE 2: Envio (so se tiver credenciais)
        if ig_user and ig_pass:
            try:
                sent = send_dms(ig_user, ig_pass, limit=5, delay=45)
                log(f"Envio OK — {sent} DMs enviadas")
            except Exception as e:
                log(f"ERRO no envio: {e}", "ERROR")
        else:
            log("Instagram nao configurado — pulando envio de DMs")
            log("Configure INSTAGRAM_USERNAME e INSTAGRAM_PASSWORD no .env")

        # Resumo
        all_leads = load_db(LEADS_DB)
        total = len(all_leads)
        sent_total = len([l for l in all_leads if l.get("sent")])
        pending = total - sent_total

        log(f"")
        log(f"RESUMO: {total} leads | {sent_total} enviados | {pending} pendentes")
        log(f"Proximo heartbeat em {interval_min} minutos...")
        log(f"{'='*50}")
        log(f"")

        time.sleep(interval_min * 60)


# ════════════════════════════════════════
# CLI
# ════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description="Lead Machine — Automacao de Leads")
    parser.add_argument("--scrape", action="store_true", help="Buscar novos leads no Instagram")
    parser.add_argument("--send", action="store_true", help="Enviar DMs para leads pendentes")
    parser.add_argument("--full", action="store_true", help="Scraping + Envio completo")
    parser.add_argument("--loop", type=int, metavar="MIN", help="Rodar em loop (heartbeat a cada N minutos)")
    parser.add_argument("--limit", type=int, default=20, help="Limite de posts por perfil (default: 20)")
    parser.add_argument("--dm-limit", type=int, default=10, help="Limite de DMs por ciclo (default: 10)")
    parser.add_argument("--status", action="store_true", help="Mostrar status do banco de leads")
    args = parser.parse_args()

    env = load_env()
    apify_token = env.get("APIFY_TOKEN")
    ig_user = env.get("INSTAGRAM_USERNAME")
    ig_pass = env.get("INSTAGRAM_PASSWORD")

    log("Lead Machine v1.0 — Automacao de Leads")
    log(f"Apify Token: {'OK' if apify_token else 'NAO CONFIGURADO'}")
    log(f"Instagram: {'@'+ig_user if ig_user else 'NAO CONFIGURADO'}")

    if args.status:
        leads = load_db(LEADS_DB)
        total = len(leads)
        sent = len([l for l in leads if l.get("sent")])
        quentes = len([l for l in leads if l.get("temp") == "quente"])
        log(f"Total: {total} | Quentes: {quentes} | Enviados: {sent} | Pendentes: {total-sent}")
        return

    if args.scrape or args.full:
        if not apify_token:
            log("ERRO: APIFY_TOKEN obrigatorio para scraping", "ERROR")
            sys.exit(1)
        scrape_leads(apify_token, limit=args.limit)

    if args.send or args.full:
        if not ig_user or not ig_pass:
            log("ERRO: INSTAGRAM_USERNAME e INSTAGRAM_PASSWORD obrigatorios para envio", "ERROR")
            sys.exit(1)
        send_dms(ig_user, ig_pass, limit=args.dm_limit)

    if args.loop:
        heartbeat(env, interval_min=args.loop)

    if not any([args.scrape, args.send, args.full, args.loop, args.status]):
        parser.print_help()


if __name__ == "__main__":
    main()
