import json
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from tools.ipinfo import IpInfoError, get_ip_info


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


async def test_get_ip_info_returns_json_string():
    data = {
        "ip": "171.239.134.252",
        "city": "Ho Chi Minh City",
        "country": "VN",
        "org": "AS7552 Viettel Group",
    }
    mock_client = _make_mock_client(_response(data))
    with patch("httpx.AsyncClient", return_value=mock_client):
        result = await get_ip_info("171.239.134.252")
    assert json.loads(result) == data
    mock_client.get.assert_called_once_with(
        "https://ipinfo.io/171.239.134.252", params={"format": "json"}
    )


async def test_get_ip_info_rejects_invalid_ip():
    with pytest.raises(IpInfoError, match="Invalid IP"):
        await get_ip_info("not-an-ip")


async def test_get_ip_info_raises_on_upstream_error():
    mock_client = _make_mock_client(_response({}, status=500))
    with patch("httpx.AsyncClient", return_value=mock_client):
        with pytest.raises(IpInfoError):
            await get_ip_info("171.239.134.252")
