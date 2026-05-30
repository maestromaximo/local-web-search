# Operations And Troubleshooting

Use this reference for Docker, SearXNG, Crawl4AI, cache, CLI, and HTTP API
questions.

## Health Check

Run:

```bash
local-web-search doctor
```

The command prints the active SearXNG URL and cache path. If `ok` is false,
start the bundled service or point the package at an existing SearXNG instance.

## Bundled SearXNG

From a cloned repo:

```bash
docker compose up -d searxng
local-web-search doctor
```

From Python, the Agents SDK helper can start the packaged compose service:

```python
web_search, web_fetch = build_agent_tools(build_container_if_missing=True)
```

If Docker is not managed by the helper, the package prints a warning once per
process. Suppress only when the application deliberately manages SearXNG:

```python
web_search, web_fetch = build_agent_tools(suppress_docker_warning=True)
```

## Existing SearXNG

Use `SEARXNG_BASE_URL`:

```bash
export SEARXNG_BASE_URL="http://127.0.0.1:8888"
```

Or pass a port to the tool factory:

```python
web_search, web_fetch = build_agent_tools(searxng_port=8899)
```

## CLI Commands

```text
local-web-search doctor
local-web-search search "query" --max-results 5
local-web-search fetch res_... --max-chars 4000
local-web-search fetch https://example.com --max-chars 4000
local-web-search serve --host 127.0.0.1 --port 8099
local-web-search skill load
```

`skill load` installs this skill into the current repo at
`.agents/skills/local-web-search`. Use:

```bash
local-web-search skill load --project-dir path/to/repo
local-web-search skill load --force
```

## Environment Variables

- `SEARXNG_BASE_URL`: full SearXNG base URL.
- `LOCAL_WEB_SEARCH_CACHE`: SQLite cache path.
- `LOCAL_WEB_SEARCH_RESULTS_TTL_SECONDS`: search-result TTL.
- `LOCAL_WEB_SEARCH_PAGES_TTL_SECONDS`: fetched-page TTL.
- `LOCAL_WEB_SEARCH_FETCH_CHARS`: default fetch slice size.
- `LOCAL_WEB_SEARCH_MAX_FETCH_CHARS`: hard fetch slice maximum.
- `LOCAL_WEB_SEARCH_CRAWL_TIMEOUT_MS`: Crawl4AI timeout.
- `LOCAL_WEB_SEARCH_DOCKER_COMPOSE_FILE`: compose file override.
- `LOCAL_WEB_SEARCH_DOCKER_CONTAINER`: SearXNG container name override.
- `LOCAL_WEB_SEARCH_SEARXNG_HOST`: host used when `SEARXNG_BASE_URL` is unset.
- `LOCAL_WEB_SEARCH_SEARXNG_PORT`: host port used when `SEARXNG_BASE_URL` is unset.
- `LOCAL_WEB_SEARCH_SEARXNG_BIND`: Docker bind address for bundled SearXNG.

## Cache Behavior

Search results and fetched pages are cached in SQLite. Stable `result_id`
values depend on the search parameters and result position. Use `refresh=True`
or `--refresh` when a task needs fresh search results or a newly crawled page.

## Crawl4AI Issues

If page fetches fail because browser dependencies are missing, run the setup
step required by Crawl4AI in the active environment:

```bash
crawl4ai-setup
```

Keep fetch slices bounded. Large pages should be read with `start` and
`max_chars` rather than fetched into the model all at once.
