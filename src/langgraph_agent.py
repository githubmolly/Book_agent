"""
LangGraph rebuild of the Book Agent.

Same 4 tools, same system prompt, same expected behavior. The point 
is to see what the framework adds (and what it hides).
"""
import json
from typing import TypedDict, Annotated
from operator import add

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage, SystemMessage
from langgraph.graph import StateGraph, END

from src.tools import (
    SEARCH_BOOK_TOOL, LIST_TOPICS_TOOL,
    SUMMARIZE_PASSAGE_TOOL, EXTRACT_KEY_TERMS_TOOL,
    search_book, list_topics, summarize_passage, extract_key_terms,
)


# ==================================================================
# State — shared object nodes read and write
# ==================================================================
class AgentState(TypedDict):
    """
    The messages field uses the `add` reducer — new messages append 
    rather than replace. This is how state accumulates across turns.
    """
    messages: Annotated[list, add]


# ==================================================================
# Tool registry (same pattern as your raw agent)
# ==================================================================
TOOL_REGISTRY = {
    "search_book": search_book,
    "list_topics": list_topics,
    "summarize_passage": summarize_passage,
    "extract_key_terms": extract_key_terms,
}


# ==================================================================
# LLM setup — bind tools so the model knows about them
# ==================================================================
_llm_with_tools = ChatAnthropic(
    model="claude-haiku-4-5-20251001",
    temperature=0,
    max_tokens=2048,
).bind_tools([
    # LangChain accepts Anthropic-format tool dicts directly
    SEARCH_BOOK_TOOL,
    LIST_TOPICS_TOOL,
    SUMMARIZE_PASSAGE_TOOL,
    EXTRACT_KEY_TERMS_TOOL,
])


SYSTEM_PROMPT = (
    "You are a helpful assistant answering questions about AI engineering. "
    "You have access to search and analysis tools over the book 'AI Engineering'. "
    "Guidelines:\n"
    "- For factual questions: call search_book first, then answer.\n"
    "- For summary requests: call search_book, then summarize_passage.\n"
    "- For terminology questions: call search_book, then extract_key_terms.\n"
    "- For 'what does this book cover' questions: call list_topics.\n"
    "- For casual conversation: respond directly, no tools.\n"
    "When citing content, mention page numbers."
)


# ==================================================================
# Node 1: Call the model
# ==================================================================
def call_model(state: AgentState) -> dict:
    """Send state.messages to Claude. Return the model's response."""
    response = _llm_with_tools.invoke(state["messages"])
    # Return format: dict with keys matching AgentState fields
    return {"messages": [response]}


# ==================================================================
# Node 2: Execute any tool calls in the last message
# ==================================================================
def call_tools(state: AgentState) -> dict:
    """Execute every tool_call in the most recent AIMessage."""
    last_message = state["messages"][-1]
    tool_messages = []

    for tool_call in last_message.tool_calls:
        name = tool_call["name"]
        args = tool_call["args"]
        tool_id = tool_call["id"]

        # Same registry-based dispatch as your raw agent
        if name in TOOL_REGISTRY:
            try:
                result = TOOL_REGISTRY[name](**args)
            except Exception as e:
                result = json.dumps({"error": "Tool execution failed", "message": str(e)})
        else:
            result = json.dumps({"error": "Unknown tool", "message": f"Tool '{name}' does not exist"})

        tool_messages.append(ToolMessage(content=str(result), tool_call_id=tool_id))

    return {"messages": tool_messages}


# ==================================================================
# Conditional edge: after the model responds, do we loop or stop?
# ==================================================================
def should_continue(state: AgentState) -> str:
    """
    Check the last message. If it has tool_calls, route to 'tools'.
    Otherwise, we're done — route to END.
    """
    last_message = state["messages"][-1]
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        return "tools"
    return END


# ==================================================================
# Build the graph
# ==================================================================
def build_graph():
    """Assemble nodes + edges into a runnable graph."""
    graph = StateGraph(AgentState)

    # Register nodes
    graph.add_node("agent", call_model)
    graph.add_node("tools", call_tools)

    # Entry point
    graph.set_entry_point("agent")

    # From "agent", conditionally go to "tools" or END
    graph.add_conditional_edges(
        "agent",
        should_continue,
        {"tools": "tools", END: END},
    )

    # After "tools" runs, always go back to "agent"
    graph.add_edge("tools", "agent")

    return graph.compile()


# ==================================================================
# Public interface — mirrors run_agent() from src/agent.py
# ==================================================================
def run_langgraph_agent(user_message: str, verbose: bool = True) -> dict:
    """Run the graph. Return dict with final_answer + tool_calls trace."""
    graph = build_graph()

    initial_state = {
        "messages": [
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=user_message),
        ]
    }

    result = graph.invoke(initial_state)

    # Extract tool call trace from the message history
    tool_calls = []
    for msg in result["messages"]:
        if hasattr(msg, "tool_calls") and msg.tool_calls:
            for tc in msg.tool_calls:
                tool_calls.append({"name": tc["name"], "input": tc["args"]})

    # Final answer is the last AIMessage with content
    final_answer = ""
    for msg in reversed(result["messages"]):
        if isinstance(msg, AIMessage) and msg.content:
            final_answer = msg.content
            break

    if verbose:
        print(f"Tool sequence: {[tc['name'] for tc in tool_calls]}")
        print(f"\nFinal answer: {final_answer}")

    return {"final_answer": final_answer, "tool_calls": tool_calls}