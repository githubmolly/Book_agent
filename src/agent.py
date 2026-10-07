"""A single-tool agent that answers questions using search_book."""
import os
import json
from anthropic import Anthropic
from dotenv import load_dotenv

from src.tools import (
    SEARCH_BOOK_TOOL, LIST_TOPICS_TOOL,
    SUMMARIZE_PASSAGE_TOOL, EXTRACT_KEY_TERMS_TOOL,
    search_book, list_topics,
    summarize_passage, extract_key_terms,
)

load_dotenv()
client = Anthropic()

MODEL = "claude-haiku-4-5-20251001"

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

TOOL_REGISTRY = {
    "search_book": search_book,
    "list_topics": list_topics,
    "summarize_passage": summarize_passage,
    "extract_key_terms": extract_key_terms,
}

TOOL_SCHEMAS = [
    SEARCH_BOOK_TOOL,
    LIST_TOPICS_TOOL,
    SUMMARIZE_PASSAGE_TOOL,
    EXTRACT_KEY_TERMS_TOOL,
]

def run_agent(user_message: str, max_turns: int = 5, verbose: bool = True) -> str:
    """
    Run the agent loop. Return the final assistant message.
    
    max_turns: safety limit — how many times the loop can iterate before we give up.
    verbose: print what the model is doing at each turn.
    """
    messages = [{"role": "user", "content": user_message}]
    

    for turn in range(1, max_turns + 1):
        if verbose:
            print(f"\n--- Turn {turn} ---")
        
        response = client.messages.create(
            model=MODEL,
            max_tokens=2048,
            system=SYSTEM_PROMPT,
            tools=TOOL_SCHEMAS,
            messages=messages,
            )
                                
        # Case 1: Model is done (no more tool calls needed)
        if response.stop_reason == "end_turn":
            final_text = "".join(b.text for b in response.content if b.type == "text")
            if verbose:
                print(f"Agent (final): {final_text}")
            return final_text
        
        # Case 2: Model wants to call one or more tools
        # Append the model's response (containing tool_use blocks) to conversation
        messages.append({"role": "assistant", "content": response.content})
        
        # Execute every tool_use block, collect tool_result blocks
        tool_results = []
        for block in response.content:
            if block.type == "tool_use":
                if verbose:
                    print(f"Tool call: {block.name}({block.input})")
                
                # if block.name == "search_book":
                #     result_text = search_book(**block.input)
                # if block.name == "list_topics":
                #     result_text = list_topics(**block.input)

                if block.name not in TOOL_REGISTRY:
                    result_text = json.dumps({
                        "error": "Unknown tool",
                        "message": f"Tool '{block.name}' does not exist. Available: {list(TOOL_REGISTRY.keys())}",
                    })
                else:
                    # # Model asks for a tool that doesn't exist. The model reads it and can course-correct.
                    # result_text = json.dumps({
                    #     "error": "Unknown tool",
                    #     "message": f"Tool '{block.name}' does not exist. Available: search_book, list_topics",
                    # })

                    # Patch 2: catch tool execution failures
                    try:
                        result_text = TOOL_REGISTRY[block.name](**block.input)
                    except Exception as e:
                        result_text = json.dumps({
                            "error": "Tool execution failed",
                            "message": str(e),
                        })
                
                if verbose:
                    print(f"Tool returned {len(result_text)} chars")
                
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": result_text,
                })
        
        # Feed the tool results back to the model
        messages.append({"role": "user", "content": tool_results})
    
    # If we exit the loop without stop_reason=end_turn, something is off
    raise RuntimeError(f"Agent did not converge in {max_turns} turns")


def run_agent_with_trace(user_message: str, max_turns: int = 5) -> dict:
    """
    Same behavior as run_agent, but returns a dict with diagnostic trace
    instead of just the final string. Useful for evaluation.
    """
    messages = [{"role": "user", "content": user_message}]
    trace = {"tool_calls": [], "final_answer": "", "turns": 0}
    last_call = None

    for turn in range(1, max_turns + 1):
        trace["turns"] = turn
        
        response = client.messages.create(
            model=MODEL,
            max_tokens=2048,
            system=SYSTEM_PROMPT,
            tools=TOOL_SCHEMAS,           # ★ use registry list, not hardcoded
            messages=messages,            # ★ this was missing entirely
        )

        # Case 1: Model finished
        if response.stop_reason == "end_turn":
            trace["final_answer"] = "".join(
                b.text for b in response.content if b.type == "text"
            )
            return trace

        # Case 2: Model wants tools — append assistant response, execute tools
        messages.append({"role": "assistant", "content": response.content})

        tool_results = []
        for block in response.content:
            if block.type == "tool_use":
                trace["tool_calls"].append({
                    "name": block.name,
                    "input": block.input,
                })
                
                # Repeat call detection (from Week 2 Day 5 robustness patch)
                current_call = (block.name, json.dumps(block.input, sort_keys=True))
                if current_call == last_call:
                    print(f"⚠ Repeat call detected: {block.name}({block.input})")
                last_call = current_call
                
                # Execute the tool via registry
                if block.name not in TOOL_REGISTRY:
                    result_text = json.dumps({
                        "error": "Unknown tool",
                        "message": f"Tool '{block.name}' does not exist. Available: {list(TOOL_REGISTRY.keys())}",
                    })
                else:
                    try:
                        result_text = TOOL_REGISTRY[block.name](**block.input)
                    except Exception as e:
                        result_text = json.dumps({
                            "error": "Tool execution failed",
                            "message": str(e),
                        })

                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": result_text,
                })

        # Feed tool results back to the model
        messages.append({"role": "user", "content": tool_results})

    # Max turns exceeded — return whatever we have
    trace["final_answer"] = "[Agent did not converge in max_turns]"
    return trace

