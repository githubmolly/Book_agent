------ LangGraph persistance -- checkpoints

need to remove .db information 

Remove-Item data/checkpoints.db
>> Remove-Item data/checkpoints.db-shm -ErrorAction SilentlyContinue
>> Remove-Item data/checkpoints.db-wal -ErrorAction SilentlyContinue
>> python src/checkpoint_demo.py
Thread demo-session-1: 0 messages already in history
Thread demo-session-2: 0 messages already in history
=== Call 1 — new thread ===
→ Classified as: search_only ()
→ Search returned 3949 chars
[search_only] # Retrieval-Augmented Generation (RAG)

Retrieval-Augmented Generation (RAG) is an AI engineering technique that enhances model outputs by connecting the model to external data sources.

## Definition...

=== Call 2 — same thread, follow-up ===
→ Classified as: search_only ()
→ Search returned 4742 chars
[search_only] # Key AI Engineering Techniques

Based on the context provided, the three very common AI engineering techniques for adapting a model to your needs are (page 35):

1. **Prompt Engineering**: Crafting d...

=== State snapshot for demo-session-1 ===
Number of messages in history: 4
  [0] HumanMessage: What is retrieval augmented generation?...
  [1] AIMessage: # Retrieval-Augmented Generation (RAG)

Retrieval-Augmented Generation (RAG) is ...
  [2] HumanMessage: What were the key techniques you just mentioned?...
  [3] AIMessage: # Key AI Engineering Techniques

Based on the context provided, the three very c...

=== Call 3 — different thread, same follow-up phrasing ===
→ Classified as: chat ()
[chat] I haven't mentioned any techniques yet in our conversation—this is actually the first message you've sent me. 

It's possible you might be:
- Continuing a conversation from a different chat session (e...



-------- (api-docs-rag) PS E:\P1_JOB\AI projects\book_agent> python src/inspect_checkpoints.py
=== Tables ===
  checkpoints
  writes

=== Row counts ===
  checkpoints: 14 rows
  writes: 31 rows

=== Threads and their checkpoint counts ===
  demo-session-1: 10 checkpoints
  demo-session-2: 4 checkpoints