from __future__ import annotations

import json
import os

import anyio.to_thread
import httpx

# DuckDuckGo's own HTML endpoints answer scrapers with an anti-bot challenge, so the
# web results come from ddgs (a metasearch aggregator that fans out to Brave, Yahoo,
# Bing, Yandex, ...). DuckDuckGo's Instant Answer API is official and unblocked, but
# only serves entity abstracts, so it is the fallback rather than the primary source.
DUCKDUCKGO_INSTANT_ANSWER_URL = "https://api.duckduckgo.com/"

# Comma-delimited ddgs backends, e.g. "brave,yahoo". "auto" tries every enabled engine.
SEARCH_BACKEND = os.environ.get("WEB_SEARCH_BACKEND", "auto")
SEARCH_PROXY = os.environ.get("WEB_SEARCH_PROXY") or None
SEARCH_TIMEOUT = int(os.environ.get("WEB_SEARCH_TIMEOUT", "15"))
MAX_RESULTS = int(os.environ.get("WEB_SEARCH_MAX_RESULTS", "10"))

# ddgs pulls in compiled deps (primp, lxml); keep it optional so the server still boots
# on the Instant Answer fallback alone when it is not installed.
try:
    from ddgs import DDGS
except ImportError:  # pragma: no cover - exercised via _ddgs_available in tests
    DDGS = None

_CATEGORY_METHODS = {
    "general": "text",
    "web": "text",
    "news": "news",
    "images": "images",
    "videos": "videos",
    "files": "books",
    "books": "books",
}

_SAFESEARCH = {0: "off", 1: "moderate", 2: "on"}

_TIME_RANGE = {"day": "d", "week": "w", "month": "m", "year": "y"}

# ddgs wants a region code (us-en, vn-vi). Map the bare language codes callers send.
_REGION_BY_LANGUAGE = {
    "en": "us-en",
    "vi": "vn-vi",
    "fr": "fr-fr",
    "de": "de-de",
    "ja": "jp-jp",
    "ko": "kr-kr",
    "zh": "cn-zh",
    "es": "es-es",
    "ru": "ru-ru",
    "th": "th-th",
    "id": "id-id",
}

TOOL_DEF = {
    "name": "web_search",
    "description": (
        "Search the web and return matching results. Aggregates several search engines "
        "and falls back to the DuckDuckGo Instant Answer API."
    ),
    "inputSchema": {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Search keyword"},
            "categories": {
                "type": "string",
                "description": "general, news, images, videos, files",
                "default": "general",
            },
            "language": {
                "type": "string",
                "description": (
                    "Result language: auto, all, a language code (en, vi, fr, ja, zh) "
                    "or a full region code (us-en, vn-vi)"
                ),
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


def _region(language: str) -> str:
    language = (language or "").strip().lower()
    if language in ("", "auto", "all"):
        return "wt-wt"
    if "-" in language:
        return language
    return _REGION_BY_LANGUAGE.get(language, "wt-wt")


def _normalize_ddgs_result(raw: dict) -> dict | None:
    """ddgs field names differ per category (href vs url, body vs description)."""
    url = raw.get("href") or raw.get("url") or raw.get("image") or ""
    title = raw.get("title") or ""
    content = raw.get("body") or raw.get("description") or raw.get("content") or raw.get("info") or ""
    if not url:
        return None
    result = {"url": url, "title": title, "content": content}
    for key in ("date", "source", "publisher", "duration", "thumbnail", "author"):
        if raw.get(key):
            result[key] = raw[key]
    return result


def _ddgs_search(
    query: str,
    categories: str,
    language: str,
    time_range: str,
    safesearch: int,
    pageno: int,
) -> list[dict]:
    """Blocking; always call through anyio.to_thread so the event loop keeps running."""
    method = _CATEGORY_METHODS.get((categories or "general").strip().lower(), "text")
    kwargs = {
        "query": query,
        "region": _region(language),
        "safesearch": _SAFESEARCH.get(safesearch, "off"),
        "max_results": MAX_RESULTS,
        "page": max(1, pageno),
        "backend": SEARCH_BACKEND,
    }
    timelimit = _TIME_RANGE.get((time_range or "").strip().lower())
    if timelimit:
        kwargs["timelimit"] = timelimit

    client = DDGS(proxy=SEARCH_PROXY, timeout=SEARCH_TIMEOUT)
    raw_results = getattr(client, method)(**kwargs)

    results = []
    seen = set()
    for raw in raw_results or []:
        item = _normalize_ddgs_result(raw)
        if item and item["url"] not in seen:
            seen.add(item["url"])
            results.append(item)
    return results


def _split_title(text: str) -> tuple[str, str]:
    """Instant Answer topic text reads "Title - description"; split it when possible."""
    title, sep, rest = text.partition(" - ")
    if sep and rest.strip():
        return title.strip(), rest.strip()
    return text.strip(), text.strip()


def _collect_topics(topics: list, results: list[dict], seen: set[str]) -> None:
    for topic in topics:
        if not isinstance(topic, dict):
            continue
        nested = topic.get("Topics")
        if isinstance(nested, list):
            _collect_topics(nested, results, seen)
            continue
        url = topic.get("FirstURL") or ""
        if not url or url in seen:
            continue
        seen.add(url)
        title, content = _split_title(topic.get("Text") or "")
        results.append({"url": url, "title": title, "content": content})


def _parse_instant_answer(query: str, data: dict) -> tuple[list[dict], str]:
    results: list[dict] = []
    seen: set[str] = set()

    for url_key, text_key in (("AbstractURL", "AbstractText"), ("DefinitionURL", "Definition")):
        url = data.get(url_key) or ""
        if url and url not in seen:
            seen.add(url)
            results.append(
                {
                    "url": url,
                    "title": data.get("Heading") or query,
                    "content": data.get(text_key) or "",
                }
            )

    for key in ("Results", "RelatedTopics"):
        entries = data.get(key)
        if isinstance(entries, list):
            _collect_topics(entries, results, seen)

    return results, data.get("Answer") or data.get("AbstractText") or ""


async def _instant_answer(query: str) -> tuple[list[dict], str]:
    params = {
        "q": query,
        "format": "json",
        "no_html": 1,
        "no_redirect": 1,
        "skip_disambig": 1,
        "t": "mcp-basic-tools",
    }
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(DUCKDUCKGO_INSTANT_ANSWER_URL, params=params)
            resp.raise_for_status()
            data = resp.json()
    except httpx.HTTPError as exc:
        raise WebSearchError(f"Failed to search for {query!r}: {exc}") from exc

    return _parse_instant_answer(query, data)


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

    results: list[dict] = []
    source = "instant_answer"

    if DDGS is not None:
        try:
            results = await anyio.to_thread.run_sync(
                lambda: _ddgs_search(query, categories, language, time_range, safesearch, pageno)
            )
            source = "ddgs"
        except Exception:  # noqa: BLE001 - any engine failure falls back to Instant Answer
            results = []

    answer = ""
    if not results:
        results, answer = await _instant_answer(query)
        source = "instant_answer"

    return json.dumps(
        {
            "query": query,
            "number_of_results": len(results),
            "results": results,
            "answer": answer,
            "source": source,
            "suggestions": [],
        }
    )
