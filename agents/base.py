"""
LEAD MACHINE — Modulo Base Compartilhado
Usado por todos os agent scripts para: env, logging, DB, scoring, formato unificado.
"""

import argparse
import json
import logging
import os
import re
import sys
import time
from datetime import datetime
from pathlib import Path

import portalocker

# ── Paths ──
BASE_DIR = Path(__file__).parent.parent
ENV_PATH = BASE_DIR / ".env"
LEADS_DIR = BASE_DIR / "leads-export"
LEADS_DB_PATH = LEADS_DIR / "leads-db.json"
LOGS_DIR = LEADS_DIR

# ── Keywords ──
INTEREST_KEYWORDS = [
    "quero", "quanto custa", "preco", "valor", "agenda", "agendar",
    "queria", "sonho", "gostaria", "interessada", "interessado",
    "onde fica", "como faco", "parcela", "convenio", "orcamento",
    "aceita", "qual o", "quanto", "informacao", "contato",
    "whatsapp", "telefone", "atende", "indicacao", "recomenda",
    "alguem conhece", "alguem sabe", "me indica",
]

BOT_KEYWORDS = [
    "solucao", "crescimento", "perfil", "seguidores", "direct com uma",
    "ajudar no crescimento", "agencia", "marketing digital", "impulsionar",
    "link na bio", "mande uma mensagem", "confira", "sigam", "siga",
    "ganhe dinheiro", "renda extra", "trabalhe de casa", "oportunidade",
]


# ════════════════════════════════════════
# CONFIGURACAO
# ════════════════════════════════════════

def load_env() -> dict:
    """Carrega variaveis do .env e merge com os.environ (os.environ tem prioridade)."""
    env = {}
    if ENV_PATH.exists():
        for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip()
    # OS env vars (set by Paperclip) override .env file
    for k, v in os.environ.items():
        env[k] = v
    return env


def resolve_param(args, arg_name: str, env_name: str, default=None):
    """Resolve parametro: CLI arg > env var > default."""
    cli_val = getattr(args, arg_name, None) if args else None
    if cli_val is not None:
        return cli_val
    env_val = os.environ.get(env_name)
    if env_val:
        return env_val
    return default


def build_arg_parser(agent_name: str, description: str) -> argparse.ArgumentParser:
    """Parser CLI padrao com argumentos compartilhados."""
    parser = argparse.ArgumentParser(
        prog=f"agent_{agent_name}",
        description=f"Lead Machine — {description}",
    )
    parser.add_argument("--query", "-q", help="Busca (ou env SEARCH_QUERY)")
    parser.add_argument("--city", "-c", help="Cidade (ou env CITY)")
    parser.add_argument("--nicho", "-n", help="Nicho (ou env NICHO)")
    parser.add_argument("--limit", "-l", type=int, help="Limite de leads (ou env LIMIT)")
    parser.add_argument("--profiles", help="Perfis separados por virgula (ou env PROFILES)")
    parser.add_argument("--dry-run", action="store_true", help="Nao salvar no DB")
    parser.add_argument("--verbose", "-v", action="store_true", help="Debug logging")
    return parser


# ════════════════════════════════════════
# LOGGING
# ════════════════════════════════════════

