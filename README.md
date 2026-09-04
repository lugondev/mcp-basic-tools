# mcp-basic-tools

Remote MCP tool server for the [LUGO gateway](https://github.com/lugondev/lugo-gateway).

Exposes a handful of general-purpose tools over the gateway's simplified MCP REST
contract, so a conversation profile can call them without anything extra running
in-process.

## Tools

| Tool | What it does |
| --- | --- |
| `timedate` | Current date and time |
| `fetch` | Fetch a URL and return readable text |
| `ipinfo` | Look up information about an IP address |
| `web_search` | Web search |

`web_search` uses the `ddgs` metasearch backend when the `search` extra is installed.
Without it the tool degrades to the DuckDuckGo Instant Answer API, which only returns
entity abstracts.

## Contract

Two endpoints — that is the whole surface:

```
GET  /tools          -> the tool definitions
POST /tools/{name}   -> call one, JSON body in, JSON result out
```

## Run it

```bash
pip install -e ".[search,dev]"
uvicorn main:app --host 0.0.0.0 --port 8020
```

Or with Docker:

```bash
docker build -t mcp-basic-tools .
docker run -p 8020:8020 mcp-basic-tools
```

Then point a gateway profile's MCP config at `http://<host>:8020`.

## Test

```bash
pytest -q
```

---

## Part of LUGO

**LUGO** is a self-hosted AI companion platform — models supply the intelligence, LUGO
supplies the experience: one assistant that talks, remembers and acts across the browser,
ESP32 boards and a Raspberry Pi.

This repository is one piece of it. Every client and service talks to the gateway:

| Repo | Role |
| --- | --- |
| [lugo-gateway](https://github.com/lugondev/lugo-gateway) | The hub — STT/TTS/LLM engines, auth, device pairing, MCP tools, per-user chat memory. Everything below talks to this. |
| [lugo-web-client](https://github.com/lugondev/lugo-web-client) | React + TypeScript web client: talk, devices, history, tools. |
| [esp32-assistant](https://github.com/lugondev/esp32-assistant) | ESP-IDF firmware for ESP32-S3 / ESP32-C3 — a hands-free voice terminal. |
| [rpi-assistant](https://github.com/lugondev/rpi-assistant) | Raspberry Pi voice client (mic capture, Opus duplex, systemd unit). |
| [knowledge-api](https://github.com/lugondev/knowledge-api) | **kbase** — RAG knowledge base: documents in, retrievable chunks out. |
| [router-memory-services](https://github.com/lugondev/router-memory-services) | **memgw** — one API in front of any AI memory provider (Mem0, Zep, pgvector). |
| **mcp-basic-tools** &nbsp;&larr; you are here | Remote MCP tool server (timedate, fetch, ipinfo, web search). |
| [livehost-api](https://github.com/lugondev/livehost-api) | TikTok Live AI co-host, an out-of-process gateway plugin. |
| [voiceprint-api](https://github.com/lugondev/voiceprint-api) | Speaker recognition (3D-Speaker), forked from [xinnan-tech/voiceprint-api](https://github.com/xinnan-tech/voiceprint-api). |
| [lugo-landing](https://github.com/lugondev/lugo-landing) | Marketing landing page for the platform, bilingual (Tiếng Việt / English). |
