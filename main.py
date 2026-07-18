from __future__ import annotations

import inspect

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

TOOLS = {
    "get_current_time": get_current_time,
    "fetch_url": fetch_url,
    "get_ip_info": get_ip_info,
    "web_search": web_search,
}

TOOL_DEFS = [TIMEDATE_TOOL_DEF, FETCH_TOOL_DEF, IPINFO_TOOL_DEF, WEB_SEARCH_TOOL_DEF]


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
