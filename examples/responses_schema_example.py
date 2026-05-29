from __future__ import annotations

from local_agentic_search.tool_schemas import responses_tool_schemas

if __name__ == "__main__":
    for schema in responses_tool_schemas():
        print(schema["name"], "-", schema["description"])
