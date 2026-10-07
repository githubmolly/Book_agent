"""
Routed Book Agent — classifies query type, then routes through 
different subgraphs based on that classification.

Demonstrates conditional edges as a control-flow primitive.
"""


from dotenv import load_dotenv
load_dotenv()  # MUST come before importing routed_agent



import json
import sqlite3
from pathlib import Path

from typing import TypedDict, Annotated, Literal
from operator import add

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langgraph.graph import StateGraph, END


from src.tools import search_book, summarize_passage, extract_key_terms


from langgraph.checkpoint.sqlite import SqliteSaver

# ==================================================================
# State — richer than the raw graph because we track the route
# ==================================================================
class RoutedState(TypedDict):
    messages: Annotated[list, add]
    query_type: str       # "chat" | "search_only" | "search_analyze"
    analysis_type: str    # "summarize" | "extract_terms" | ""
    search_results: str   # cached retrieval output


# Two LLMs — could be different models entirely
_classifier_llm = ChatAnthropic(
    model="claude-haiku-4-5-20251001",
    temperature=0,
    max_tokens=200,
)

_answer_llm = ChatAnthropic(
    model="claude-haiku-4-5-20251001",
    temperature=0,
    max_tokens=2048,
)


# ==================================================================
# Node 1: Classify the query
# ==================================================================
CLASSIFIER_PROMPT = """Classify the user's question into one of three types:

- "chat": Casual conversation or greeting. No book search needed.
- "search_only": Factual question that requires looking up book content.
- "search_analyze": Requires searching AND then summarizing or extracting terms.

If the type is "search_analyze", also specify what analysis:
- "summarize": User wants a summary, overview, or bullet points
- "extract_terms": User wants key terms, definitions, or glossary

Output ONLY a JSON object like:
{"query_type": "search_analyze", "analysis_type": "summarize"}

Question: """


def classify_query(state: RoutedState) -> dict:
    """Classify, using recent conversation history for context."""
    # Build a short transcript of the recent conversation
    recent = state["messages"][-6:]  # last 3 exchanges max
    transcript = "\n".join(
        f"{'User' if isinstance(m, HumanMessage) else 'Assistant'}: {m.content}"
        for m in recent
    )

    prompt = (
        CLASSIFIER_PROMPT
        + "\n\nRecent conversation:\n"
        + transcript
        + "\n\nClassify the LAST user message, considering the context above."
    )
    response = _classifier_llm.invoke([HumanMessage(content=prompt)])

    # ... rest of the parsing logic unchanged
    try:
        text = response.content.strip()
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        result = json.loads(text.strip())
        query_type = result.get("query_type", "search_only")
        analysis_type = result.get("analysis_type", "")
    except (json.JSONDecodeError, IndexError):
        query_type = "search_only"
        analysis_type = ""

    print(f"→ Classified as: {query_type} ({analysis_type})")
    return {"query_type": query_type, "analysis_type": analysis_type}
# ==================================================================
# Node 2: Do the search
# ==================================================================
def do_search(state: RoutedState) -> dict:
    """Retrieve chunks, using recent context to inform the query."""
    # Combine the last few messages into search-relevant context
    recent = state["messages"][-4:]
    query_context = " ".join(m.content for m in recent if hasattr(m, "content"))
    results = search_book(query_context, top_k=5)
    print(f"→ Search returned {len(results)} chars")
    return {"search_results": results}
# ==================================================================
# Node 3: Analyze search results (summarize or extract terms)
# ==================================================================
def do_analyze(state: RoutedState) -> dict:
    """Route to the correct analyzer based on state.analysis_type."""
    text = state["search_results"]
    analysis_type = state["analysis_type"]

    if analysis_type == "summarize":
        analyzed = summarize_passage(text)
    elif analysis_type == "extract_terms":
        analyzed = extract_key_terms(text)
    else:
        analyzed = text

    print(f"→ Analysis ({analysis_type}): {len(analyzed)} chars")
    return {"search_results": analyzed}


# ==================================================================
# Node 4: Respond
# ==================================================================
# def respond(state: RoutedState) -> dict:
#     """Final answer to the user based on the accumulated state."""
#     user_msg = state["messages"][-1].content
#     query_type = state["query_type"]

