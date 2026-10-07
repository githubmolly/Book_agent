# scripts/langgraph_mcp_demo.py
"""Demonstrate LangGraph consuming an MCP server as its tool source."""
import asyncio
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.prebuilt import create_react_agent  
from langchain_anthropic import ChatAnthropic
from dotenv import load_dotenv

load_dotenv()


async def main():
    # Connect to your MCP server — same server config as the inspector used
    client = MultiServerMCPClient(
        {
            "book-search": {
                "command": "E:\\P1_JOB\\AI projects\\book_agent\\.venv\\Scripts\\python.exe",
                "args": ["-m", "src.mcp_server"],
                "transport": "stdio",
            }
        }
    )

    # Discover what tools the MCP server exposes
    tools = await client.get_tools()          # ← now async, and awaited
    print(f"Loaded {len(tools)} tools from MCP:")
    for t in tools:
        print(f"  - {t.name}: {t.description[:80]}...")
    print()

    # Build a ReAct agent that uses these tools
    llm = ChatAnthropic(model="claude-haiku-4-5-20251001")
    agent = create_react_agent(llm, tools)

    # Ask a question that requires tool use
    result = await agent.ainvoke({
        "messages": [
            ("user", "Summarize what the AI Engineering book says about RAG evaluation."),
        ]
    })

    print("=== Answer ===")
    print(result["messages"][-1].content)

    # Bonus: print the tool invocations that happened
    print("\n=== Tool calls made ===")
    for msg in result["messages"]:
        if hasattr(msg, "tool_calls") and msg.tool_calls:
            for tc in msg.tool_calls:
                print(f"  - {tc['name']}({tc['args']})")

if __name__ == "__main__":
    asyncio.run(main())