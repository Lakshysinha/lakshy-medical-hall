from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

from pharmacy_app.api import PharmacyAPI, handle_api_error


class PharmacyHTTPRequestHandler(BaseHTTPRequestHandler):
    api: PharmacyAPI

    def _send_json(self, status: int, payload: dict) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_json(self) -> dict:
        content_length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(content_length) if content_length > 0 else b"{}"
        return json.loads(raw.decode("utf-8"))

    def _token(self) -> str:
        auth = self.headers.get("Authorization", "")
        if auth.startswith("Bearer "):
            return auth.replace("Bearer ", "", 1).strip()
        return ""

    def do_POST(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        try:
            payload = self._read_json()
            if path == "/auth/login":
                result = self.api.login(payload["username"], payload["password"])
                self._send_json(200, result)
                return
            if path == "/auth/logout":
                result = self.api.logout(self._token())
                self._send_json(200, result)
                return
            if path == "/medicines":
                result = self.api.add_medicine(self._token(), payload)
                self._send_json(201, result)
                return
            if path == "/batches":
                result = self.api.add_batch(self._token(), payload)
                self._send_json(201, result)
                return
            if path == "/sales":
                result = self.api.create_sale(self._token(), payload)
                self._send_json(201, result)
                return
            self._send_json(404, {"error": "Not found"})
        except Exception as exc:  # transport-level error mapping
            mapped = handle_api_error(exc)
            self._send_json(mapped["status_code"], {"error": mapped["error"]})

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        path = parsed.path
        query = parse_qs(parsed.query)
        try:
            if path == "/medicines/search":
                result = self.api.search_medicine(self._token(), query.get("q", [""])[0])
                self._send_json(200, result)
                return
            if path == "/reports/daily":
                result = self.api.daily_summary(self._token(), query["day"][0])
                self._send_json(200, result)
                return
            self._send_json(404, {"error": "Not found"})
        except Exception as exc:  # transport-level error mapping
            mapped = handle_api_error(exc)
            self._send_json(mapped["status_code"], {"error": mapped["error"]})


def build_server(host: str, port: int, api: PharmacyAPI) -> ThreadingHTTPServer:
    class _BoundHandler(PharmacyHTTPRequestHandler):
        pass

    _BoundHandler.api = api
    return ThreadingHTTPServer((host, port), _BoundHandler)
