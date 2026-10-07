# scripts/checkpoint_demo.py
"""Demonstrate checkpointing: state persists across invocations by thread_id."""
from src.routed_agent import run_routed_agent
from src.routed_agent import _graph

for tid in ["demo-session-1", "demo-session-2"]:
    snapshot = _graph.get_state({"configurable": {"thread_id": tid}})
    n = len(snapshot.values.get("messages", [])) if snapshot.values else 0
    print(f"Thread {tid}: {n} messages already in history")


print("=== Call 1 — new thread ===")
r1 = run_routed_agent(
    "What is retrieval augmented generation?",
    thread_id="demo-session-1",
)
print(f"[{r1['query_type']}] {r1['final_answer'][:200]}...")

print("\n=== Call 2 — same thread, follow-up ===")
r2 = run_routed_agent(
    "What were the key techniques you just mentioned?",
    thread_id="demo-session-1",
)
print(f"[{r2['query_type']}] {r2['final_answer'][:200]}...")

# After Call 2, before Call 3
from src.routed_agent import _graph

snapshot = _graph.get_state({"configurable": {"thread_id": "demo-session-1"}})
print("\n=== State snapshot for demo-session-1 ===")
print(f"Number of messages in history: {len(snapshot.values['messages'])}")
for i, m in enumerate(snapshot.values["messages"]):
    role = type(m).__name__
    print(f"  [{i}] {role}: {m.content[:80]}...")



print("\n=== Call 3 — different thread, same follow-up phrasing ===")
r3 = run_routed_agent(
    "What were the key techniques you just mentioned?",
    thread_id="demo-session-2",
)
print(f"[{r3['query_type']}] {r3['final_answer'][:200]}...")


