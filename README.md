* What the book agent actually does

In one sentence: the book agent is a question-answering system over AI Engineering book that accepts natural-language questions, decides whether they need retrieval, searches the book, and produces grounded answers — accessible via HTTP API, MCP protocol, or direct Python.

In one paragraph: you extract text from a PDF book, chunk it, index it with BM25, then wrap that in a LangGraph agent that classifies each incoming question, routes it through appropriate processing (search / analyze / respond), and returns an answer grounded in the book's actual content. The whole thing runs behind a FastAPI streaming endpoint, packaged as a Docker container, with conversation state persisted across turns via SQLite checkpointing. The same tools that power the LangGraph agent are also exposed as an MCP server, letting external clients (Claude Desktop, a separate LangGraph agent) invoke them through a standards-compliant protocol.

* Architecture layer

Layer 1 -- the knowledge base
src/knowledge_base.py
takes a PDF, extracts text with PyMuPDF, splits into 1485 overlapping chunks(chunk size = 1000, overlap=150, sliding window), and builds a BM25 index over the chunks. chunks and index persist to data/index/bm25.pkl for fast reload. This layer does not interact with LLM, just retrieval infrastructure. 

Layer 2 -- the tools
src/tools.py
wraps the knowledge base into four LLM-callable functions with Anthropic tool schemas: search_book, list_topics, summarize_passage, extract_key_terms. Each has JSON schema declaring its arguments so an LLM can decide when to call it and with what parameters.

Layer 3 -- the agent(LangGraph)
src/routed_agent.py
this is where control flow lives. 
A stategraph with four nodes: clasify(Claude reads the question and returns one of the tool), do _search(retireves 5 chunks from the knowledge base), do_analyze(optionally summarizes or extracts key terms from search results), respond(claude generates the final answer)
Two conditional edges route based on the classification: chat skips search entirely, search_only skips analysis, search_analyze goes through everything. State is persisted per-thread via SqliteSaver checkpointing, so multi-turn conversations work — same thread_id continues context, different thread_id starts fresh.

layer 4 -- the API(FastAPI)
src/api.py
How the outside world talks to code over HTTP. It is like the front counter of a restaurant where customers order food. Testing on code editor is like order from kitchen. How does a web browser or mobile app talk to my agent?
POST /query — synchronous, returns the whole answer at the end.
POST /query/stream — streams NDJSON stage transitions (classified → searching → analyzed → final) as the agent progresses. Uses StreamingResponse from FastAPI/Starlette.


Layer 5 -- the container(Docker)
Dockerfile + docker-compose.yml
How code and its enrionment are packaged into a portable box that runs indentically anywhere. It is like a food truck that brings the whole kitchen to other location. How do I ship this so it runs anywhere?
Multi-stage build separates dependency installation with uv form runtime image. Runs as non-root user. The .dockerignore file is critical -- anything referenced by pyproject.toml metadata or loaded at import time must not be excluded. Secrets injected at runtime vis --env-file .env. Docker Compose consolidates the run command into docker-compose up

Layer 6 -- the MCP server
src/mcp_server.py
How AI agents discover and call the tools using a standardized protocol. Like USB port. How do LLM applications discover and use my tools without custom integration?
Exposes search_book and list_topics via the Model Context Protocol using FastMCP. Runs as a subprocess spoken to over stdio JSON-RPC. LangGraph agent using langchain-mcp-adapters (in src/langgraph_mcp_demo.py).



User question
    ↓
[Layer 4] FastAPI /query/stream endpoint receives POST
    ↓
[Layer 3] run_routed_agent(question, thread_id) invoked
    ↓
[Layer 3] Checkpointer loads any prior conversation state for this thread
    ↓
[Layer 3] classify node — Claude Haiku classifies (uses recent history if present)
    ↓
[Layer 3] Conditional edge routes based on classification
    ↓
[Layer 2 → Layer 1] If search: do_search calls search_book(), which hits KnowledgeBase.search()
    ↓
[Layer 3] (Optional) do_analyze summarizes or extracts terms
    ↓
[Layer 3] respond node — Claude Haiku synthesizes final answer with full conversation history + retrieved context
    ↓
[Layer 3] Checkpointer persists new state
    ↓
[Layer 4] Answer streamed back as final NDJSON line
    ↓
User sees grounded answer

The MCP path is parallel to Layer 4 rather than downstream of it — MCP clients bypass FastAPI entirely and talk directly to src/mcp_server.py, which reaches into Layer 2 → Layer 1.

