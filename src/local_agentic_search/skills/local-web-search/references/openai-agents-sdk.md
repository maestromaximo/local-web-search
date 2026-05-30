# OpenAI Agents SDK Integration

Use this reference when the user wants Local Web Search inside an OpenAI Agents
SDK agent.

## Default Pattern

Install:

```bash
pip install "local-web-search[agents]"
```

Code:

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

`build_agent_tools()` returns two Agents SDK `function_tool` objects. The tool
functions are async internally, but they can be used from normal SDK runs.

## Tool Contract

`web_search` accepts:

- `query`: search query.
- `max_results`: 1 to 20, default 5.
- `page`: SearXNG page number, default 1.
- `language`: optional language code such as `en`.
- `categories`: optional comma-separated SearXNG categories.
- `engines`: optional comma-separated SearXNG engines.
- `time_range`: `day`, `month`, `year`, or `None`.
- `safesearch`: `0`, `1`, or `2`.
- `refresh`: bypass cached search results.

`web_search` returns compact results with stable `result_id` values and a
`full_text_command_text` hint.

`web_fetch` accepts:

- `result_id`: preferred stable ID returned by `web_search`.
- `url`: direct URL fallback when no `result_id` exists.
- `start`: character offset into fetched text.
- `max_chars`: bounded page-text slice size.
- `refresh`: bypass cached page text.

`web_fetch` returns `content`, slice offsets, `total_chars`, `has_more`, and a
`next_fetch_command_text` hint when more text is available.

## Agent Instructions

Add the search/fetch discipline to the agent's own instructions. A good base:

```text
Use web_search for current web information. Search results are snippets. Call
web_fetch with a result_id before relying on page details not present in a
snippet. Cite or preserve URLs from fetched results when source attribution is
needed.
```

For research-heavy agents, add:

```text
Prefer narrow searches. Fetch only the results needed to answer the question.
When web_fetch returns has_more, request the next slice only if the missing text
is likely relevant.
```

## Existing Service Injection

When the application already owns configuration, cache, or test doubles, inject
a service:

```python
from local_agentic_search import LocalSearchConfig, LocalSearchService
from local_agentic_search.agent_tools import build_agent_tools

service = LocalSearchService(LocalSearchConfig(searxng_base_url="http://127.0.0.1:8899"))
web_search, web_fetch = build_agent_tools(service=service)
```

Do not pass both `service` and SearXNG connection options.

## Port Selection

If port `8888` is busy:

```python
web_search, web_fetch = build_agent_tools(
    build_container_if_missing=True,
    searxng_port=8899,
)
```

If Docker is managed outside Python, align the environment:

```bash
LOCAL_WEB_SEARCH_SEARXNG_PORT=8899 docker compose up -d searxng
```

## Custom Responses API Loops

Use `responses_tool_schemas()` only when not using the Agents SDK helper:

```python
from local_agentic_search.tool_schemas import responses_tool_schemas

tools = responses_tool_schemas()
```

The app must still execute `web_search` and `web_fetch` locally and send their
JSON outputs back as function-call outputs.