def setup_logger(agent_name: str, verbose: bool = False) -> logging.Logger:
    """Logger que escreve em stderr (Paperclip captura) + arquivo .log."""
    logger = logging.getLogger(f"leadmachine.{agent_name}")
    logger.setLevel(logging.DEBUG if verbose else logging.INFO)

    if logger.handlers:
        return logger

    fmt = logging.Formatter(
        f"[%(asctime)s] [%(levelname)s] [{agent_name}] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # stderr handler (Paperclip captura stderr separado)
    stderr_h = logging.StreamHandler(sys.stderr)
    stderr_h.setLevel(logging.DEBUG if verbose else logging.INFO)
    stderr_h.setFormatter(fmt)
    logger.addHandler(stderr_h)

    # File handler
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    log_path = LOGS_DIR / f"{agent_name}.log"
    file_h = logging.FileHandler(log_path, encoding="utf-8")
    file_h.setLevel(logging.DEBUG)
    file_h.setFormatter(fmt)
    logger.addHandler(file_h)

    return logger


# ════════════════════════════════════════
# LEADS DATABASE
# ════════════════════════════════════════

def load_leads() -> list:
    """Carrega leads do JSON DB. Migra formato antigo automaticamente."""
    if not LEADS_DB_PATH.exists():
        return []
    try:
        data = json.loads(LEADS_DB_PATH.read_text(encoding="utf-8"))
        if not isinstance(data, list):
            return []
        return [migrate_lead(l) for l in data]
    except (json.JSONDecodeError, IOError):
        return []


def save_leads(leads: list, logger=None) -> None:
    """Salva leads no JSON DB com file locking (seguro para execucao paralela)."""
    LEADS_DIR.mkdir(parents=True, exist_ok=True)
    tmp_path = LEADS_DB_PATH.with_suffix(".tmp")

    try:
        with open(tmp_path, "w", encoding="utf-8") as f:
            portalocker.lock(f, portalocker.LOCK_EX)
            try:
                json.dump(leads, f, ensure_ascii=False, indent=2)
            finally:
                portalocker.unlock(f)
        # Atomic replace
        if LEADS_DB_PATH.exists():
            LEADS_DB_PATH.unlink()
        tmp_path.rename(LEADS_DB_PATH)
    except Exception as e:
        if logger:
            logger.error(f"Erro ao salvar leads: {e}")
        # Fallback: write directly
        LEADS_DB_PATH.write_text(
            json.dumps(leads, ensure_ascii=False, indent=2), encoding="utf-8"
        )


def get_next_id(leads: list) -> str:
    """Retorna proximo ID unico (ex: L-00022). Escaneia TODOS os IDs existentes."""
    max_num = 0
    for lead in leads:
        lid = lead.get("id", "")
        match = re.match(r"L-(\d+)", lid)
        if match:
            num = int(match.group(1))
            if num > max_num:
                max_num = num
    return f"L-{max_num + 1:05d}"


def deduplicate_key(lead: dict) -> str:
    """Gera chave de deduplicacao: plataforma:user:url."""
    plat = (lead.get("plataforma") or "unknown").lower().strip()
    user = (lead.get("user") or lead.get("perfil") or "").lower().strip().lstrip("@")
    url = (lead.get("url") or lead.get("post_url") or "").strip()
    return f"{plat}:{user}:{url}"


def merge_leads(existing: list, new_leads: list, logger=None) -> tuple:
    """
    Merge new_leads em existing com deduplicacao.
    Retorna (lista_mergeada, contagem_novos).
    """
    existing_keys = {deduplicate_key(l) for l in existing}
    actually_new = []

    for lead in new_leads:
        key = deduplicate_key(lead)
        if key not in existing_keys:
            existing_keys.add(key)
            actually_new.append(lead)

    # Assign IDs to new leads
    all_leads = list(existing)
    for lead in actually_new:
        lead["id"] = get_next_id(all_leads)
        all_leads.append(lead)

    if logger:
        logger.info(f"Merge: {len(actually_new)} novos de {len(new_leads)} encontrados")

    return all_leads, len(actually_new)


def migrate_lead(lead: dict) -> dict:
    """Converte lead formato antigo para formato unificado (preenche campos faltantes)."""
    now_short = datetime.now().strftime("%d/%m")

    # Auto-detect tipo baseado na plataforma
    plat = lead.get("plataforma", "instagram")
    auto_tipo = "empresa" if plat == "google" else "pessoa"

    # Preencher campos que faltam sem sobrescrever existentes
    defaults = {
        "tipo": auto_tipo,
        "nome": username_to_name(lead.get("user", "")),
        "user": lead.get("user", ""),
        "plataforma": "instagram",
        "perfil": f"@{lead.get('user', '')}" if lead.get("user") else "",
        "evidencia": build_evidencia(lead.get("text", "")),
        "texto_original": lead.get("text", ""),
        "url": lead.get("post_url", ""),
        "post_owner": lead.get("post_owner", ""),
        "cidade": "",
        "nicho": "",
        "score": lead.get("score", 0),
        "temp": lead.get("temp", ""),
        "qualified": False,
        "etapa": "descoberto",
        "email": None,
        "telefone": None,
        "coletado": now_short,
        "scraped_at": lead.get("scraped_at", datetime.now().isoformat()),
        "sent": lead.get("sent", False),
        "sent_at": lead.get("sent_at"),
        "dmEnviada": None,
        "clienteDestino": None,
    }

    # Se ja tem sent=True, marcar etapa como contactado
    if lead.get("sent"):
        defaults["etapa"] = "contactado"
        if lead.get("sent_at"):
            try:
                dt = datetime.fromisoformat(lead["sent_at"])
                defaults["dmEnviada"] = dt.strftime("%d/%m %H:%M")
            except (ValueError, TypeError):
                pass

    for k, v in defaults.items():
        if k not in lead or lead[k] is None:
            lead[k] = v

    return lead


# ════════════════════════════════════════
# CRIACAO DE LEADS
# ════════════════════════════════════════

def create_lead(
    plataforma: str,
    user: str,
    texto: str,
    url: str,
    cidade: str = "",
    nicho: str = "",
    post_owner: str = "",
    nome: str = "",
    score: int = 0,
    temp: str = "",
    email=None,
    telefone=None,
    tipo: str = "",
    extra: dict = None,
) -> dict:
    """Factory para criar lead no formato unificado. ID e atribuido no merge."""
    if not nome:
        nome = username_to_name(user)

    if not temp and score > 0:
        temp = classify_temp(score)

    # Tipo: pessoa ou empresa (auto-detect se nao fornecido)
    if not tipo:
        if plataforma == "google":
            tipo = "empresa"
        else:
            tipo = "pessoa"

    # Prefixo de perfil depende da plataforma
    if plataforma in ("instagram", "x", "tiktok", "twitter"):
        perfil = f"@{user}" if not user.startswith("@") else user
    else:
        perfil = user

    now = datetime.now()

    lead = {
        "id": "",  # Atribuido no merge
        "tipo": tipo,
        "nome": nome,
        "user": user.lstrip("@"),
        "plataforma": plataforma,
        "perfil": perfil,
        "evidencia": build_evidencia(texto, nicho),
        "texto_original": texto,
        "url": url,
        "post_owner": post_owner,
        "cidade": cidade,
        "nicho": nicho,
        "score": score,
        "temp": temp,
        "qualified": False,
        "etapa": "descoberto",
        "email": email,
        "telefone": telefone,
        "coletado": now.strftime("%d/%m"),
        "scraped_at": now.isoformat(),
        "sent": False,
        "sent_at": None,
        "dmEnviada": None,
        "clienteDestino": None,
    }

    if extra:
        lead.update(extra)

    return lead


# ════════════════════════════════════════
# SCORING & CLASSIFICACAO
# ════════════════════════════════════════

def is_bot(text: str) -> bool:
    """Verifica se texto e bot/spam."""
    txt = text.lower()
    return any(bk in txt for bk in BOT_KEYWORDS)


def calculate_score(text: str, city_match: bool = False) -> int:
    """
    Score 0-100 baseado em multiplos fatores.
    - Intencao direta (quero, agendar): 85-95
    - Consulta de preco (valor, quanto): 75-85
    - Interesse indireto (sonho, gostaria): 60-75
    - Match de cidade: +5
    - Multiplos keywords: +5
    """
    txt = text.lower()
    score = 0
    matches = 0

    # Intencao direta
    direct = ["quero", "agenda", "agendar", "gostaria", "me indica", "indicacao"]
    if any(k in txt for k in direct):
        score = 88
        matches += 1

    # Consulta de preco — perguntou valor = quente
    price = ["valor", "preco", "quanto custa", "quanto", "orcamento", "parcela"]
    if any(k in txt for k in price):
        score = max(score, 88)
        matches += 1

    # Interesse indireto
    indirect = ["sonho", "queria", "interessada", "interessado", "recomenda",
                "alguem conhece", "alguem sabe"]
    if any(k in txt for k in indirect):
        score = max(score, 65)
        matches += 1

    # Interesse fraco (qualquer keyword de interesse)
    if score == 0 and any(kw in txt for kw in INTEREST_KEYWORDS):
        score = 55

    # Bonus: multiplos keywords
    if matches >= 2:
        score = min(score + 5, 100)

    # Bonus: match de cidade
    if city_match:
        score = min(score + 5, 100)

    # Penalidade: texto muito curto (< 10 chars) = baixo esforco
    if len(txt.strip()) < 10 and score > 0:
        score = max(score - 10, 40)

    return score


def classify_temp(score: int) -> str:
    """Classifica temperatura: quente >= 80, morno >= 50, frio < 50."""
    if score >= 80:
        return "quente"
    elif score >= 50:
        return "morno"
    else:
        return "frio"


# ════════════════════════════════════════
# UTILIDADES
# ════════════════════════════════════════

def username_to_name(username: str) -> str:
    """
    'roberta_andreia_silva' -> 'Roberta Andreia Silva'
    'dr.viniciuslonghini' -> 'Dr Viniciuslonghini'
    """
    if not username:
        return ""
    name = username.lstrip("@")
    # Separar por _ e .
    parts = re.split(r"[_.]", name)
    # Remover numeros puros
    parts = [p for p in parts if p and not p.isdigit()]
    return " ".join(p.title() for p in parts)


def build_evidencia(texto: str, context: str = "") -> str:
    """Constroi string de evidencia legivel. Trunca em 120 chars."""
    if not texto:
        return ""
    # Limpar quebras de linha
    clean = " ".join(texto.split())
    if len(clean) > 80:
        clean = clean[:77] + "..."
    evidencia = f'"{clean}"'
    if context:
        evidencia += f" — interesse em {context}"
    return evidencia


def short_date() -> str:
    """Retorna 'DD/MM' para hoje."""
    return datetime.now().strftime("%d/%m")


# ════════════════════════════════════════
# SAIDA (stdout para Paperclip)
# ════════════════════════════════════════

def output_result(summary: dict) -> None:
    """
    Imprime JSON de resultado no stdout para Paperclip capturar.
    Chamado UMA VEZ no final de cada execucao de agente.
    """
    print(json.dumps(summary, ensure_ascii=False, indent=2))


def make_result(
    agent: str,
    status: str = "success",
    leads_found: int = 0,
    leads_new: int = 0,
    leads_total: int = 0,
    query: str = "",
    city: str = "",
    errors: list = None,
    extra: dict = None,
) -> dict:
    """Constroi dict de resultado padrao."""
    result = {
        "agent": agent,
        "status": status,
        "leads_found": leads_found,
        "leads_new": leads_new,
        "leads_total": leads_total,
        "query": query,
        "city": city,
        "timestamp": datetime.now().isoformat(),
        "errors": errors or [],
    }
    if extra:
        result.update(extra)
    return result
