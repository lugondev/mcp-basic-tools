from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urlparse

import httpx

TOOL_DEF = {
    "name": "fetch_url",
    "description": "Fetch a URL over HTTP(S) and return its response text, truncated to max_length.",
    "inputSchema": {
        "type": "object",
        "properties": {
            "url": {"type": "string", "description": "http(s) URL to fetch"},
            "max_length": {
                "type": "integer",
                "description": "Maximum number of characters to return",
                "default": 5000,
            },
        },
        "required": ["url"],
    },
}


class FetchError(Exception):
    pass


def _assert_public_host(hostname: str) -> None:
    try:
        addrs = [ipaddress.ip_address(hostname)]
    except ValueError:
        try:
            infos = socket.getaddrinfo(hostname, None)
        except socket.gaierror as exc:
            raise FetchError(f"Could not resolve host: {hostname}") from exc
        addrs = [ipaddress.ip_address(info[4][0]) for info in infos]

    for addr in addrs:
        if (
            addr.is_private
            or addr.is_loopback
            or addr.is_link_local
            or addr.is_multicast
            or addr.is_reserved
            or addr.is_unspecified
        ):
            raise FetchError(f"Refusing to fetch internal/private address: {hostname}")


async def fetch_url(url: str, max_length: int = 5000) -> str:
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise FetchError("Only http/https URLs are allowed")
    if not parsed.hostname:
        raise FetchError("URL must include a host")
    _assert_public_host(parsed.hostname)

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url)
            resp.raise_for_status()
    except httpx.HTTPError as exc:
        raise FetchError(f"Failed to fetch {url}: {exc}") from exc

    return resp.text[:max_length]
