"""
LEAD MACHINE - Buscas Salvas (Schedule)

Modulo que gerencia o searches.json - lista de buscas que o runner
automatico vai disparar de tempos em tempos.

Schema de uma busca:
{
  "id": "S-0001",
  "nome": "Dentistas Maringa",
  "query": "dentista implante dentario",
  "cidade": "Maringa-PR",
  "nicho": "odontologia",
  "plataformas": ["google", "instagram", "tiktok"],
  "intervalo_horas": 6,
  "ativa": true,
  "last_run": "2026-04-18T12:00:00",
  "next_run": "2026-04-18T18:00:00",
  "created_at": "2026-04-18T10:00:00",
  "last_status": "success",
  "last_stats": {"leads_novos": 12, "quentes": 3}
}
"""

import json
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional

import portalocker

BASE_DIR = Path(__file__).parent.parent
SEARCHES_PATH = BASE_DIR / "leads-export" / "searches.json"

# Plataformas validas (correspondem aos agent_*.py)
VALID_PLATFORMS = {"google", "instagram", "facebook", "tiktok", "twitter"}


def _now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def load() -> List[dict]:
    """Carrega buscas. Retorna [] se nao existe."""
    if not SEARCHES_PATH.exists():
        return []
    try:
        data = json.loads(SEARCHES_PATH.read_text(encoding="utf-8"))
        if not isinstance(data, list):
            return []
        return data
    except (json.JSONDecodeError, IOError):
        return []


def save(searches: List[dict]) -> None:
    """Salva com file locking (seguro para concorrencia runner+dashboard)."""
    SEARCHES_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp = SEARCHES_PATH.with_suffix(".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        portalocker.lock(f, portalocker.LOCK_EX)
        try:
            json.dump(searches, f, ensure_ascii=False, indent=2)
        finally:
            portalocker.unlock(f)
    if SEARCHES_PATH.exists():
        SEARCHES_PATH.unlink()
    tmp.rename(SEARCHES_PATH)


def _next_id(searches: List[dict]) -> str:
    max_n = 0
    for s in searches:
        m = re.match(r"S-(\d+)", s.get("id", ""))
        if m:
            max_n = max(max_n, int(m.group(1)))
    return f"S-{max_n + 1:04d}"


def validate(payload: dict) -> tuple:
    """Valida payload de nova busca. Retorna (ok, erros)."""
    errors = []
    if not payload.get("nome", "").strip():
        errors.append("nome obrigatorio")
    if not payload.get("query", "").strip():
        errors.append("query obrigatoria")
    platforms = payload.get("plataformas") or []
    if not platforms:
        errors.append("escolha pelo menos 1 plataforma")
    else:
        invalid = [p for p in platforms if p not in VALID_PLATFORMS]
        if invalid:
            errors.append(f"plataformas invalidas: {invalid}")
    try:
        intervalo = int(payload.get("intervalo_horas", 6))
        if intervalo < 1 or intervalo > 168:
            errors.append("intervalo_horas deve estar entre 1 e 168 (7 dias)")
    except (TypeError, ValueError):
        errors.append("intervalo_horas deve ser numero")
    return (len(errors) == 0, errors)


def add(payload: dict) -> dict:
    """Cria nova busca. Retorna o objeto criado."""
    ok, errors = validate(payload)
    if not ok:
        raise ValueError("; ".join(errors))

    searches = load()
    intervalo = int(payload.get("intervalo_horas", 6))
    now = datetime.now()

    search = {
        "id": _next_id(searches),
        "nome": payload["nome"].strip(),
        "query": payload["query"].strip(),
        "cidade": (payload.get("cidade") or "").strip(),
        "nicho": (payload.get("nicho") or "").strip(),
        "plataformas": list(payload["plataformas"]),
        "intervalo_horas": intervalo,
        "ativa": bool(payload.get("ativa", True)),
        "last_run": None,
        "next_run": now.isoformat(timespec="seconds"),  # roda na proxima iteracao
        "created_at": _now_iso(),
        "last_status": None,
        "last_stats": None,
    }
    searches.append(search)
    save(searches)
    return search


def update(search_id: str, patch: dict) -> Optional[dict]:
    """Atualiza busca existente. Retorna objeto atualizado ou None se nao achar."""
    searches = load()
    for s in searches:
        if s.get("id") == search_id:
            # Campos permitidos pra update via UI
            allowed = {"nome", "query", "cidade", "nicho", "plataformas",
                       "intervalo_horas", "ativa"}
            for k in allowed:
                if k in patch:
                    s[k] = patch[k]
            # Recalcula next_run se intervalo mudou ou ativa foi ligada
            if "intervalo_horas" in patch or patch.get("ativa") is True:
                s["next_run"] = _compute_next_run(s).isoformat(timespec="seconds")
            save(searches)
            return s
    return None


def delete(search_id: str) -> bool:
    """Remove busca. True se deletou."""
    searches = load()
    remaining = [s for s in searches if s.get("id") != search_id]
    if len(remaining) == len(searches):
        return False
    save(remaining)
    return True


def get(search_id: str) -> Optional[dict]:
    for s in load():
        if s.get("id") == search_id:
            return s
    return None


def _compute_next_run(search: dict, from_time: datetime = None) -> datetime:
    """Calcula proximo run baseado em last_run + intervalo_horas."""
    base = from_time or datetime.now()
    return base + timedelta(hours=int(search.get("intervalo_horas", 6)))


def due_searches(now: datetime = None) -> List[dict]:
    """Lista buscas ATIVAS cujo next_run ja venceu."""
    if now is None:
        now = datetime.now()
    due = []
    for s in load():
        if not s.get("ativa"):
            continue
        next_run = s.get("next_run")
        if not next_run:
            due.append(s)
            continue
        try:
            nr = datetime.fromisoformat(next_run)
            if nr <= now:
                due.append(s)
        except (ValueError, TypeError):
            due.append(s)
    return due


def mark_started(search_id: str) -> None:
    """Registra que busca comecou (so atualiza last_run)."""
    searches = load()
    for s in searches:
        if s.get("id") == search_id:
            s["last_run"] = _now_iso()
            save(searches)
            return


def mark_completed(search_id: str, status: str = "success",
                   stats: dict = None) -> None:
    """Registra que busca terminou, recalcula next_run."""
    searches = load()
    for s in searches:
        if s.get("id") == search_id:
            s["last_run"] = _now_iso()
            s["last_status"] = status
            s["last_stats"] = stats or {}
            s["next_run"] = _compute_next_run(s).isoformat(timespec="seconds")
            save(searches)
            return


def trigger_now(search_id: str) -> Optional[dict]:
    """Forca a busca a rodar na proxima iteracao do runner (seta next_run = agora)."""
    searches = load()
    for s in searches:
        if s.get("id") == search_id:
            s["next_run"] = _now_iso()
            s["ativa"] = True
            save(searches)
            return s
    return None
