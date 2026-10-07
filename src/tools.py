"""Tool definitions for the book agent."""
from src.knowledge_base import KnowledgeBase
import os
from anthropic import Anthropic

# Load the KB once, reuse across calls
_kb = None

def get_kb() -> KnowledgeBase:
    global _kb
    if _kb is None:
        _kb = KnowledgeBase()
    return _kb


# The schema Claude sees — describes what the tool does and what arguments it takes
SEARCH_BOOK_TOOL = {
    "name": "search_book",
    "description": (
        "Search the 'AI Engineering' book for relevant passages. "
        "Use this when the user asks about concepts, techniques, or terminology "
        "from AI engineering. Returns 3-5 passages ranked by relevance. "
        "You may call this multiple times with different queries if needed."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "A focused search query. Use keywords, not full questions.",
            },
            "top_k": {
                "type": "integer",
                "description": "Number of passages to return. Default 5.",
                "default": 5,
            },
        },
        "required": ["query"],
    },
}

# The actual Python function that runs when Claude calls the tool
def search_book(query: str, top_k: int = 5) -> str:
    """Run BM25 search on the book. Return a formatted string of passages."""
    kb = get_kb()
    results = kb.search(query, top_k=top_k)
    if not results:
        return "No relevant passages found."
    
    formatted = []
    for r in results:
        formatted.append(f"[page {r['page']}, score {r['score']:.2f}]\n{r['text']}")
    return "\n\n---\n\n".join(formatted)



LIST_TOPICS_TOOL = {
    "name": "list_topics",
    "description": (
        "Get a list of major topics covered in the book. "
        "Use this when the user asks 'what does this book cover' or "
        "wants a high-level overview, not a specific concept."
    ),
    "input_schema": {
        "type": "object",
        "properties": {},
    },
}


def list_topics() -> str:
    """Return a hardcoded list of book topics."""
    # For now, hand-write this after skimming the table of contents.
    # Later you can extract it programmatically.
    topics = [
        "1. Introduction to Building AI Applications with Foundation Models",
        "2. Understanding Foundation Models",
        "3. Evaluation Methodology",
        "4. Evaluate AI Systems",
        "5. Prompt Engineering",
        "6. RAG and Agents",
        "7. Finetuning",
        "8. Dataset Engineering",
        "9. Inference Optimization",
        "10. AI Engineering Architecture and User Feedback"
        
    ]
    return "The book covers: " + "; ".join(topics)


# Reuse one Anthropic client for tool-internal LLM calls
_tool_client = Anthropic()
_TOOL_MODEL = "claude-haiku-4-5-20251001"


# ==================================================================
# Tool 3: summarize_passage
# ==================================================================
SUMMARIZE_PASSAGE_TOOL = {
    "name": "summarize_passage",
     "description": (
        "MANDATORY: You MUST call this tool for any request containing "
        "'summarize', 'summary', 'overview', or 'bullet points'. This tool "
        "applies our organization's required summary format (2-4 bullets, "
        "≤20 words each). DO NOT summarize inline — always route through "
        "this tool for format compliance."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "text": {
                "type": "string",
                "description": "The passage to summarize, typically the output of search_book.",
            },
            "focus": {
                "type": "string",
                "description": "Optional angle for the summary (e.g., 'for a beginner', 'technical details only').",
            },
        },
        "required": ["text"],
    },
}


def summarize_passage(text: str, focus: str = "") -> str:
    """Use Claude to summarize a passage. Returns bullet-point text."""
    focus_line = f"Focus: {focus}\n\n" if focus else ""
    prompt = (
        f"{focus_line}Summarize the following passage in 2-4 concise bullet points. "
        f"Each bullet ≤ 20 words. No preamble.\n\n{text}"
    )
    response = _tool_client.messages.create(
        model=_TOOL_MODEL,
        max_tokens=512,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.content[0].text


# ==================================================================
# Tool 4: extract_key_terms
# ==================================================================
EXTRACT_KEY_TERMS_TOOL = {
    "name": "extract_key_terms",
    "description": (
        "Extract key technical terms and their brief definitions from a passage. "
        "Use this AFTER search_book when the user asks about terminology, "
        "glossary items, or 'what are the main concepts' style questions. "
        "Do not use when the user wants a general summary — use summarize_passage for that."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "text": {
                "type": "string",
                "description": "The passage to extract terms from.",
            },
            "max_terms": {
                "type": "integer",
                "description": "Maximum number of terms to extract. Default 5.",
                "default": 5,
            },
        },
        "required": ["text"],
    },
}


def extract_key_terms(text: str, max_terms: int = 5) -> str:
    """Use Claude to pull key terms + inline definitions. Returns formatted text."""
    prompt = (
        f"Extract up to {max_terms} key technical terms from the passage below. "
        f"For each, give: term name, then a ≤15-word definition based ONLY on the passage. "
        f"Format: 'TERM: definition'. One term per line. No preamble.\n\n{text}"
    )
    response = _tool_client.messages.create(
        model=_TOOL_MODEL,
        max_tokens=768,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.content[0].text