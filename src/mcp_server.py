# src/mcp_server.py
"""MCP server exposing book_agent tools to any MCP client (Claude Desktop, etc.).

Run standalone with:  python -m src.mcp_server
Or via Claude Desktop config (see notes below).
"""
# src/mcp_server.py — fallback if FastMCP unavailable
from dotenv import load_dotenv
load_dotenv()

import asyncio
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

from src.tools import get_kb

app = Server("book-search-server")


@app.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="search_book",
            description="Search the 'AI Engineering' book for passages relevant to a query.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "top_k": {"type": "integer", "default": 5},
                },
                "required": ["query"],
            },
        ),
        Tool(
            name="list_topics",
            description="List major topics covered in the book.",
            inputSchema={"type": "object", "properties": {}},
        ),
    ]


@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    kb = get_kb()
    if name == "search_book":
        results = kb.search(arguments["query"], top_k=arguments.get("top_k", 5))
        text = "\n\n---\n\n".join(
            f"Passage {i+1} (score={r['score']:.2f}):\n{r['text']}"
            for i, r in enumerate(results)
        )
        return [TextContent(type="text", text=text or "No results found.")]
    elif name == "list_topics":
        topics = getattr(kb, "list_topics", lambda: ["RAG", "Fine-tuning", "Evaluation", "Agents"])()
        text = "\n".join(f"- {t}" for t in topics)
        return [TextContent(type="text", text=text)]
    else:
        return [TextContent(type="text", text=f"Unknown tool: {name}")]


async def main():
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())