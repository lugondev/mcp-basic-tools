import json
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from tools import web_search as ws
from tools.web_search import WebSearchError, web_search


def _make_mock_client(get_response):
    mock = AsyncMock()
    mock.get = AsyncMock(return_value=get_response)
    mock.__aenter__ = AsyncMock(return_value=mock)
    mock.__aexit__ = AsyncMock(return_value=False)
    return mock


def _response(data, status=200):
    resp = MagicMock()
    resp.json = MagicMock(return_value=data)
    resp.status_code = status
    if status >= 400:
        resp.raise_for_status = MagicMock(
            side_effect=httpx.HTTPStatusError("error", request=MagicMock(), response=resp)
        )
    else:
        resp.raise_for_status = MagicMock()
    return resp


def _mock_ddgs(results=None, error=None):
    """Patch the DDGS class so tests never touch the network."""
    client = MagicMock()
    for method in ("text", "news", "images", "videos", "books"):
        if error is not None:
            getattr(client, method).side_effect = error
        else:
            getattr(client, method).return_value = results or []
    return patch.object(ws, "DDGS", MagicMock(return_value=client)), client


async def test_web_search_returns_ddgs_results():
    ddgs_patch, client = _mock_ddgs(
        [
            {
                "title": "FastAPI",
                "href": "https://fastapi.tiangolo.com/",
                "body": "FastAPI framework, high performance",
            }
        ]
    )
    with ddgs_patch:
        result = json.loads(await web_search("fastapi"))

    assert result["source"] == "ddgs"
    assert result["number_of_results"] == 1
    assert result["results"] == [
        {
            "url": "https://fastapi.tiangolo.com/",
            "title": "FastAPI",
            "content": "FastAPI framework, high performance",
        }
    ]
    client.text.assert_called_once_with(
        query="fastapi",
        region="wt-wt",
        safesearch="off",
        max_results=ws.MAX_RESULTS,
        page=1,
        backend=ws.SEARCH_BACKEND,
    )


async def test_web_search_maps_params_onto_ddgs():
    ddgs_patch, client = _mock_ddgs([{"title": "t", "href": "https://x.dev/", "body": "b"}])
    with ddgs_patch:
        await web_search(
            "phở bò",
            categories="news",
            language="vi",
            time_range="day",
            safesearch=2,
            pageno=3,
        )

    client.news.assert_called_once_with(
        query="phở bò",
        region="vn-vi",
        safesearch="on",
        max_results=ws.MAX_RESULTS,
        page=3,
        backend=ws.SEARCH_BACKEND,
        timelimit="d",
    )


async def test_web_search_accepts_full_region_code():
    ddgs_patch, client = _mock_ddgs([{"title": "t", "href": "https://x.dev/", "body": "b"}])
    with ddgs_patch:
        await web_search("test", language="uk-en")

    assert client.text.call_args.kwargs["region"] == "uk-en"


async def test_web_search_dedupes_and_normalizes_alternate_fields():
    ddgs_patch, _client = _mock_ddgs(
        [
            {"title": "A", "url": "https://a.dev/", "description": "desc", "source": "News"},
            {"title": "A dup", "url": "https://a.dev/", "description": "dup"},
            {"title": "No url", "body": "dropped"},
        ]
    )
    with ddgs_patch:
        result = json.loads(await web_search("a", categories="news"))

    assert result["results"] == [
        {"url": "https://a.dev/", "title": "A", "content": "desc", "source": "News"}
    ]


async def test_web_search_falls_back_to_instant_answer_when_ddgs_empty():
    data = {
        "Heading": "FastAPI",
        "AbstractURL": "https://en.wikipedia.org/wiki/FastAPI",
        "AbstractText": "FastAPI is a web framework.",
        "RelatedTopics": [{"FirstURL": "https://x.dev/", "Text": "X - a thing"}],
    }
    ddgs_patch, _client = _mock_ddgs([])
    mock_client = _make_mock_client(_response(data))
    with ddgs_patch, patch("httpx.AsyncClient", return_value=mock_client):
        result = json.loads(await web_search("fastapi"))

    assert result["source"] == "instant_answer"
    assert result["answer"] == "FastAPI is a web framework."
    assert result["results"] == [
        {
            "url": "https://en.wikipedia.org/wiki/FastAPI",
            "title": "FastAPI",
            "content": "FastAPI is a web framework.",
        },
        {"url": "https://x.dev/", "title": "X", "content": "a thing"},
    ]
    mock_client.get.assert_called_once_with(
        "https://api.duckduckgo.com/",
        params={
            "q": "fastapi",
            "format": "json",
            "no_html": 1,
            "no_redirect": 1,
            "skip_disambig": 1,
            "t": "mcp-basic-tools",
        },
    )


async def test_web_search_falls_back_when_ddgs_raises():
    ddgs_patch, _client = _mock_ddgs(error=RuntimeError("No results found."))
    mock_client = _make_mock_client(_response({"Answer": "42"}))
    with ddgs_patch, patch("httpx.AsyncClient", return_value=mock_client):
        result = json.loads(await web_search("meaning of life"))

    assert result["source"] == "instant_answer"
    assert result["answer"] == "42"


async def test_web_search_works_without_ddgs_installed():
    mock_client = _make_mock_client(_response({"Answer": "42"}))
    with patch.object(ws, "DDGS", None), patch("httpx.AsyncClient", return_value=mock_client):
        result = json.loads(await web_search("meaning of life"))

    assert result["source"] == "instant_answer"


async def test_web_search_rejects_empty_query():
    with pytest.raises(WebSearchError, match="empty"):
        await web_search("   ")


async def test_web_search_raises_when_both_sources_fail():
    ddgs_patch, _client = _mock_ddgs([])
    mock_client = _make_mock_client(_response({}, status=502))
    with ddgs_patch, patch("httpx.AsyncClient", return_value=mock_client):
        with pytest.raises(WebSearchError):
            await web_search("fastapi")
