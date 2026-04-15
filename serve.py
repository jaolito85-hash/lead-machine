#!/usr/bin/env python3
"""
Lead Machine — Server local
Serve o dashboard + leads-db.json + proxy para Paperclip API (resolve CORS).

Uso:
  python serve.py
  → Dashboard:     http://localhost:8080
  → Leads API:     http://localhost:8080/leads.json
  → Paperclip API: http://localhost:8080/api/* (proxy → localhost:3100)
"""

import json
import urllib.request
import urllib.error
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path

PORT = 8081
PAPERCLIP_URL = "http://localhost:3100"
BASE_DIR = Path(__file__).parent
LEADS_DB = BASE_DIR / "leads-export" / "leads-db.json"


class LeadMachineHandler(SimpleHTTPRequestHandler):
    """Handler que serve dashboard + leads + proxy para Paperclip."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(BASE_DIR), **kwargs)

    def end_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PATCH, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Cache-Control", "no-cache")
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.end_headers()

    def do_GET(self):
        path = self.path.split("?")[0]
        if path == "/leads.json":
            self.serve_leads()
            return
        if path.startswith("/api/"):
            self.proxy_to_paperclip("GET")
            return
        if path in ("/", "/index.html"):
            self.path = "/dashboard/index.html"
        super().do_GET()

    def do_POST(self):
        if self.path.startswith("/api/"):
            self.proxy_to_paperclip("POST")
        else:
            self.send_response(404)
            self.end_headers()

    def do_PATCH(self):
        if self.path.startswith("/api/"):
            self.proxy_to_paperclip("PATCH")
        else:
            self.send_response(404)
            self.end_headers()

    def proxy_to_paperclip(self, method):
        """Proxy requests para Paperclip API em localhost:3100."""
        target_url = f"{PAPERCLIP_URL}{self.path}"
        try:
            # Ler body se POST/PATCH
            body = None
            if method in ("POST", "PATCH"):
                content_length = int(self.headers.get("Content-Length", 0))
                if content_length > 0:
                    body = self.rfile.read(content_length)

            req = urllib.request.Request(
                target_url,
                data=body,
                method=method,
                headers={"Content-Type": "application/json"},
            )

            with urllib.request.urlopen(req, timeout=120) as resp:
                response_data = resp.read()
                self.send_response(resp.status)
                self.send_header("Content-Type", resp.headers.get("Content-Type", "application/json"))
                self.send_header("Content-Length", len(response_data))
                self.end_headers()
                self.wfile.write(response_data)

        except urllib.error.HTTPError as e:
            response_data = e.read()
            self.send_response(e.code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", len(response_data))
            self.end_headers()
            self.wfile.write(response_data)

        except Exception as e:
            error = json.dumps({"error": f"Paperclip offline: {e}"}).encode("utf-8")
            self.send_response(502)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", len(error))
            self.end_headers()
            self.wfile.write(error)

    def serve_leads(self):
        """Serve leads-db.json sempre atualizado."""
        try:
            if LEADS_DB.exists():
                data = json.loads(LEADS_DB.read_text(encoding="utf-8"))
            else:
                data = []

            content = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", len(content))
            self.end_headers()
            self.wfile.write(content)

        except Exception as e:
            error = json.dumps({"error": str(e)}).encode("utf-8")
            self.send_response(500)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(error)

    def log_message(self, format, *args):
        msg = str(args[0]) if args else ""
        if "/api/" in msg or "/leads" in msg or ".html" in msg:
            print(f"[{self.log_date_time_string()}] {msg}")


def main():
    server = HTTPServer(("0.0.0.0", PORT), LeadMachineHandler)
    print(f"Lead Machine Dashboard: http://localhost:{PORT}")
    print(f"Leads API:              http://localhost:{PORT}/leads.json")
    print(f"Paperclip Proxy:        http://localhost:{PORT}/api/* -> {PAPERCLIP_URL}")
    print(f"\nPressione Ctrl+C para parar")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServer parado.")
        server.server_close()


if __name__ == "__main__":
    main()