#     if query_type == "chat":
#         response = _answer_llm.invoke([
#             SystemMessage(content="You are a helpful assistant. Respond conversationally."),
#             HumanMessage(content=user_msg),
#         ])
#     else:
#         context = state.get("search_results", "")
#         response = _answer_llm.invoke([
#             SystemMessage(content=(
#                 "You are answering a question about AI engineering. "
#                 "Use the provided context to answer. Cite page numbers when possible."
#             )),
#             HumanMessage(content=f"Context from book:\n\n{context}\n\nQuestion: {user_msg}"),
#         ])

#     return {"messages": [response]}


def respond(state: RoutedState) -> dict:
    """Final answer using the full conversation history."""
    query_type = state["query_type"]

    if query_type == "chat":
        system = SystemMessage(content="You are a helpful assistant. Respond conversationally.")
    else:
        context = state.get("search_results", "")
        system = SystemMessage(content=(
            "You are answering questions about AI engineering. "
            "Use the provided context to answer. Cite page numbers when possible.\n\n"
            f"Context from book:\n\n{context}"
        ))

    # Pass system prompt + full message history to the LLM
    response = _answer_llm.invoke([system] + state["messages"])

    return {"messages": [response]}


# ==================================================================
# Conditional edges — the payoff
# ==================================================================
def route_after_classify(state: RoutedState) -> Literal["do_search", "respond"]:
    """First conditional edge: chat skips search entirely."""
    if state["query_type"] == "chat":
        return "respond"
    return "do_search"


def route_after_search(state: RoutedState) -> Literal["do_analyze", "respond"]:
    """Second conditional edge: only search_analyze goes through analysis."""
    if state["query_type"] == "search_analyze":
        return "do_analyze"
    return "respond"



# ==================================================================
# Build the graph ONCE at module load, with a persistent checkpointer
# ==================================================================
def _create_checkpointer() -> SqliteSaver:
    """
    Create a SqliteSaver backed by a file next to the project data dir.

    check_same_thread=False lets the connection be shared across threads,
    which FastAPI's threadpool needs.
    """
    db_path = Path(__file__).resolve().parent.parent / "data" / "checkpoints.db"
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path), check_same_thread=False)
    return SqliteSaver(conn)


# Module-level: built once, reused across all invocations
_checkpointer = _create_checkpointer()

# ==================================================================
# Build the graph
# ==================================================================


def build_routed_graph(checkpointer=None, interrupt_before=None):
    """
    Build and compile the routed graph.

    Args:
        checkpointer: optional checkpointer (SqliteSaver, MemorySaver, or None)
        interrupt_before: optional list of node names to pause before
    """
    graph = StateGraph(RoutedState)

    graph.add_node("classify", classify_query)
    graph.add_node("do_search", do_search)
    graph.add_node("do_analyze", do_analyze)
    graph.add_node("respond", respond)

    graph.set_entry_point("classify")

    graph.add_conditional_edges(
        "classify",
        route_after_classify,
        {"do_search": "do_search", "respond": "respond"},
    )
    graph.add_conditional_edges(
        "do_search",
        route_after_search,
        {"do_analyze": "do_analyze", "respond": "respond"},
    )
    graph.add_edge("do_analyze", "respond")
    graph.add_edge("respond", END)

    return graph.compile(
        checkpointer=checkpointer,
        interrupt_before=interrupt_before or [],
    )


# Module-level: compile once with the persistent checkpointer
_graph = build_routed_graph(checkpointer=_checkpointer)

def run_routed_agent(user_message: str, thread_id: str = "default") -> dict:
    """
    Run the routed agent on a single message.

    Args:
        user_message: The user's question or utterance.
        thread_id: Conversation identifier. Same thread_id preserves state
                   across calls; different thread_id starts fresh.

    Returns:
        Same shape as before: {final_answer, query_type, analysis_type}
    """
    initial_state = {
        "messages": [HumanMessage(content=user_message)],
        "query_type": "",
        "analysis_type": "",
        "search_results": "",
    }
    config = {"configurable": {"thread_id": thread_id}}

    result = _graph.invoke(initial_state, config=config)

    final = ""
    for msg in reversed(result["messages"]):
        if isinstance(msg, AIMessage) and msg.content:
            final = msg.content
            break

    return {
        "final_answer": final,
        "query_type": result["query_type"],
        "analysis_type": result["analysis_type"],
    }