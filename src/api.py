"""FastAPI wrapper around the routed agent."""

from dotenv import load_dotenv
load_dotenv()  # MUST come before importing routed_agent


from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import Optional

from src.routed_agent import run_routed_agent

from fastapi.responses import StreamingResponse
import json

app = FastAPI(
    title="Book Agent API",
    description="Query an AI Engineering book via a routed multi-tool agent",
    version="0.1.0",
)


# Request schema defines what a caller must send when they hit your /query endpoint.
class QueryRequest(BaseModel):
    """Request body for /query endpoint."""
    question: str = Field(..., min_length=1, max_length=1000, description="The user's question")


# response schema. Defines what your endpoint returns.
class QueryResponse(BaseModel):
    """Structured response — same shape as run_routed_agent output."""
    final_answer: str
    query_type: str
    analysis_type: Optional[str] = None



def stream_agent_output(question: str):
    """Yield agent output token by token or chunk by chunk."""
    # For a simple demo, we'll stream state updates from the routed agent
    # A more complete version would stream the LLM's token output directly
    yield json.dumps({"stage": "starting", "message": "Classifying query..."}) + "\n"
    
    result = run_routed_agent(question)
    
    yield json.dumps({
        "stage": "classified",
        "query_type": result["query_type"],
        "analysis_type": result.get("analysis_type", ""),
    }) + "\n"
    
    yield json.dumps({
        "stage": "final",
        "answer": result["final_answer"],
    }) + "\n"


@app.post("/query/stream")
def query_stream(request: QueryRequest):
    """Streamed version of /query — sends updates as agent progresses."""
    return StreamingResponse(
        stream_agent_output(request.question),
        media_type="application/x-ndjson",
    )



@app.get("/")
def root():
    """Health check."""
    return {"status": "ok", "service": "book-agent-api"}


@app.post("/query", response_model=QueryResponse)
def query_endpoint(request: QueryRequest) -> QueryResponse:
    """Send a question to the agent, get an answer."""
    try:
        result = run_routed_agent(request.question)
        return QueryResponse(
            final_answer=result["final_answer"],
            query_type=result["query_type"],
            analysis_type=result.get("analysis_type") or None,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Agent execution failed: {str(e)}")
    
