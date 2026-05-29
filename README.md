# Local Agentic Search

Local Agentic Search is a small drop-in style web search backend for agents:

- `web_search` asks a local SearXNG instance for search results and returns compact snippets.
- `web_fetch` uses Crawl4AI to fetch full page text only when an agent asks for it.
- SQLite caching keeps result IDs and fetched page text stable across tool calls.

The tool names intentionally look like normal web tools. The implementation is local, but the agent sees a simple web search and web fetch surface.

## Quick Start

```powershell
docker compose up -d searxng
uv venv
.\.venv\Scripts\python -m pip install -e ".[server,agents,dev]"
.\.venv\Scripts\crawl4ai-setup
.\.venv\Scripts\python scripts\smoke_e2e.py --query "OpenAI Agents SDK function tools"
```

Search from the CLI:

```powershell
local-web-search search "OpenAI Agents SDK function tools" --max-results 5
```

Fetch full text for a result returned by search:

```powershell
local-web-search fetch res_... --max-chars 4000
```

Run the HTTP API:

```powershell
local-web-search serve --host 127.0.0.1 --port 8099
```

## Agent SDK Usage

```python
from agents import Agent, Runner
from local_agentic_search.agent_tools import build_agent_tools

web_search, web_fetch = build_agent_tools()

agent = Agent(
    name="Research assistant",
    instructions=(
        "Use web_search for current web results. Search returns snippets only. "
        "Call web_fetch with a result_id when full page text is needed."
    ),
    model="gpt-5.5",
    tools=[web_search, web_fetch],
)

result = Runner.run_sync(agent, "Find recent information about Crawl4AI.")
print(result.final_output)
```

## Responses API Tool Schemas

For direct OpenAI API tool loops, use:

```python
from local_agentic_search.tool_schemas import responses_tool_schemas

tools = responses_tool_schemas()
```

Your application still executes `web_search` and `web_fetch` locally and returns their JSON outputs as function call outputs.

## Search Result Shape

Each `web_search` result includes:

```json
{
  "result_id": "res_...",
  "search_id": "search_...",
  "position": 1,
  "title": "Page title",
  "url": "https://example.com",
  "snippet": "Compact SearXNG snippet",
  "site_links": [],
  "full_text_available": true,
  "full_text_command": {
    "tool": "web_fetch",
    "arguments": {
      "result_id": "res_...",
      "start": 0,
      "max_chars": 4000
    }
  },
  "full_text_command_text": "web_fetch(result_id='res_...', start=0, max_chars=4000)"
}
```

`web_fetch` returns a page slice with `start`, `end`, `total_chars`, `has_more`, and a `next_fetch_command` when more text is available.

## Configuration

Environment variables:

- `SEARXNG_BASE_URL`: defaults to `http://127.0.0.1:8888`
- `LOCAL_WEB_SEARCH_CACHE`: defaults to `.cache/local_agentic_search.sqlite3`
- `LOCAL_WEB_SEARCH_RESULTS_TTL_SECONDS`: defaults to `86400`
- `LOCAL_WEB_SEARCH_PAGES_TTL_SECONDS`: defaults to `604800`
- `LOCAL_WEB_SEARCH_FETCH_CHARS`: default fetch slice size, defaults to `4000`
- `LOCAL_WEB_SEARCH_MAX_FETCH_CHARS`: maximum fetch slice size, defaults to `20000`

## HTTP API

- `GET /health`
- `GET /search?q=...&max_results=5`
- `POST /search`
- `POST /fetch`
- `GET /openai/tools`

## Notes

SearXNG is responsible for search engine aggregation. Crawl4AI is responsible for rendering and extracting full page text. Respect robots.txt, site terms, authentication boundaries, and rate limits when using this against public sites.
