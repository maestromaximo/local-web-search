# Local Web Search

Local Web Search is an agent-friendly local web search backend. It gives agents
two simple tools:

- `web_search` asks a local SearXNG instance for search results and returns
  compact snippets.
- `web_fetch` uses Crawl4AI to fetch full page text only when the agent asks for
  a specific result.

SQLite caching keeps result IDs and fetched page text stable across tool calls.
The tool names intentionally look like normal web tools, but all execution
happens in your local environment.

## Install

```powershell
python -m pip install local-web-search
```

Install optional integrations as needed:

```powershell
python -m pip install "local-web-search[server]"
python -m pip install "local-web-search[agents]"
python -m pip install "local-web-search[server,agents]"
```

The Python import package is `local_agentic_search`:

```python
from local_agentic_search import LocalSearchService
```

## Quick Start

Clone the repository if you want the bundled Docker Compose SearXNG setup:

```powershell
git clone https://github.com/maestromaximo/local-web-search.git
cd local-web-search
docker compose up -d searxng
python -m pip install -e ".[server,agents,dev]"
python -m crawl4ai-setup
```

Check that SearXNG is reachable:

```powershell
local-web-search doctor
```

Search from the CLI:

```powershell
local-web-search search "OpenAI Agents SDK function tools" --max-results 5
```

Fetch full text for a result returned by search:

```powershell
local-web-search fetch res_... --max-chars 4000
```

Fetch a URL directly:

```powershell
local-web-search fetch https://example.com --max-chars 4000
```

Run the HTTP API:

```powershell
local-web-search serve --host 127.0.0.1 --port 8099
```

## CLI

```text
local-web-search doctor
local-web-search search "query" [--max-results 5] [--language en]
local-web-search fetch res_... [--start 0] [--max-chars 4000]
local-web-search fetch https://example.com [--max-chars 4000]
local-web-search serve [--host 127.0.0.1] [--port 8099]
```

Run `local-web-search --help` or `local-web-search <command> --help` for the
full command reference.

## OpenAI Agents SDK Usage

```python
from agents import Agent, Runner
from local_agentic_search.agent_tools import build_agent_tools

web_search, web_fetch = build_agent_tools(build_container_if_missing=True)

agent = Agent(
    name="Research assistant",
    instructions=(
        "Use web_search when current web information is useful. Search results "
        "are snippets. Call web_fetch with a result_id before relying on page "
        "details not present in a snippet."
    ),
    model="gpt-4.1-mini",
    tools=[web_search, web_fetch],
)

result = Runner.run_sync(agent, "Find recent information about Crawl4AI.")
print(result.final_output)
```

By default, `build_agent_tools()` assumes Docker/SearXNG is already running and
prints a yellow console warning once per process. To let the tool factory start
SearXNG when the container is missing or stopped:

```python
web_search, web_fetch = build_agent_tools(build_container_if_missing=True)
```

To silence the warning while keeping startup manual:

```python
web_search, web_fetch = build_agent_tools(suppress_docker_warning=True)
```

## Responses API Tool Schemas

For direct OpenAI API tool loops, use:

```python
from local_agentic_search.tool_schemas import responses_tool_schemas

tools = responses_tool_schemas()
```

Your application still executes `web_search` and `web_fetch` locally and returns
their JSON outputs as function call outputs.

## HTTP API

Start the server with:

```powershell
local-web-search serve
```

Routes:

- `GET /health`
- `GET /search?q=...&max_results=5`
- `POST /search`
- `POST /fetch`
- `GET /openai/tools`

See `examples/http_client_example.py` for a minimal async HTTP client.

## Examples

- `examples/agents_sdk_example.py`: build OpenAI Agents SDK tools named
  `web_search` and `web_fetch`.
- `examples/http_client_example.py`: call the local HTTP API with `httpx`.
- `examples/responses_schema_example.py`: print the Responses API tool schemas.

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

`web_fetch` returns a page slice with `start`, `end`, `total_chars`, `has_more`,
and a `next_fetch_command` when more text is available.

## Configuration

Environment variables:

- `SEARXNG_BASE_URL`: defaults to `http://127.0.0.1:8888`
- `LOCAL_WEB_SEARCH_CACHE`: defaults to `.cache/local_agentic_search.sqlite3`
- `LOCAL_WEB_SEARCH_RESULTS_TTL_SECONDS`: defaults to `86400`
- `LOCAL_WEB_SEARCH_PAGES_TTL_SECONDS`: defaults to `604800`
- `LOCAL_WEB_SEARCH_FETCH_CHARS`: default fetch slice size, defaults to `4000`
- `LOCAL_WEB_SEARCH_MAX_FETCH_CHARS`: maximum fetch slice size, defaults to
  `20000`
- `LOCAL_WEB_SEARCH_CRAWL_TIMEOUT_MS`: Crawl4AI timeout, defaults to `45000`
- `LOCAL_WEB_SEARCH_DOCKER_COMPOSE_FILE`: optional compose file path
- `LOCAL_WEB_SEARCH_DOCKER_CONTAINER`: optional SearXNG container name

The automatic Docker path uses a fast `docker container inspect` check. If the
configured container is paused, it runs `docker container unpause`; if it is
missing or stopped, it runs `docker compose up -d --build searxng`.

## Publishing

The repository includes GitHub Actions for CI and PyPI publishing. The publish
workflow runs on every push to `main` and on manual dispatch. It checks PyPI for
existing `local-web-search` releases, bumps the patch version if necessary,
commits that version bump back to `main`, then builds and publishes with PyPI
Trusted Publishing.

To enable publishing, add a PyPI Trusted Publisher for:

- PyPI project: `local-web-search`
- Owner: `maestromaximo`
- Repository: `local-web-search`
- Workflow: `publish.yml`
- Environment: `pypi`

## License and Notices

Local Web Search is licensed under the Apache License 2.0.

SearXNG is a separate service licensed under the GNU Affero General Public
License v3.0 or later. Crawl4AI is licensed under the Apache License 2.0. See
`THIRD_PARTY_NOTICES.md` for details.

You are responsible for respecting robots.txt, website terms, copyright,
authentication boundaries, privacy rules, and rate limits when searching and
fetching public web content.
