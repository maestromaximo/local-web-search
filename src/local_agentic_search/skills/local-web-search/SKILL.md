---
name: local-web-search
description: Add, configure, or troubleshoot the local-web-search Python package in agentic projects. Use when working with local web search, SearXNG, Crawl4AI, web_search/web_fetch tools, OpenAI Agents SDK Agent and Runner integrations, LiteLLM or non-OpenAI model adapters, Responses API function schemas, or repo-local .agents skill installation.
---

# Local Web Search

## Overview

Use this skill to wire Local Web Search into an agent project as two local tools:
`web_search` for compact SearXNG snippets and `web_fetch` for bounded Crawl4AI
page text. Prefer the package's built-in OpenAI Agents SDK helper unless the
project already has a custom tool loop.

## Quick Path

1. Install the package and the integration dependency:

```bash
pip install "local-web-search[agents]"
```

2. Keep Docker Engine running. Let the tool factory start the bundled SearXNG
   container when the app does not manage one itself:

```python
from agents import Agent, Runner
from local_agentic_search.agent_tools import build_agent_tools

web_search, web_fetch = build_agent_tools(build_container_if_missing=True)

agent = Agent(
    name="Research assistant",
    instructions=(
        "Use web_search for current web information. Search results are snippets. "
        "Call web_fetch with a result_id before relying on page details not present "
        "in a snippet."
    ),
    model="gpt-4.1-mini",
    tools=[web_search, web_fetch],
)

result = Runner.run_sync(agent, "Find recent information about SearXNG.")
print(result.final_output)
```

3. Set `model` explicitly. For LiteLLM or another provider adapter, keep these
   local function tools in `tools=[web_search, web_fetch]` and swap only the
   model/provider configuration.

## Implementation Rules

- Use `build_agent_tools()` for OpenAI Agents SDK projects. It returns two
  SDK `function_tool` objects and hides the service, cache, SearXNG, and
  Crawl4AI wiring.
- Do not substitute OpenAI hosted `WebSearchTool` when the user asks for this
  package. Local Web Search is deliberately local and uses SearXNG plus
  Crawl4AI in the user's environment.
- In prompts, tell the agent that search results are snippets and that it must
  call `web_fetch` before relying on details not present in a snippet.
- Prefer `build_container_if_missing=True` for examples and quick starts. Use
  manual Docker startup or `searxng_base_url` when the host application owns
  infrastructure.
- Use `responses_tool_schemas()` only for custom Responses API loops where the
  application executes tool calls itself.
- Keep web fetch slices bounded. Increase `max_chars` only when the task needs
  more page text, and continue with `next_fetch_command` when `has_more` is
  true.

## References

- Read `references/openai-agents-sdk.md` when adding or changing an OpenAI
  Agents SDK integration.
- Read `references/litellm-and-providers.md` when the project uses LiteLLM,
  Any-LLM, a custom OpenAI-compatible endpoint, or a special model.
- Read `references/operations.md` when troubleshooting Docker, ports, SearXNG,
  Crawl4AI, cache behavior, or CLI/API usage.

## Common Checks

- Confirm Python is 3.10 or newer.
- Confirm `openai-agents` is installed for `build_agent_tools()`.
- Confirm Docker Engine is running unless the project points at an existing
  SearXNG instance.
- Run `local-web-search doctor` when SearXNG connectivity is uncertain.
- If the user wants this skill installed into a repo, run
  `local-web-search skill load` from that repo root. Use `--force` to update an
  existing `.agents/skills/local-web-search` copy.
