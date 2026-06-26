#!/usr/bin/env python3
"""
LEAD MACHINE — Server local
Serve o dashboard + leads-db.json + buscas salvas + endpoint on-demand /api/run.

Uso:
  python serve.py
  → Dashboard:     http://localhost:8081
  → Leads API:     http://localhost:8081/leads.json
  → Buscas API:    http://localhost:8081/api/local/searches
  → Run on-demand: http://localhost:8081/api/run  (POST) / /api/run/:id (GET)

O runner.py (agents/runner.py) continua funcionando separadamente via
supervisord — ele roda as buscas salvas em loop. O /api/run é um disparo
on-demand que roda os mesmos agentes (subprocess) sem passar pelo Paperclip.
"""

import json
import os
import sys
import uuid
import threading
import subprocess
import concurrent.futures
import time
from datetime import datetime
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from urllib.parse import quote, parse_qs, urlparse

# Permite importar modulos de agents/
sys.path.insert(0, str(Path(__file__).parent / "agents"))
import searches as searches_module
import campaigns as campaigns_module
import exports as exports_module


def env_int(name, default):
    try:
        return int(os.getenv(name, str(default)))
    except ValueError:
        return default


PORT = env_int("DASHBOARD_PORT", 8081)
BASE_DIR = Path(__file__).parent
LEADS_DB = BASE_DIR / "leads-export" / "leads-db.json"
AGENTS_DIR = BASE_DIR / "agents"

# Mapa plataforma -> script (mesmo usado pelo runner.py)
AGENT_SCRIPTS = {
    "google": "agent_google_maps.py",
    "instagram": "agent_instagram.py",
    "tiktok": "agent_tiktok.py",
    "youtube": "agent_youtube.py",
}

# Store em memoria dos runs on-demand: {run_id: {...}}
_RUNS = {}
_RUNS_LOCK = threading.Lock()


# ── Execução on-demand (mirror do runner.execute_search, sem searches.json) ──

def _run_agent_subprocess(script_name, query, cidade, nicho, campaign_id, log_lines):
    """Roda 1 agente como subprocess. Retorna dict com resultado."""
    plat = script_name.replace("agent_", "").replace(".py", "").replace("google_maps", "google")
    script_path = AGENTS_DIR / script_name
    if not script_path.exists():
        return {"platform": plat, "ok": False, "error": f"script nao existe: {script_name}"}

    env = os.environ.copy()
    env["SEARCH_QUERY"] = query
    env["CITY"] = cidade or ""
    env["NICHO"] = nicho or ""
    if campaign_id:
        env["CAMPAIGN_ID"] = campaign_id

    log_lines.append(f"[{_now()}] → disparando {plat} (query='{query}', cidade='{cidade}')")
    start = time.time()
    try:
        result = subprocess.run(
            [sys.executable, str(script_path)],
            env=env,
            cwd=str(BASE_DIR),
            capture_output=True,
            text=True,
            timeout=900,  # 15min por agente
            encoding="utf-8",
            errors="replace",
        )
        duration = round(time.time() - start, 1)
        ok = result.returncode == 0
        log_lines.append(f"[{_now()}] ← {plat} {'OK' if ok else 'FAIL'} em {duration}s (rc={result.returncode})")
        return {
            "platform": plat,
            "ok": ok,
            "returncode": result.returncode,
            "duration_sec": duration,
            "stdout_tail": (result.stdout or "")[-500:],
            "stderr_tail": (result.stderr or "")[-500:],
        }
    except subprocess.TimeoutExpired:
        log_lines.append(f"[{_now()}] ← {plat} TIMEOUT (>15min)")
        return {"platform": plat, "ok": False, "error": "timeout"}
    except Exception as e:
        log_lines.append(f"[{_now()}] ← {plat} EXCECAO: {e}")
        return {"platform": plat, "ok": False, "error": str(e)}


