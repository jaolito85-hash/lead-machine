"""
Servidor minimo do dashboard.

Roda na porta 8090 (escolhi diferente da 8081 do dashboard principal,
pra voce poder abrir os dois ao mesmo tempo se quiser).

Uso:
  python -m agents.comment_collector.dashboard.serve

Depois abra: http://localhost:8090
"""

import json
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

# Permite rodar como modulo OU direto
if __name__ == "__main__" and __package__ is None:
    sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
    __package__ = "agents.comment_collector.dashboard"

from .. import db  # noqa: E402

DASHBOARD_DIR = Path(__file__).parent
PORT = 8090


class Handler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        # Suprime log padrao (muito verboso)
        pass

    def do_GET(self):
        if self.path == "/" or self.path == "/index.html":
            return self._serve_file("index.html", "text/html; charset=utf-8")

        if self.path == "/api/stats":
            return self._serve_json(db.get_stats())

        self.send_response(404)
        self.end_headers()
        self.wfile.write(b"Not Found")

    def _serve_file(self, name: str, content_type: str):
        path = DASHBOARD_DIR / name
        if not path.exists():
            self.send_response(404)
            self.end_headers()
            return
        body = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _serve_json(self, data: dict):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)


def main():
    db.init_db()
    server = HTTPServer(("0.0.0.0", PORT), Handler)
    print(f"Dashboard rodando em http://localhost:{PORT}")
    print("Ctrl+C pra parar.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nDashboard parado.")


if __name__ == "__main__":
    main()
