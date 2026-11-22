"""Small HTTP server for the public BIN/IIN metadata checker."""
from __future__ import annotations

import json
import os
import re
import threading
import time
from collections import defaultdict, deque
from datetime import datetime, timezone
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

from sandbox.bin_classifier import classify_bin_metadata

ROOT = Path(__file__).resolve().parent / "web"
BINLIST_URL = "https://lookup.binlist.net/"
PREFIX_RE = re.compile(r"^[0-9]{6,8}$")
CACHE_TTL_SECONDS = 21600
RATE_WINDOW_SECONDS = 60
RATE_MAX_REQUESTS = 30
_cache = {}
_rate = defaultdict(deque)
_lock = threading.Lock()


def validate_prefix(value):
    if not PREFIX_RE.fullmatch(value):
        raise ValueError("Only a 6–8 digit BIN/IIN prefix is accepted.")
    return value


def normalize_metadata(data):
    if not isinstance(data, dict):
        raise ValueError("Unexpected metadata response.")
    country = data.get("country") if isinstance(data.get("country"), dict) else {}
    bank = data.get("bank") if isinstance(data.get("bank"), dict) else {}
    number = data.get("number") if isinstance(data.get("number"), dict) else {}
    retrieved = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    classification = classify_bin_metadata(data, source="binlist.net", retrieved_at=retrieved)
    return {
        "scheme": data.get("scheme"), "type": data.get("type"), "brand": data.get("brand"),
        "bank": {"name": bank.get("name")},
        "country": {"name": country.get("name"), "alpha2": country.get("alpha2")},
        "prepaid": data.get("prepaid"),
        "number": {"length": number.get("length"), "luhn": number.get("luhn")},
        "authentication_status": "Not tested",
        "classification": classification,
    }


def _allow_request(client_ip, now=None):
    now = time.monotonic() if now is None else now
    with _lock:
        requests = _rate[client_ip]
        while requests and now - requests[0] >= RATE_WINDOW_SECONDS:
            requests.popleft()
        if len(requests) >= RATE_MAX_REQUESTS:
            return False
        requests.append(now)
        return True


def fetch_metadata(prefix):
    prefix = validate_prefix(prefix)
    now = time.monotonic()
    with _lock:
        cached = _cache.get(prefix)
        if cached and now - cached[0] < CACHE_TTL_SECONDS:
            return 200, cached[1]
    request = Request(BINLIST_URL + prefix, headers={
        "Accept": "application/json", "User-Agent": "SafeBINLookup/1.0"
    })
    try:
        with urlopen(request, timeout=8) as response:
            payload = json.loads(response.read(65536).decode("utf-8"))
        normalized = normalize_metadata(payload)
        with _lock:
            _cache[prefix] = (now, normalized)
        return 200, normalized
    except HTTPError as exc:
        if exc.code == 404:
            return 404, {"error": "No public issuer metadata found."}
        return 502, {"error": "Metadata provider returned an upstream error."}
    except (URLError, TimeoutError, OSError, ValueError, UnicodeDecodeError):
        return 502, {"error": "Metadata provider is temporarily unavailable."}


class CheckerHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def log_message(self, format, *args):
        return

    def _json(self, status, payload):
        body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = urlsplit(self.path).path
        if path.startswith("/api/bin/"):
            prefix = path.removeprefix("/api/bin/")
            try:
                validate_prefix(prefix)
            except ValueError as exc:
                self._json(400, {"error": str(exc)})
                return
            if not _allow_request(self.client_address[0]):
                self._json(429, {"error": "Rate limit reached. Wait a minute and retry."})
                return
            status, payload = fetch_metadata(prefix)
            self._json(status, payload)
            return
        if path == "/":
            self.path = "/bin-checker.html"
        elif path != "/bin-checker.html":
            self._json(404, {"error": "Not found."})
            return
        super().do_GET()


def main():
    host = os.getenv("WEB_HOST", "127.0.0.1")
    port = int(os.getenv("WEB_PORT", "8080"))
    server = ThreadingHTTPServer((host, port), CheckerHandler)
    print(f"BIN/IIN checker listening on http://{host}:{port}")
    print("For public access, place this behind an HTTPS reverse proxy.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
