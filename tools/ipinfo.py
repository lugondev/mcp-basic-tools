from __future__ import annotations

import ipaddress
import json

import httpx

TOOL_DEF = {
    "name": "get_ip_info",
    "description": "Look up geolocation and ISP info for an IPv4/IPv6 address via ipinfo.io.",
    "inputSchema": {
        "type": "object",
        "properties": {
            "ip": {"type": "string", "description": "IPv4 or IPv6 address to look up"},
        },
        "required": ["ip"],
    },
}


class IpInfoError(Exception):
    pass


async def get_ip_info(ip: str) -> str:
    try:
        ipaddress.ip_address(ip)
    except ValueError as exc:
        raise IpInfoError(f"Invalid IP address: {ip}") from exc

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(f"https://ipinfo.io/{ip}", params={"format": "json"})
            resp.raise_for_status()
            data = resp.json()
    except httpx.HTTPError as exc:
        raise IpInfoError(f"Failed to fetch IP info for {ip}: {exc}") from exc

    return json.dumps(data)
