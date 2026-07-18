from __future__ import annotations

import json

import httpx

TEGUSEARCH_BASE_URL = "https://tegusearch-main.lugondev.workers.dev"

TOOL_DEF = {
    "name": "web_search",
    "description": "Search the web via TeguSearch (meta search aggregator) and return matching results.",
    "inputSchema": {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Search keyword"},
            "categories": {
                "type": "string",
                "description": "general, news, images, videos, files, social media",
                "default": "general",
            },
            "language": {
                "type": "string",
                "description": "Result language, e.g. auto, all, en, vi, fr, ja, zh",
                "default": "auto",
            },
            "time_range": {
                "type": "string",
                "description": "day, week, month, year, or empty for no filter",
                "default": "",
            },
            "safesearch": {
                "type": "integer",
                "description": "0 off, 1 moderate, 2 strict",
                "default": 0,
            },
            "pageno": {"type": "integer", "description": "Page number for pagination", "default": 1},
        },
        "required": ["query"],
    },
}


class WebSearchError(Exception):
    pass


async def web_search(
    query: str,
    categories: str = "general",
    language: str = "auto",
    time_range: str = "",
    safesearch: int = 0,
    pageno: int = 1,
) -> str:
    if not query.strip():
        raise WebSearchError("query must not be empty")

    params = {
        "q": query,
        "categories": categories,
        "language": language,
        "safesearch": safesearch,
        "pageno": pageno,
        "format": "json",
    }
    if time_range:
        params["time_range"] = time_range

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(f"{TEGUSEARCH_BASE_URL}/search", params=params)
            resp.raise_for_status()
            data = resp.json()
    except httpx.HTTPError as exc:
        raise WebSearchError(f"Failed to search for {query!r}: {exc}") from exc

    return json.dumps(data)
