from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from tools.fetch import FetchError, fetch_url


def _make_mock_client(get_response):
    mock = AsyncMock()
    mock.get = AsyncMock(return_value=get_response)
    mock.__aenter__ = AsyncMock(return_value=mock)
    mock.__aexit__ = AsyncMock(return_value=False)
    return mock


def _response(text, status=200):
    resp = MagicMock()
    resp.text = text
    resp.status_code = status
    if status >= 400:
        resp.raise_for_status = MagicMock(
            side_effect=httpx.HTTPStatusError("error", request=MagicMock(), response=resp)
        )
    else:
        resp.raise_for_status = MagicMock()
    return resp


def _public_addrinfo():
    return [(None, None, None, None, ("93.184.216.34", 0))]


async def test_fetch_url_returns_text():
    mock_client = _make_mock_client(_response("hello world"))
    with patch("socket.getaddrinfo", return_value=_public_addrinfo()):
        with patch("httpx.AsyncClient", return_value=mock_client):
            result = await fetch_url("https://example.com")
    assert result == "hello world"


async def test_fetch_url_truncates_to_max_length():
    mock_client = _make_mock_client(_response("a" * 100))
    with patch("socket.getaddrinfo", return_value=_public_addrinfo()):
        with patch("httpx.AsyncClient", return_value=mock_client):
            result = await fetch_url("https://example.com", max_length=10)
    assert result == "a" * 10


async def test_fetch_url_rejects_non_http_scheme():
    with pytest.raises(FetchError, match="http/https"):
        await fetch_url("ftp://example.com")


async def test_fetch_url_rejects_loopback_ip():
    with pytest.raises(FetchError, match="internal/private"):
        await fetch_url("http://127.0.0.1/secret")


async def test_fetch_url_rejects_private_ip():
    with pytest.raises(FetchError, match="internal/private"):
        await fetch_url("http://10.0.0.5/")


async def test_fetch_url_raises_on_upstream_error():
    mock_client = _make_mock_client(_response("err", status=500))
    with patch("socket.getaddrinfo", return_value=_public_addrinfo()):
        with patch("httpx.AsyncClient", return_value=mock_client):
            with pytest.raises(FetchError):
                await fetch_url("https://example.com")
