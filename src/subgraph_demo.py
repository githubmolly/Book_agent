# src/subgraph_demo.py
"""Demonstrate subgraphs: a research workflow as an embeddable subgraph."""
from typing import TypedDict
from langgraph.graph import StateGraph, START, END
from src.tools import search_book


class ResearchState(TypedDict):
    """State scoped to the research subgraph."""
    query: str
    search_results: str
    analysis: str


def do_search_step(state: ResearchState) -> dict:
    results = search_book(state["query"], top_k=5)
    return {"search_results": results}


def do_analyze_step(state: ResearchState) -> dict:
    # Simplified — a real analyzer would call an LLM
    analysis = f"Retrieved {len(state['search_results'])} chars; would synthesize here."
    return {"analysis": analysis}


# Build the subgraph
research_builder = StateGraph(ResearchState)
research_builder.add_node("search", do_search_step)
research_builder.add_node("analyze", do_analyze_step)
research_builder.add_edge(START, "search")
research_builder.add_edge("search", "analyze")
research_builder.add_edge("analyze", END)
research_subgraph = research_builder.compile()


if __name__ == "__main__":
    # Test the subgraph standalone — this is the point of subgraphs
    result = research_subgraph.invoke({"query": "what is RAG evaluation"})
    print("Search chars:", len(result["search_results"]))
    print("Analysis:", result["analysis"])