def _run_subprocess_simple(script_name, args, log_lines, timeout=600):
    """Roda um subprocess simples (qualifier/enricher). Retorna {ok, returncode, stdout_tail}."""
    script_path = AGENTS_DIR / script_name
    if not script_path.exists():
        return {"ok": False, "error": f"script nao existe: {script_name}"}
    try:
        result = subprocess.run(
            [sys.executable, str(script_path)] + args,
            cwd=str(BASE_DIR),
            capture_output=True,
            text=True,
            timeout=timeout,
            encoding="utf-8",
            errors="replace",
        )
        ok = result.returncode == 0
        log_lines.append(f"[{_now()}] ← {script_name} {'OK' if ok else 'FAIL'} (rc={result.returncode})")
        return {
            "ok": ok,
            "returncode": result.returncode,
            "stdout_tail": (result.stdout or "")[-500:],
        }
    except Exception as e:
        log_lines.append(f"[{_now()}] ← {script_name} EXCECAO: {e}")
        return {"ok": False, "error": str(e)}


def _execute_run(run_id, payload):
    """Executa o run em background: agentes em paralelo → qualifier → enricher."""
    log_lines = []
    query = payload.get("query") or payload.get("nicho") or ""
    cidade = payload.get("cidade") or ""
    nicho = payload.get("nicho") or query
    campaign_id = payload.get("campaign_id") or "C-LEGACY"
    plataformas = payload.get("plataformas") or []

    log_lines.append(f"[{_now()}] ▶ RUN {run_id} iniciado")
    log_lines.append(f"[{_now()}]   query='{query}' cidade='{cidade}' nicho='{nicho}' plataformas={plataformas} campaign_id={campaign_id}")

    # 1) Agentes em paralelo (ThreadPoolExecutor)
    results = []
    valid_plats = [p for p in plataformas if p in AGENT_SCRIPTS]
    if valid_plats:
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool:
            futures = {}
            for plat in valid_plats:
                script = AGENT_SCRIPTS[plat]
                futures[pool.submit(
                    _run_agent_subprocess, script, query, cidade, nicho, campaign_id, log_lines
                )] = plat
            for fut in concurrent.futures.as_completed(futures):
                results.append(fut.result())
    else:
        log_lines.append(f"[{_now()}] ⚠ nenhuma plataforma valida informada: {plataformas}")

    ok_count = sum(1 for r in results if r.get("ok"))
    fail_count = len(results) - ok_count

    # 2) Qualifier
    log_lines.append(f"[{_now()}] → qualificando leads novos...")
    qual = _run_subprocess_simple("agent_qualifier.py", ["--requalify"], log_lines, timeout=600)

    # 3) Enricher
    log_lines.append(f"[{_now()}] → enriquecendo leads (top)...")
    enrich = _run_subprocess_simple("agent_enricher.py", ["--limit", "20"], log_lines, timeout=900)

    stats = {
        "agentes_ok": ok_count,
        "agentes_fail": fail_count,
        "plataformas": [r.get("platform") for r in results],
        "qualifier_ok": qual.get("ok", False),
        "enricher_ok": enrich.get("ok", False),
        "total_leads_antes": _count_leads(),
        "total_leads_depois": _count_leads(),
    }
    status = "succeeded" if ok_count > 0 else "failed"
    log_lines.append(f"[{_now()}] ◀ RUN {run_id} concluido ({status})")

    with _RUNS_LOCK:
        _RUNS[run_id].update({
            "status": status,
            "stats": stats,
            "finished_at": _now(),
            "log": log_lines,
        })


def _count_leads():
    try:
        if LEADS_DB.exists():
            data = json.loads(LEADS_DB.read_text(encoding="utf-8"))
            return len(data) if isinstance(data, list) else 0
    except Exception:
        pass
    return 0


def _now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


