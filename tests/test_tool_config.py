import importlib

from fastapi.testclient import TestClient


def _reload_main_with_disabled(monkeypatch, disabled: str):
    monkeypatch.setenv("MCP_DISABLED_TOOLS", disabled)
    import main

    importlib.reload(main)
    return main


def test_disabled_tool_excluded_from_list(monkeypatch):
    main = _reload_main_with_disabled(monkeypatch, "web_search")
    client = TestClient(main.app)

    resp = client.get("/tools")
    names = {t["name"] for t in resp.json()}
    assert "web_search" not in names
    assert names == {"get_current_time", "fetch_url", "get_ip_info"}


def test_disabled_tool_invoke_returns_404(monkeypatch):
    main = _reload_main_with_disabled(monkeypatch, "web_search")
    client = TestClient(main.app)

    resp = client.post("/tools/web_search", json={"arguments": {"query": "test"}})
    assert resp.status_code == 404


def test_no_disabled_tools_env_keeps_all_tools(monkeypatch):
    main = _reload_main_with_disabled(monkeypatch, "")
    client = TestClient(main.app)

    resp = client.get("/tools")
    names = {t["name"] for t in resp.json()}
    assert names == {"get_current_time", "fetch_url", "get_ip_info", "web_search"}
