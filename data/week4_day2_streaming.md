What this day proves — and what it does not

Being explicit up front so a reviewer doesn't overclaim:

Proves: FastAPI can hold an HTTP response open and emit chunks over time; the NDJSON contract is well-formed and parseable line-by-line on the client; the routed LangGraph agent runs cleanly from inside an ASGI request handler.


Two-terminal workflow

Long-running services hold the terminal that launched them. Any client testing has to happen from a second window.

>>Terminal 1 — start the server Terminal 1 (server terminal).
Runs the service. Its output is the service's log stream — every request, every error, every print statement from inside your endpoint handlers. You read this terminal to see what the server is doing internally.

powershell
cd "E:\P1_JOB\AI projects\book_agent"
.\.venv\Scripts\Activate.ps1
uvicorn src.api:app --reload

Output:

INFO:     Will watch for changes in these directories: ['E:\\P1_JOB\\AI projects\\book_agent']
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
INFO:     Started reloader process [15524] using StatReload
INFO:     Started server process [33288]
INFO:     Waiting for application startup.
INFO:     Application startup complete.



>>Terminal 2 — issue requests Terminal 2 (client terminal)
Runs whatever pokes at the service. Its output is what a real user of your API would see — the HTTP response body.

cd "E:\P1_JOB\AI projects\book_agent"
.\.venv\Scripts\Activate.ps1


>>Sanity check: server up and reachable

Before hitting the actual endpoint, confirm the server is listening:

powershell
curl.exe http://127.0.0.1:8000/docs -o NUL -w "%{http_code}`n"

output (200 is the confirmation; %{http_code} doesn't expand on PowerShell but the transfer summary + status code still confirm reachability):

  % Total    % Received % Xferd  Average Speed  Time    Time    Time   Current
                                 Dload  Upload  Total   Spent   Left   Speed
100   1013  100   1013    0      0  45626      0 --:--:-- --:--:-- --:--:-- 46045
200


>>Working streaming call

curl.exe --% -N -X POST "http://127.0.0.1:8000/query/stream" -H "Content-Type: application/json" -d "{\"question\": \"Summarize fine-tuning in 3 bullets\"}"


Observed output
Client side (Terminal 2) — three NDJSON lines
json
{"stage": "starting", "message": "Classifying query..."}
{"stage": "classified", "query_type": "search_analyze", "analysis_type": "summarize"}
{"stage": "final", "answer": "# Fine-tuning Summary\n\n\u2022 **Memory Constraints**: Memory is a significant bottleneck when fine-tuning large foundation models, making techniques that reduce memory footprint essential for accessibility.\n\n\u2022 **Parameter-Efficient Approaches**: Parameter-efficient fine-tuning methods allow developers to adapt models to specific tasks while substantially reducing both trainable parameters and memory requirements compared to full fine-tuning.\n\n\u2022 **Model Merging**: An experimental complementary technique that combines multiple fine-tuned models designed for the same purpose, offering an alternative to traditional fine-tuning methods."}


Server side (Terminal 1) — uvicorn logs

INFO:     127.0.0.1:14243 - "GET /docs HTTP/1.1" 200 OK
INFO:     127.0.0.1:14249 - "POST /query/stream HTTP/1.1" 200 OK
→ Classified as: search_analyze (summarize)
→ Search returned 4088 chars
→ Analysis (summarize): 461 chars