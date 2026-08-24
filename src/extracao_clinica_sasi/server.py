"""Servidor HTTP local do motor clínico, sem dependências externas."""

from __future__ import annotations

import argparse
import json
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

from .core import compilar_payload

MAX_BODY_BYTES = 2 * 1024 * 1024


class ClinicalHandler(BaseHTTPRequestHandler):
    server_version = "ExtracaoClinicaSASI/0.1"

    def log_message(self, format: str, *args: Any) -> None:
        return

    def _json(self, status: int, payload: dict[str, Any]) -> None:
        encoded = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(encoded)

    def do_GET(self) -> None:
        if self.path == "/healthz":
            self._json(
                HTTPStatus.OK,
                {"status": "ok", "service": "extracao-clinica-sasi"},
            )
            return
        self._json(HTTPStatus.NOT_FOUND, {"error": "rota não encontrada"})

    def do_POST(self) -> None:
        if self.path != "/v1/compile":
            self._json(HTTPStatus.NOT_FOUND, {"error": "rota não encontrada"})
            return
        content_type = self.headers.get("Content-Type", "").split(";", 1)[0].strip()
        if content_type != "application/json":
            self._json(HTTPStatus.UNSUPPORTED_MEDIA_TYPE, {"error": "Content-Type deve ser application/json"})
            return
        try:
            tamanho = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            self._json(HTTPStatus.BAD_REQUEST, {"error": "Content-Length inválido"})
            return
        if tamanho <= 0 or tamanho > MAX_BODY_BYTES:
            self._json(HTTPStatus.REQUEST_ENTITY_TOO_LARGE, {"error": "corpo vazio ou maior que 2 MiB"})
            return
        try:
            payload = json.loads(self.rfile.read(tamanho))
            resultado = compilar_payload(payload)
        except (json.JSONDecodeError, UnicodeDecodeError, ValueError) as exc:
            self._json(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return
        self._json(HTTPStatus.OK, resultado)


def criar_servidor(host: str = "127.0.0.1", port: int = 8765) -> ThreadingHTTPServer:
    return ThreadingHTTPServer((host, port), ClinicalHandler)


def main() -> int:
    parser = argparse.ArgumentParser(description="Servidor local do motor clínico SASI")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    server = criar_servidor(args.host, args.port)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