class LeadMachineHandler(SimpleHTTPRequestHandler):
    """Handler que serve dashboard + leads + buscas + endpoint on-demand /api/run."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(BASE_DIR), **kwargs)

    def end_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PATCH, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Cache-Control", "no-cache")
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.end_headers()

    def do_GET(self):
        path = self.path.split("?")[0]
        if path == "/leads.json":
            return self.serve_leads()
        if path == "/api/local/searches":
            return self.serve_searches_list()
        if path.startswith("/api/local/searches/"):
            sid = path.split("/api/local/searches/")[1].rstrip("/")
            return self.serve_search_get(sid)
        if path == "/api/local/campaigns":
            return self.serve_campaigns_list()
        if path.startswith("/api/local/campaigns/"):
            cid = path.split("/api/local/campaigns/")[1].rstrip("/")
            return self.serve_campaign_get(cid)
        if path == "/api/local/exports":
            return self.serve_export()
        if path.startswith("/api/local/affiliate/"):
            return self.serve_affiliate(path)
        if path.startswith("/api/run/"):
            rid = path.split("/api/run/")[1].rstrip("/")
            return self.serve_run_status(rid)
        if path in ("/", "/index.html"):
            self.path = "/dashboard/index.html"
        super().do_GET()

    def do_POST(self):
        path = self.path.split("?")[0]
        if path == "/api/run":
            return self.serve_run_create()
        if path == "/api/local/searches":
            return self.serve_search_create()
        if path.endswith("/run") and path.startswith("/api/local/searches/"):
            sid = path.replace("/api/local/searches/", "").replace("/run", "")
            return self.serve_search_trigger(sid)
        if path == "/api/local/campaigns":
            return self.serve_campaign_create()
        if path.startswith("/api/local/affiliate/") and path.endswith("/offers"):
            return self.serve_affiliate_offer_create(path)
        if path.startswith("/api/local/affiliate/") and path.endswith("/search"):
            return self.serve_affiliate_search(path)
        if path.startswith("/api/local/affiliate/") and path.endswith("/draft"):
            return self.serve_affiliate_draft(path)
        self.send_response(404)
        self.end_headers()

    def do_PATCH(self):
        path = self.path.split("?")[0]
        if path.startswith("/api/local/searches/"):
            sid = path.split("/api/local/searches/")[1].rstrip("/")
            return self.serve_search_update(sid)
        if path.startswith("/api/local/campaigns/"):
            cid = path.split("/api/local/campaigns/")[1].rstrip("/")
            return self.serve_campaign_update(cid)
        self.send_response(404)
        self.end_headers()

    def do_DELETE(self):
        path = self.path.split("?")[0]
        if path.startswith("/api/local/searches/"):
            sid = path.split("/api/local/searches/")[1].rstrip("/")
            return self.serve_search_delete(sid)
        if path.startswith("/api/local/campaigns/"):
            cid = path.split("/api/local/campaigns/")[1].rstrip("/")
            return self.serve_campaign_delete(cid)
        self.send_response(404)
        self.end_headers()

    # ── Run on-demand (POST /api/run, GET /api/run/:id) ─────────

    def serve_run_create(self):
        payload = self._read_json()
        if payload is None:
            return
        query = (payload.get("query") or payload.get("nicho") or "").strip()
        if not query:
            return self._send_json(400, {"error": "query (ou nicho) obrigatorio"})
        cidade = (payload.get("cidade") or "").strip()
        nicho = (payload.get("nicho") or query).strip()
        campaign_id = (payload.get("campaign_id") or "C-LEGACY").strip()
        plataformas = payload.get("plataformas") or []
        if not isinstance(plataformas, list) or not plataformas:
            plataformas = ["google"]

        run_id = f"R-{uuid.uuid4().hex[:12]}"
        run = {
            "id": run_id,
            "status": "running",
            "query": query,
            "cidade": cidade,
            "nicho": nicho,
            "campaign_id": campaign_id,
            "plataformas": plataformas,
            "started_at": _now(),
            "finished_at": None,
            "stats": None,
            "log": [],
        }
        with _RUNS_LOCK:
            _RUNS[run_id] = run

        # Dispara em background (nao bloqueia a resposta)
        full_payload = {
            "query": query, "cidade": cidade, "nicho": nicho,
            "campaign_id": campaign_id, "plataformas": plataformas,
        }
        t = threading.Thread(target=_execute_run, args=(run_id, full_payload), daemon=True)
        t.start()

        self._send_json(202, {
            "run_id": run_id,
            "status": "running",
            "started_at": run["started_at"],
            "plataformas": plataformas,
            "campaign_id": campaign_id,
        })

    def serve_run_status(self, rid):
        with _RUNS_LOCK:
            run = _RUNS.get(rid)
        if not run:
            return self._send_json(404, {"error": "run nao encontrado", "run_id": rid})
        self._send_json(200, run)

    # ── Leads ───────────────────────────────────────────────────

    def serve_leads(self):
        try:
            if LEADS_DB.exists():
                data = json.loads(LEADS_DB.read_text(encoding="utf-8"))
            else:
                data = []
            self._send_json(200, data)
        except Exception as e:
            self._send_json(500, {"error": str(e)})

    # ── Buscas Salvas ───────────────────────────────────────────

    def serve_searches_list(self):
        try:
            self._send_json(200, searches_module.load())
        except Exception as e:
            self._send_json(500, {"error": str(e)})

    def serve_search_get(self, sid):
        s = searches_module.get(sid)
        if s is None:
            return self._send_json(404, {"error": "busca nao encontrada"})
        self._send_json(200, s)

    def serve_search_create(self):
        payload = self._read_json()
        if payload is None:
            return
        try:
            created = searches_module.add(payload)
            self._send_json(201, created)
        except ValueError as e:
            self._send_json(400, {"error": str(e)})
        except Exception as e:
            self._send_json(500, {"error": str(e)})

    def serve_search_update(self, sid):
        payload = self._read_json()
        if payload is None:
            return
        updated = searches_module.update(sid, payload)
        if updated is None:
            return self._send_json(404, {"error": "busca nao encontrada"})
        self._send_json(200, updated)

    def serve_search_delete(self, sid):
        ok = searches_module.delete(sid)
        if not ok:
            return self._send_json(404, {"error": "busca nao encontrada"})
        self._send_json(200, {"deleted": sid})

    def serve_search_trigger(self, sid):
        s = searches_module.trigger_now(sid)
        if s is None:
            return self._send_json(404, {"error": "busca nao encontrada"})
        self._send_json(200, {"triggered": s})

    # ── Campanhas ───────────────────────────────────────────────

    def _campaigns_with_counts(self):
        """Anexa total_leads e leads_quentes em cada campanha pra UI."""
        camps = campaigns_module.load()
        if LEADS_DB.exists():
            try:
                leads = json.loads(LEADS_DB.read_text(encoding="utf-8"))
            except Exception:
                leads = []
        else:
            leads = []
        counts = {}
        hot_counts = {}
        for l in leads:
            cid = l.get("campaign_id") or "C-LEGACY"
            counts[cid] = counts.get(cid, 0) + 1
            if l.get("temp") == "quente":
                hot_counts[cid] = hot_counts.get(cid, 0) + 1
        for c in camps:
            c["_total_leads"] = counts.get(c["id"], 0)
            c["_hot_leads"] = hot_counts.get(c["id"], 0)
        return camps

    def serve_campaigns_list(self):
        try:
            self._send_json(200, self._campaigns_with_counts())
        except Exception as e:
            self._send_json(500, {"error": str(e)})

    def serve_campaign_get(self, cid):
        c = campaigns_module.get(cid)
        if c is None:
            return self._send_json(404, {"error": "campanha nao encontrada"})
        self._send_json(200, c)

    def serve_campaign_create(self):
        payload = self._read_json()
        if payload is None:
            return
        try:
            # Garante Legado existe como ancora de integridade referencial
            campaigns_module.ensure_legacy()
            created = campaigns_module.add(payload)
            self._send_json(201, created)
        except ValueError as e:
            self._send_json(400, {"error": str(e)})
        except Exception as e:
            self._send_json(500, {"error": str(e)})

    def serve_campaign_update(self, cid):
        payload = self._read_json()
        if payload is None:
            return
        updated = campaigns_module.update(cid, payload)
        if updated is None:
            return self._send_json(404, {"error": "campanha nao encontrada"})
        self._send_json(200, updated)

    def serve_campaign_delete(self, cid):
        # DELETE = arquivar (soft). Pra remover definitivo usar ?hard=1
        qs = self.path.split("?", 1)
        hard = len(qs) > 1 and "hard=1" in qs[1]
        if hard:
            ok = campaigns_module.delete(cid)
        else:
            archived = campaigns_module.archive(cid)
            ok = archived is not None
        if not ok:
            return self._send_json(404, {"error": "campanha nao encontrada ou protegida"})
        self._send_json(200, {"archived" if not hard else "deleted": cid})

    # ── Afiliados (US / BR) ─────────────────────────────────────

    def serve_affiliate(self, path):
        """GET /api/local/affiliate/{market}/{kind} -> le agents/affiliate_{market}/{file}.

        market: us | br    kind: offers | signals | discovery
        Arquivo ausente devolve vazio (BR ainda sem coleta, etc.) em vez de erro.
        """
        parts = path.strip("/").split("/")  # api/local/affiliate/us/offers
        if len(parts) != 5:
            return self._send_json(404, {"error": "rota invalida"})
        market, kind = parts[3], parts[4]
        if market not in ("us", "br"):
            return self._send_json(404, {"error": f"mercado invalido: {market}"})
        fname = {"offers": "offers.json", "signals": "intent_signals.json",
                 "discovery": "discovery.json"}.get(kind)
        if not fname:
            return self._send_json(404, {"error": f"recurso invalido: {kind}"})
        fpath = BASE_DIR / "agents" / f"affiliate_{market}" / fname
        if not fpath.exists():
            return self._send_json(200, [] if kind == "signals" else {})
        try:
            self._send_json(200, json.loads(fpath.read_text(encoding="utf-8")))
        except Exception as e:
            self._send_json(500, {"error": str(e)})

    def serve_affiliate_offer_create(self, path):
        """POST /api/local/affiliate/{market}/offers — cadastra produto+link."""
        parts = path.strip("/").split("/")
        market = parts[3] if len(parts) >= 5 else ""
        if market not in ("us", "br"):
            return self._send_json(404, {"error": "mercado invalido"})
        payload = self._read_json()
        if payload is None:
            return
        product = (payload.get("product") or "").strip()
        if not product:
            return self._send_json(400, {"error": "produto obrigatorio"})
        fpath = BASE_DIR / "agents" / f"affiliate_{market}" / "offers.json"
        try:
            data = json.loads(fpath.read_text(encoding="utf-8")) if fpath.exists() else {}
        except Exception:
            data = {}
        if not isinstance(data, dict):
            data = {}
        offers = data.get("offers") or []
        import re as _re
        max_n = 0
        for o in offers:
            m = _re.search(r"(\d+)$", o.get("id", ""))
            if m:
                max_n = max(max_n, int(m.group(1)))
        offer = {
            "id": f"OFF-{market.upper()}-{max_n + 1:03d}",
            "product": product,
            "category": (payload.get("category") or "").strip(),
            "network": (payload.get("network") or "").strip(),
            "affiliate_link": (payload.get("affiliate_link") or "").strip() or "PLACEHOLDER_TROCAR_APOS_APROVACAO",
            "commission": (payload.get("commission") or "").strip(),
            "allows_social_dm": True,
        }
        offers.append(offer)
        data["offers"] = offers
        data.setdefault("market", market.upper())
        try:
            fpath.parent.mkdir(parents=True, exist_ok=True)
            fpath.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
            self._send_json(201, offer)
        except Exception as e:
            self._send_json(500, {"error": str(e)})

    def serve_affiliate_search(self, path):
        """POST /api/local/affiliate/{market}/search — dispara coleta por produto (background)."""
        parts = path.strip("/").split("/")
        market = parts[3] if len(parts) >= 5 else ""
        if market not in ("us", "br"):
            return self._send_json(404, {"error": "mercado invalido"})
        payload = self._read_json()
        if payload is None:
            return
        query = (payload.get("query") or "").strip()
        if not query:
            return self._send_json(400, {"error": "query obrigatoria"})
        platform = (payload.get("platform") or "reddit").strip()
        if platform not in ("reddit", "tiktok", "instagram", "all"):
            platform = "reddit"
        script = BASE_DIR / "agents" / "affiliate_us" / "spike_collect.py"
        logf = BASE_DIR / "agents" / f"affiliate_{market}" / "last_search.log"
        try:
            logf.parent.mkdir(parents=True, exist_ok=True)
            fh = open(logf, "w", encoding="utf-8")
            max_items = str(int(payload.get("max_items", 12)))
            subprocess.Popen(
                [sys.executable, str(script), "--market", market,
                 "--product", query, "--platform", platform, "--max-items", max_items],
                stdout=fh, stderr=subprocess.STDOUT, cwd=str(BASE_DIR),
            )
            self._send_json(202, {"started": True, "query": query,
                                  "market": market, "platform": platform})
        except Exception as e:
            self._send_json(500, {"error": str(e)})

    def serve_affiliate_draft(self, path):
        """POST /api/local/affiliate/{market}/draft — gera a DM de outreach pra um sinal."""
        parts = path.strip("/").split("/")
        market = parts[3] if len(parts) >= 5 else ""
        if market not in ("us", "br"):
            return self._send_json(404, {"error": "mercado invalido"})
        payload = self._read_json()
        if payload is None:
            return
        signal = payload.get("signal") or {}
        try:
            import importlib
            sys.path.insert(0, str(BASE_DIR / "agents" / "affiliate_us"))
            outreach = importlib.import_module("outreach")
            self._send_json(200, outreach.generate_dm(market, signal))
        except Exception as e:
            self._send_json(500, {"error": str(e)})

    # ── Exports ─────────────────────────────────────────────────

    def serve_export(self):
        """GET /api/local/exports?campaign_id=C-0001&format=csv|xlsx"""
        qs = parse_qs(urlparse(self.path).query)
        campaign_id = (qs.get("campaign_id", [""])[0] or "").strip()
        fmt = (qs.get("format", ["csv"])[0] or "csv").lower()

        if not campaign_id:
            return self._send_json(400, {"error": "campaign_id obrigatorio"})

        try:
            filename, content, count, campaign = exports_module.build_export(campaign_id, fmt)
        except exports_module.ExportError as e:
            status = 404 if e.code == "campaign_not_found" else 400
            return self._send_json(status, {"error": str(e), "code": e.code})
        except Exception as e:
            return self._send_json(500, {"error": str(e)})

        # Persiste arquivo + atualiza campanha (se nao for caso vazio).
        if count > 0:
            try:
                exports_module.EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
                (exports_module.EXPORTS_DIR / filename).write_bytes(content)
                campaigns_module.update(campaign_id, {
                    "last_exported_at": exports_module.datetime.now().isoformat(timespec="seconds"),
                    "last_exported_count": count,
                    "last_exported_format": fmt,
                })
            except Exception as e:
                # Falhou em salvar, mas ainda entregamos o arquivo pro cliente
                print(f"[exports] aviso: falha ao persistir/atualizar: {e}")

        if fmt == "xlsx":
            ctype = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        else:
            ctype = "text/csv; charset=utf-8"

        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", len(content))
        self.send_header(
            "Content-Disposition",
            f"attachment; filename=\"{filename}\"; filename*=UTF-8''{quote(filename)}",
        )
        self.send_header("X-Lead-Count", str(count))
        self.end_headers()
        if content:
            self.wfile.write(content)

    # ── Helpers ─────────────────────────────────────────────────

    def _send_json(self, status, obj):
        data = json.dumps(obj, ensure_ascii=False, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", len(data))
        self.end_headers()
        self.wfile.write(data)

    def _read_json(self):
        length = int(self.headers.get("Content-Length", 0))
        if length == 0:
            self._send_json(400, {"error": "body vazio"})
            return None
        try:
            body = self.rfile.read(length).decode("utf-8")
            return json.loads(body)
        except json.JSONDecodeError as e:
            self._send_json(400, {"error": f"JSON invalido: {e}"})
            return None

    def log_message(self, format, *args):
        msg = str(args[0]) if args else ""
        if "/api/" in msg or "/leads" in msg or ".html" in msg:
            print(f"[{self.log_date_time_string()}] {msg}")


def main():
    server = HTTPServer(("0.0.0.0", PORT), LeadMachineHandler)
    print(f"Lead Machine Dashboard: http://localhost:{PORT}")
    print(f"Leads API:              http://localhost:{PORT}/leads.json")
    print(f"Buscas API:             http://localhost:{PORT}/api/local/searches")
    print(f"Run on-demand:          POST http://localhost:{PORT}/api/run")
    print(f"                         GET http://localhost:{PORT}/api/run/:id")
    print(f"\nPressione Ctrl+C para parar")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServer parado.")
        server.server_close()


if __name__ == "__main__":
    main()
