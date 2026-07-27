from __future__ import annotations

import inspect
import os

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from tools.fetch import TOOL_DEF as FETCH_TOOL_DEF
from tools.fetch import FetchError, fetch_url
from tools.ipinfo import TOOL_DEF as IPINFO_TOOL_DEF
from tools.ipinfo import IpInfoError, get_ip_info
from tools.timedate import TOOL_DEF as TIMEDATE_TOOL_DEF
from tools.timedate import get_current_time
from tools.web_search import TOOL_DEF as WEB_SEARCH_TOOL_DEF
from tools.web_search import WebSearchError, web_search

app = FastAPI(title="mcp-basic-tools")

_ALL_TOOLS = {
    "get_current_time": get_current_time,
    "fetch_url": fetch_url,
    "get_ip_info": get_ip_info,
    "web_search": web_search,
}

_ALL_TOOL_DEFS = [TIMEDATE_TOOL_DEF, FETCH_TOOL_DEF, IPINFO_TOOL_DEF, WEB_SEARCH_TOOL_DEF]

# Comma-separated tool names to turn off, e.g. "web_search,fetch_url".
DISABLED_TOOLS = {name.strip() for name in os.environ.get("MCP_DISABLED_TOOLS", "").split(",") if name.strip()}

TOOLS = {name: fn for name, fn in _ALL_TOOLS.items() if name not in DISABLED_TOOLS}
TOOL_DEFS = [d for d in _ALL_TOOL_DEFS if d["name"] not in DISABLED_TOOLS]


class InvokeRequest(BaseModel):
    arguments: dict = {}


@app.get("/tools")
async def list_tools() -> list[dict]:
    return TOOL_DEFS


@app.post("/tools/{name}")
async def invoke_tool(name: str, payload: InvokeRequest) -> dict:
    tool = TOOLS.get(name)
    if tool is None:
        raise HTTPException(status_code=404, detail=f"Unknown tool: {name}")

    try:
        result = tool(**payload.arguments)
        if inspect.isawaitable(result):
            result = await result
    except (ValueError, FetchError, IpInfoError, WebSearchError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except TypeError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    return {"result": result}
