MCP Integration for book_agent

Status: MCP server built, validated end-to-end, and consumable from both the MCP Inspector and a LangGraph agent. Claude Desktop integration deferred.

What is MCP, and why is it in this project?

Model Context Protocol (MCP) is an open standard, for connecting LLMs to external tools and data sources. It defines one wire protocol (JSON-RPC over stdio or Server-Sent Events) that any client, and any server (Python, Node, Go, etc.) can implement.
MCP is "the USB-C of AI tooling" — one connector, many devices.

Why this project uses it: the book_agent project already has LangGraph-based tools accessible from a LangGraph agent. Exposing those same tools via MCP means:

Any MCP client (Claude Desktop, a future custom UI, another agent framework) can call them without a rewrite.
The Week 3 fraud investigator flagship will use MCP tools consumed by LangGraph — this integration is the miniature version of that pattern.

What was built
src/mcp_server.py — an MCP server exposing two tools
Built with FastMCP (high-level Python API in the MCP SDK 1.x line).

Both tools reuse the existing KnowledgeBase via the project's get_kb() lazy-init pattern in src/tools.py, meaning MCP consumers get the same BM25 retrieval as the internal LangGraph agent — one source of truth for search behavior.

Validation paths
MCP Inspector (Node-based, run via npx @modelcontextprotocol/inspector) — confirmed both tools register correctly, both invoke successfully with expected results.
LangGraph agent (scripts/langgraph_mcp_demo.py) — a ReAct agent consumes the MCP server as its tool source via langchain-mcp-adapters.


Prerequisites

Beyond the base book_agent project requirements:

Node.js LTS — required for the MCP Inspector (npx @modelcontextprotocol/inspector). Install: winget install OpenJS.NodeJS.LTS (Windows) or from https://nodejs.org.
MCP Python SDK, pinned to the 1.x stable line — the 2.x line was in beta as of mid-2026 with breaking API changes:  mcp[cli]>=1.28,<2

langchain-mcp-adapters — for consuming the MCP server from a LangGraph agent:  langchain-mcp-adapters


How to run
Standalone (verify the server imports and starts cleanly)
powershell
python -m src.mcp_server

With the MCP Inspector (interactive testing)
npx @modelcontextprotocol/inspector "E:\P1_JOB\AI projects\book_agent\.venv\Scripts\python.exe" -m src.mcp_server

Opens a browser tab (usually http://localhost:5173). The left pane shows connection status; under the Tools tab, both search_book and list_topics should appear with descriptions pulled from their docstrings.

Test list_topics first (no args, quickest sanity check). Then search_book with a real query like "RAG evaluation".


### MCP demo

(api-docs-rag) PS E:\P1_JOB\AI projects\book_agent> python -m src.langgraph_mcp_demo 
Loaded 2 tools from MCP:
  - search_book: Search the 'AI Engineering' book for passages relevant to a query....
  - list_topics: List major topics covered in the book....

E:\P1_JOB\AI projects\book_agent\src\langgraph_mcp_demo.py:33: LangGraphDeprecatedSinceV10: create_react_agent has been moved to `langchain.agents`. Please update your import to `from langchain.agents import create_agent`. Deprecated in LangGraph V1.0 to be removed in V2.0.
  agent = create_react_agent(llm, tools)
=== Answer ===
Based on the search results, here's what the AI Engineering book says about RAG evaluation:

## Key Points on RAG Evaluation:

**Factual Consistency as Core Evaluation Criteria:**
- Factual consistency is identified as a crucial evaluation criterion for RAG systems. The evaluation ensures that generated responses are factually consistent with the retrieved context.

**Retrieval Metrics:**
The book discusses two main metrics for evaluating the retriever component:

1. **Context Precision**: Measures what percentage of retrieved documents are actually relevant to the query. This is simpler to compute since you only need to compare retrieved documents to the query, which can be done by an AI judge.

2. **Context Recall**: Measures what percentage of all relevant documents in your database are successfully retrieved. This is more complex to compute because you need to annotate the relevance of all documents in your database.

**Evaluation Set Creation:**
- To compute these metrics, you need to curate an evaluation set with test queries and documents
- For each test query, you annotate each document as relevant or not relevant
- Annotations can be done either by humans or AI judges

**Production Considerations:**
- The book notes that in production, some RAG frameworks only support context precision (the simpler metric) rather than context recall, due to the computational complexity of needing to annotate all documents in the database.

**Broader Context:**
The book emphasizes that before implementing any RAG optimization steps, you should define your evaluation criteria and design your evaluation pipeline systematically.

=== Tool calls made ===
  - search_book({'query': 'RAG evaluation', 'top_k': 5})




The end-to-end trace as a diagram.

Question (natural language)
    ↓
LangChain agent (create_agent)
    ↓  [decides to invoke tool]
langchain-mcp-adapters (converts MCP tool → LangChain tool)
    ↓  [JSON-RPC over stdio]
MCP server subprocess (src/mcp_server.py)
    ↓  [calls get_kb().search()]
KnowledgeBase (BM25 over PDF chunks)
    ↓  [returns 5 passages]
Back up through all layers
    ↓
LLM synthesizes grounded answer