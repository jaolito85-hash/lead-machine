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
import sys
import urllib.request
import urllib.error
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path

# Permite importar modulos de agents/
sys.path.insert(0, str(Path(__file__).parent / "agents"))
import searches as searches_module

PORT = 8081
PAPERCLIP_URL = "http://localhost:3100"
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
        if path.startswith("/api/"):
            return self.proxy_to_paperclip("POST")
        self.send_response(404)
        self.end_headers()

    def do_PATCH(self):
        path = self.path.split("?")[0]
        if path.startswith("/api/local/searches/"):
            sid = path.split("/api/local/searches/")[1].rstrip("/")
            return self.serve_search_update(sid)
        if path.startswith("/api/"):
            return self.proxy_to_paperclip("PATCH")
        self.send_response(404)
        self.end_headers()

    def do_DELETE(self):
        path = self.path.split("?")[0]
        if path.startswith("/api/local/searches/"):
            sid = path.split("/api/local/searches/")[1].rstrip("/")
            return self.serve_search_delete(sid)
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
