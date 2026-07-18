import json
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

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


async def test_web_search_returns_json_string():
    data = {
        "query": "fastapi",
        "number_of_results": 1,
        "results": [
            {"url": "https://fastapi.tiangolo.com/", "title": "FastAPI", "content": "..."}
        ],
        "suggestions": [],
    }
    mock_client = _make_mock_client(_response(data))
    with patch("httpx.AsyncClient", return_value=mock_client):
        result = await web_search("fastapi")
    assert json.loads(result) == data
    mock_client.get.assert_called_once_with(
        "https://tegusearch-main.lugondev.workers.dev/search",
        params={
            "q": "fastapi",
            "categories": "general",
            "language": "auto",
            "safesearch": 0,
            "pageno": 1,
            "format": "json",
        },
    )


async def test_web_search_includes_time_range_when_set():
    mock_client = _make_mock_client(_response({"query": "news", "results": []}))
    with patch("httpx.AsyncClient", return_value=mock_client):
        await web_search("news", time_range="day")
    _, kwargs = mock_client.get.call_args
    assert kwargs["params"]["time_range"] == "day"


async def test_web_search_rejects_empty_query():
    with pytest.raises(WebSearchError, match="empty"):
        await web_search("   ")


async def test_web_search_raises_on_upstream_error():
    mock_client = _make_mock_client(_response({}, status=502))
    with patch("httpx.AsyncClient", return_value=mock_client):
        with pytest.raises(WebSearchError):
            await web_search("fastapi")
