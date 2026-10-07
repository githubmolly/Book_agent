# scripts/hitl_demo.py
"""Demonstrate human-in-the-loop: pause, inspect, resume."""
from langchain_core.messages import HumanMessage
from langgraph.checkpoint.memory import MemorySaver

from src.routed_agent import build_routed_graph

# Use MemorySaver for a clean demo run — no SQLite pollution
demo_checkpointer = MemorySaver()

# Build a separate graph instance with an interrupt before do_search
hitl_graph = build_routed_graph(
    checkpointer=demo_checkpointer,
    interrupt_before=["do_search"],
)

config = {"configurable": {"thread_id": "hitl-demo"}}

# First invoke — runs up to do_search, then pauses
print("=== First invoke — should pause before do_search ===")

# Key API detail: hitl_graph.invoke(None, config=config) with None as the input is the "resume from checkpoint" signal. Passing new input would start a fresh run.
result = hitl_graph.invoke(
    {
        "messages": [HumanMessage(content="What is fine-tuning?")],
        "query_type": "",
        "analysis_type": "",
        "search_results": "",
    },
    config=config,
)
print(f"Classified as: {result['query_type']}")
print(f"search_results so far: {len(result.get('search_results', ''))} chars")

# Inspect graph state — what's the next scheduled step?
snapshot = hitl_graph.get_state(config)
print(f"\nGraph is paused. Next node scheduled: {snapshot.next}")
# Expected: ('do_search',)

# --- Simulate a human decision point here ---
input("\nPress Enter to resume the graph (in a real system, this would be an approval UI)...")

# Resume by passing None as input
print("\n=== Resuming ===")
result = hitl_graph.invoke(None, config=config)
print(f"Search returned: {len(result.get('search_results', ''))} chars")
print(f"\nFinal answer:\n{result['messages'][-1].content[:300]}...")