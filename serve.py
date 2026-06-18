#!/usr/bin/env python3
"""
Lead Machine — Server local
Serve o dashboard + leads-db.json + buscas salvas + proxy para Paperclip API.

Uso:
  python serve.py
  → Dashboard:     http://localhost:8081
  → Leads API:     http://localhost:8081/leads.json
  → Buscas API:    http://localhost:8081/api/local/searches
  → Paperclip API: http://localhost:8081/api/* (proxy → localhost:3100)
"""

import json
import os
import sys
import urllib.request
import urllib.error
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path

# Permite importar modulos de agents/
sys.path.insert(0, str(Path(__file__).parent / "agents"))
import searches as searches_module
import campaigns as campaigns_module
import exports as exports_module
from urllib.parse import quote, parse_qs, urlparse

def env_int(name, default):
    try:
        return int(os.getenv(name, str(default)))
    except ValueError:
        return default


PORT = env_int("DASHBOARD_PORT", 8081)
PAPERCLIP_PORT = env_int("PAPERCLIP_PORT", 3100)
PAPERCLIP_URL = os.getenv("PAPERCLIP_URL", f"http://localhost:{PAPERCLIP_PORT}").rstrip("/")
BASE_DIR = Path(__file__).parent
LEADS_DB = BASE_DIR / "leads-export" / "leads-db.json"


class LeadMachineHandler(SimpleHTTPRequestHandler):
    """Handler que serve dashboard + leads + buscas + proxy para Paperclip."""

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
        if path.startswith("/api/"):
            return self.proxy_to_paperclip("GET")
        if path in ("/", "/index.html"):
            self.path = "/dashboard/index.html"
        super().do_GET()

    def do_POST(self):
        path = self.path.split("?")[0]
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
        if path.startswith("/api/"):
            return self.proxy_to_paperclip("POST")
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
        if path.startswith("/api/"):
            return self.proxy_to_paperclip("PATCH")
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

    # ── Proxy Paperclip ─────────────────────────────────────────

    def proxy_to_paperclip(self, method):
        target_url = f"{PAPERCLIP_URL}{self.path}"
        try:
            body = None
            if method in ("POST", "PATCH"):
                content_length = int(self.headers.get("Content-Length", 0))
                if content_length > 0:
                    body = self.rfile.read(content_length)

            req = urllib.request.Request(
                target_url, data=body, method=method,
                headers={"Content-Type": "application/json"},
            )

            with urllib.request.urlopen(req, timeout=120) as resp:
                data = resp.read()
                self.send_response(resp.status)
                self.send_header("Content-Type", resp.headers.get("Content-Type", "application/json"))
                self.send_header("Content-Length", len(data))
                self.end_headers()
                self.wfile.write(data)

        except urllib.error.HTTPError as e:
            data = e.read()
            self.send_response(e.code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", len(data))
            self.end_headers()
            self.wfile.write(data)

        except Exception as e:
            self._send_json(502, {"error": f"Paperclip offline: {e}"})

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
            import subprocess
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
    print(f"Paperclip Proxy:        http://localhost:{PORT}/api/*  ->  {PAPERCLIP_URL}")
    print(f"\nPressione Ctrl+C para parar")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServer parado.")
        server.server_close()


if __name__ == "__main__":
    main()
