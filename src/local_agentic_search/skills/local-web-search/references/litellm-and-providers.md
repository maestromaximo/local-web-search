# LiteLLM And Provider Patterns

Use this reference when an OpenAI Agents SDK project uses LiteLLM, Any-LLM, a
custom OpenAI-compatible endpoint, or another non-default model provider.

## Main Rule

Local Web Search tools are local `function_tool`s. They do not require the
model provider to support hosted web search. Keep the tools the same and change
only the model/provider configuration.

```python
from agents import Agent, Runner
from agents.extensions.models.litellm_model import LitellmModel
from local_agentic_search.agent_tools import build_agent_tools

web_search, web_fetch = build_agent_tools(build_container_if_missing=True)

agent = Agent(
    name="Research assistant",
    instructions=(
        "Use web_search for current web information. Search results are snippets. "
        "Call web_fetch with a result_id before relying on page details not present "
        "in a snippet."
    ),
    model=LitellmModel(model="openai/gpt-4.1-mini"),
    tools=[web_search, web_fetch],
)

result = Runner.run_sync(agent, "Find the latest release notes for SearXNG.")
print(result.final_output)
```

Install the LiteLLM adapter dependency:

```bash
pip install "openai-agents[litellm]"
```

When using this package's convenience extra plus LiteLLM:

```bash
pip install "local-web-search[agents]" "openai-agents[litellm]"
```

## Special Models

Use an explicit model on the `Agent`. Do not depend on the SDK fallback model
when quality, latency, cost, or provider behavior matters.

Provider-specific examples may require environment variables expected by that
provider or LiteLLM. Do not put API keys in code samples.

## Hosted Tool Caveat

Do not attach OpenAI hosted tools such as hosted web search to a LiteLLM-backed
agent unless the exact backend supports them. Local Web Search avoids this by
running search and fetch as application-owned function tools.

## Validation Checklist

Validate the exact backend before treating the integration as production-ready:

- The model can call both tools with JSON arguments.
- The model respects the search-before-fetch instruction.
- Streaming runs still surface tool calls as expected.
- Usage accounting is present if the application depends on it.
- Tracing is disabled or configured correctly when no OpenAI tracing key is
  available.

## Run-Level Overrides

If a project uses run-level model overrides, keep the agent tools attached to
the agent and override the model through the SDK run configuration used by that
project. Re-run at least one search/fetch workflow after changing provider
routing.
