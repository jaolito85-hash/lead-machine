"""
LEAD MACHINE - Campanhas (Workspaces)

Uma Campanha é o guarda-chuva que organiza leads por nicho/cidade/cliente.
Todo lead coletado pertence a exatamente uma campanha (pode ser "Legado"
caso não tenha sido atribuído). O Kanban filtra por campanha ativa.

Schema:
{
  "id": "C-0001",
  "nome": "Harmonização Facial — Maringa-PR",
  "nicho": "harmonizacao facial",
  "cidade": "Maringa-PR",
  "cliente_destino": "Dra. Camila Guerreiro",
  "query": "harmonizacao facial",
  "plataformas": ["instagram", "tiktok"],
  "status": "ativa",        # ativa | arquivada
  "created_at": "2026-04-22T16:00:00",
  "updated_at": "2026-04-22T16:00:00",
  "notes": ""
}
"""

import json
import re
from datetime import datetime
from pathlib import Path
from typing import List, Optional

import portalocker

BASE_DIR = Path(__file__).parent.parent
CAMPAIGNS_PATH = BASE_DIR / "leads-export" / "campaigns.json"

VALID_PLATFORMS = {"google", "instagram", "facebook", "tiktok", "twitter", "x", "youtube"}
VALID_STATUS = {"ativa", "arquivada"}

LEGACY_CAMPAIGN_ID = "C-LEGACY"  # id fixo reservado pra campanha "Legado"


def _now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def load() -> List[dict]:
    if not CAMPAIGNS_PATH.exists():
        return []
    try:
        data = json.loads(CAMPAIGNS_PATH.read_text(encoding="utf-8"))
        if not isinstance(data, list):
            return []
        return data
    except (json.JSONDecodeError, IOError):
        return []


def save(campaigns: List[dict]) -> None:
    CAMPAIGNS_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp = CAMPAIGNS_PATH.with_suffix(".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        portalocker.lock(f, portalocker.LOCK_EX)
        try:
            json.dump(campaigns, f, ensure_ascii=False, indent=2)
        finally:
            portalocker.unlock(f)
    if CAMPAIGNS_PATH.exists():
        CAMPAIGNS_PATH.unlink()
    tmp.rename(CAMPAIGNS_PATH)


def _next_id(campaigns: List[dict]) -> str:
    max_n = 0
    for c in campaigns:
        m = re.match(r"C-(\d+)", c.get("id", ""))
        if m:
            max_n = max(max_n, int(m.group(1)))
    return f"C-{max_n + 1:04d}"


def validate(payload: dict) -> tuple:
    errors = []
    if not payload.get("nome", "").strip():
        errors.append("nome obrigatorio")
    status = payload.get("status", "ativa")
    if status not in VALID_STATUS:
        errors.append(f"status invalido: {status}")
    platforms = payload.get("plataformas") or []
    invalid = [p for p in platforms if p not in VALID_PLATFORMS]
    if invalid:
        errors.append(f"plataformas invalidas: {invalid}")
    return (len(errors) == 0, errors)


def add(payload: dict) -> dict:
    ok, errors = validate(payload)
    if not ok:
        raise ValueError("; ".join(errors))
    campaigns = load()
    now = _now_iso()
    nacional = bool(payload.get("nacional", False))
    campaign = {
        "id": _next_id(campaigns),
        "nome": payload["nome"].strip(),
        "nicho": (payload.get("nicho") or "").strip(),
        # Se nacional, ignora qualquer cidade enviada (evita ambiguidade)
        "cidade": "" if nacional else (payload.get("cidade") or "").strip(),
        "cliente_destino": (payload.get("cliente_destino") or "").strip(),
        "query": (payload.get("query") or "").strip(),
        "plataformas": list(payload.get("plataformas") or []),
        "nacional": nacional,
        "status": payload.get("status", "ativa"),
        "notes": (payload.get("notes") or "").strip(),
        "created_at": now,
        "updated_at": now,
    }
    campaigns.append(campaign)
    save(campaigns)
    return campaign


def update(campaign_id: str, patch: dict) -> Optional[dict]:
    campaigns = load()
    for c in campaigns:
        if c.get("id") == campaign_id:
            allowed = {"nome", "nicho", "cidade", "cliente_destino",
                       "query", "plataformas", "nacional", "status", "notes",
                       "last_exported_at", "last_exported_count", "last_exported_format"}
            for k in allowed:
                if k in patch:
                    c[k] = patch[k]
            # Sanitize: campanha nacional = sem cidade
            if c.get("nacional"):
                c["cidade"] = ""
            c["updated_at"] = _now_iso()
            save(campaigns)
            return c
    return None


def delete(campaign_id: str) -> bool:
    """Deletar e destrutivo. Use archive() em vez disso pra manter historico."""
    if campaign_id == LEGACY_CAMPAIGN_ID:
        return False  # protege Legado
    campaigns = load()
    remaining = [c for c in campaigns if c.get("id") != campaign_id]
    if len(remaining) == len(campaigns):
        return False
    save(remaining)
    return True


def archive(campaign_id: str) -> Optional[dict]:
    """Arquiva (soft delete) — campanha some do seletor mas leads ficam."""
    return update(campaign_id, {"status": "arquivada"})


def get(campaign_id: str) -> Optional[dict]:
    for c in load():
        if c.get("id") == campaign_id:
            return c
    return None


def ensure_legacy() -> dict:
    """Garante que a campanha 'Legado' existe. Idempotente."""
    campaigns = load()
    for c in campaigns:
        if c.get("id") == LEGACY_CAMPAIGN_ID:
            return c
    now = _now_iso()
    legacy = {
        "id": LEGACY_CAMPAIGN_ID,
        "nome": "Legado — Imports anteriores",
        "nicho": "",
        "cidade": "",
        "cliente_destino": "",
        "query": "",
        "plataformas": [],
        "nacional": True,
        "status": "ativa",
        "notes": "Campanha criada automaticamente pra acomodar leads coletados antes do sistema de Campanhas.",
        "created_at": now,
        "updated_at": now,
    }
    campaigns.insert(0, legacy)
    save(campaigns)
    return legacy
