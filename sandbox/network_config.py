"""Explicit, allowlisted proxy configuration for approved QA connectivity checks.

This module validates configuration only; it does not open network connections,
rotate proxies, select geographic exits, or alter payment/fraud signals.
"""
from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlsplit


@dataclass(frozen=True)
class ApprovedProxy:
    url: str
    host: str


def resolve_approved_proxy(
    proxy_url: str | None,
    approved_hosts: set[str] | frozenset[str],
) -> ApprovedProxy | None:
    """Return a configured HTTPS proxy only when its host is explicitly approved."""
    if not proxy_url:
        return None
    parsed = urlsplit(proxy_url.strip())
    host = (parsed.hostname or "").lower()
    allowed = {item.strip().lower() for item in approved_hosts if item.strip()}
    if parsed.scheme.lower() != "https":
        raise ValueError("Only HTTPS proxies are supported for approved QA connectivity.")
    if not host or host not in allowed:
        raise ValueError("Proxy host is not in the explicit QA allowlist.")
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ValueError("Proxy credentials, query strings, and fragments are not accepted.")
    if parsed.path not in ("", "/"):
        raise ValueError("Proxy URL must not contain a path.")
    try:
        port = parsed.port
    except ValueError as exc:
        raise ValueError("Proxy port is invalid.") from exc
    if port not in (None, 443):
        raise ValueError("Only the default HTTPS proxy port is supported.")
    return ApprovedProxy(url=proxy_url.strip(), host=host)
