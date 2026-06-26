from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

from .native_host import build_status_response

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 18732


class StatusHandler(BaseHTTPRequestHandler):
    server_version = "CodexWorkGate/0.1"

    def _send_json(self, status_code: int, payload: dict[str, Any]) -> None:
        body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self) -> None:
        self._send_json(204, {})

    def do_GET(self) -> None:
        if self.path.split("?", 1)[0] != "/status":
            self._send_json(404, {"ok": False, "reason": "not_found"})
            return
        self._send_json(200, build_status_response())

    def log_message(self, _format: str, *_args: Any) -> None:
        return


def serve_http(host: str = DEFAULT_HOST, port: int = DEFAULT_PORT) -> None:
    server = ThreadingHTTPServer((host, port), StatusHandler)
    server.serve_forever()
