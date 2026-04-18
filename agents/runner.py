#!/usr/bin/env python3
"""
LEAD MACHINE - Runner automatico

Fica rodando em loop. A cada TICK_SECONDS verifica searches.json:
- Pra cada busca ATIVA com next_run vencido:
  - Dispara agentes em paralelo (subprocess, 1 por plataforma)
  - Quando todos terminam: roda qualifier (que dispara Telegram)
  - Atualiza last_run/next_run

Uso:
  python agents/runner.py
  python agents/runner.py --tick 30         # checar a cada 30s
  python agents/runner.py --dry-run         # so mostra o que faria
  python agents/runner.py --once            # 1 iteracao e sai

Ctrl+C para parar.
"""

import argparse
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import searches
from base import setup_logger

# Mapa plataforma -> script
AGENT_SCRIPTS = {
    "google": "agent_google_maps.py",
    "instagram": "agent_instagram.py",
    "facebook": "agent_facebook.py",
    "tiktok": "agent_tiktok.py",
    "twitter": "agent_twitter.py",
}

AGENTS_DIR = Path(__file__).parent
BASE_DIR = AGENTS_DIR.parent
LOG_DIR = BASE_DIR / "leads-export"


def run_agent(script: str, search: dict, logger) -> dict:
    """Roda 1 agente como subprocess. Retorna {platform, ok, stdout, stderr}."""
    plat = script.replace("agent_", "").replace(".py", "").replace("google_maps", "google")
    script_path = AGENTS_DIR / script
    if not script_path.exists():
        return {"platform": plat, "ok": False, "error": f"script nao existe: {script}"}

    env = os.environ.copy()
    env["SEARCH_QUERY"] = search["query"]
    env["CITY"] = search.get("cidade", "")
    env["NICHO"] = search.get("nicho", "")

    logger.info(f"  → disparando {plat} (query='{search['query']}', cidade='{search.get('cidade','')}')")
    start = time.time()

    try:
        result = subprocess.run(
            [sys.executable, str(script_path)],
            env=env,
            cwd=str(BASE_DIR),
            capture_output=True,
            text=True,
            timeout=600,  # 10min por agente
            encoding="utf-8",
            errors="replace",
        )
        duration = round(time.time() - start, 1)
        ok = result.returncode == 0
        log_prefix = "OK" if ok else "FAIL"
        logger.info(f"  ← {plat} {log_prefix} em {duration}s (rc={result.returncode})")
        return {
            "platform": plat,
            "ok": ok,
            "returncode": result.returncode,
            "duration_sec": duration,
            "stdout_tail": (result.stdout or "")[-500:],
            "stderr_tail": (result.stderr or "")[-500:],
        }
    except subprocess.TimeoutExpired:
        logger.error(f"  ← {plat} TIMEOUT (>10min)")
        return {"platform": plat, "ok": False, "error": "timeout"}
    except Exception as e:
        logger.error(f"  ← {plat} EXCECAO: {e}")
        return {"platform": plat, "ok": False, "error": str(e)}


def run_qualifier(logger) -> dict:
    """Roda o qualifier (dispara Telegram pros leads quentes novos)."""
    script_path = AGENTS_DIR / "agent_qualifier.py"
    logger.info("  → qualificando leads novos...")
    try:
        result = subprocess.run(
            [sys.executable, str(script_path), "--requalify"],
            cwd=str(BASE_DIR),
            capture_output=True,
            text=True,
            timeout=300,
            encoding="utf-8",
            errors="replace",
        )
        logger.info(f"  ← qualifier rc={result.returncode}")
        return {"ok": result.returncode == 0,
                "stdout_tail": (result.stdout or "")[-500:]}
    except Exception as e:
        logger.error(f"  ← qualifier EXCECAO: {e}")
        return {"ok": False, "error": str(e)}


def execute_search(search: dict, logger, dry_run: bool = False) -> dict:
    """Executa uma busca: dispara todos os agentes em paralelo, depois qualifier."""
    search_id = search["id"]
    logger.info(f"")
    logger.info(f"========================================")
    logger.info(f"▶ EXECUTANDO {search_id}: {search['nome']}")
    logger.info(f"  query='{search['query']}' cidade='{search.get('cidade','')}'")
    logger.info(f"  plataformas={search['plataformas']}")
    logger.info(f"========================================")

    if dry_run:
        logger.info("  (dry-run - nao vai rodar de verdade)")
        return {"dry_run": True}

    searches.mark_started(search_id)

    # Dispara todos os agentes em paralelo
    import concurrent.futures
    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool:
        futures = {}
        for plat in search["plataformas"]:
            script = AGENT_SCRIPTS.get(plat)
            if not script:
                logger.warning(f"  plataforma desconhecida: {plat}")
                continue
            futures[pool.submit(run_agent, script, search, logger)] = plat
        for fut in concurrent.futures.as_completed(futures):
            results.append(fut.result())

    # Roda qualifier (inclui Telegram)
    qual = run_qualifier(logger)

    ok_count = sum(1 for r in results if r.get("ok"))
    fail_count = len(results) - ok_count
    stats = {
        "agentes_ok": ok_count,
        "agentes_fail": fail_count,
        "plataformas": [r["platform"] for r in results],
        "qualifier_ok": qual.get("ok", False),
    }

    status = "success" if ok_count > 0 else "failed"
    searches.mark_completed(search_id, status=status, stats=stats)

    logger.info(f"◀ {search_id} concluida ({ok_count} OK, {fail_count} falharam)")
    return {"search_id": search_id, "results": results, "qualifier": qual, "stats": stats}


def tick(logger, dry_run: bool = False) -> int:
    """Uma iteracao do loop. Retorna quantas buscas executou."""
    due = searches.due_searches()
    if not due:
        return 0
    logger.info(f"★ {len(due)} busca(s) vencida(s)")
    for s in due:
        execute_search(s, logger, dry_run=dry_run)
    return len(due)


def main():
    parser = argparse.ArgumentParser(description="Lead Machine - Runner automatico")
    parser.add_argument("--tick", type=int, default=60, help="Segundos entre checks (default 60)")
    parser.add_argument("--once", action="store_true", help="Roda 1 iteracao e sai")
    parser.add_argument("--dry-run", action="store_true", help="So mostra, nao executa")
    args = parser.parse_args()

    logger = setup_logger("runner")
    logger.info("========================================")
    logger.info("  LEAD MACHINE RUNNER iniciado")
    logger.info(f"  tick={args.tick}s  once={args.once}  dry_run={args.dry_run}")
    logger.info("  Ctrl+C para parar")
    logger.info("========================================")

    iteration = 0
    try:
        while True:
            iteration += 1
            executed = tick(logger, dry_run=args.dry_run)
            if executed == 0:
                logger.info(f"[{datetime.now().strftime('%H:%M:%S')}] tick {iteration}: nenhuma busca vencida")
            if args.once:
                break
            time.sleep(args.tick)
    except KeyboardInterrupt:
        logger.info("")
        logger.info("Runner parado pelo usuario.")
        sys.exit(0)


if __name__ == "__main__":
    main()
