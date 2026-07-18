from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

TOOL_DEF = {
    "name": "get_current_time",
    "description": "Get the current date/time as an ISO 8601 string in the given timezone.",
    "inputSchema": {
        "type": "object",
        "properties": {
            "timezone": {
                "type": "string",
                "description": "IANA timezone name, e.g. 'Asia/Ho_Chi_Minh'. Defaults to UTC.",
                "default": "UTC",
            },
        },
        "required": [],
    },
}


def get_current_time(timezone: str = "UTC") -> str:
    try:
        tz = ZoneInfo(timezone)
    except ZoneInfoNotFoundError as exc:
        raise ValueError(f"Unknown timezone: {timezone}") from exc
    return datetime.now(tz).isoformat()
