from __future__ import annotations

from agents import Agent, Runner

from local_agentic_search.agent_tools import build_agent_tools

web_search, web_fetch = build_agent_tools()

agent = Agent(
    name="Research assistant",
    instructions=(
        "Use web_search when current web information is useful. Search results are snippets. "
        "Call web_fetch with a result_id before relying on page details not present in a snippet."
    ),
    model="gpt-5.4-mini",
    tools=[web_search, web_fetch],
)

if __name__ == "__main__":
    result = Runner.run_sync(agent, "Find information about SearXNG JSON search results.")
    print(result.final_output)
