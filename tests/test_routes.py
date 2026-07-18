from unittest.mock import patch

from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


def test_list_tools_returns_all_defs():
    resp = client.get("/tools")
    assert resp.status_code == 200
    names = {t["name"] for t in resp.json()}
    assert names == {"get_current_time", "fetch_url", "get_ip_info", "web_search"}


def test_invoke_get_current_time():
    resp = client.post("/tools/get_current_time", json={"arguments": {}})
    assert resp.status_code == 200
    assert "result" in resp.json()


def test_invoke_unknown_tool_404():
    resp = client.post("/tools/nope", json={"arguments": {}})
    assert resp.status_code == 404


def test_invoke_get_current_time_bad_timezone_400():
    resp = client.post("/tools/get_current_time", json={"arguments": {"timezone": "Not/AZone"}})
    assert resp.status_code == 400


def test_invoke_fetch_url_missing_url_422():
    resp = client.post("/tools/fetch_url", json={"arguments": {}})
    assert resp.status_code == 422


def test_invoke_fetch_url_blocked_host_400():
    with patch("socket.getaddrinfo", side_effect=AssertionError("should not resolve a literal IP")):
        resp = client.post("/tools/fetch_url", json={"arguments": {"url": "http://127.0.0.1/"}})
    assert resp.status_code == 400


def test_invoke_get_ip_info_bad_ip_400():
    resp = client.post("/tools/get_ip_info", json={"arguments": {"ip": "not-an-ip"}})
    assert resp.status_code == 400


def test_invoke_get_ip_info_missing_ip_422():
    resp = client.post("/tools/get_ip_info", json={"arguments": {}})
    assert resp.status_code == 422


def test_invoke_web_search_empty_query_400():
    resp = client.post("/tools/web_search", json={"arguments": {"query": "   "}})
    assert resp.status_code == 400


def test_invoke_web_search_missing_query_422():
    resp = client.post("/tools/web_search", json={"arguments": {}})
    assert resp.status_code == 422
