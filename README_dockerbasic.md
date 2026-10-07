## Running with Docker
Requirements: Docker Desktop installed.
```bash
# Set your API key
export ANTHROPIC_API_KEY=sk-ant-...
# Build and run
docker-compose up --build
# The API is now at http://localhost:8000
# Interactive docs at http://localhost:8000/docs
```
Test with curl:
```bash
curl -X POST http://localhost:8000/query \
     -H "Content-Type: application/json" \
     -d '{"question": "What is RAG?"}'
```



Goal: 
Containerize the FastAPI + LangGraph service so it runs identically inside an isolated Linux environment, testable end-to-end via port mapping from PowerShell on the host.

Details:
Secrets are injected at container runtime via --env-file, never baked into the image.

Verification commands:
PS
docker --version
docker ps


-- Multi-stage
Commands:
refine dockerfile to multiple stage

powershell
docker build -t book-agent:v0.2 .
docker images | Select-String book-agent
(api-docs-rag) PS E:\P1_JOB\AI projects\book_agent> docker images | Select-String book-agent

book-agent:v0.1   d0b08201e273        918MB          224MB        
book-agent:v0.2   8c86c1a39e92        804MB          196MB  

###The savings come from dropping uv, pip's cache, and the pip install layers.


-- Docker compose

create and modify the docker-compose.yml file

--build
docker-compose up --build

 The API is now available at `http://localhost:8000`
   - Interactive docs: `http://localhost:8000/docs`
   - Streaming endpoint: `POST /query/stream`

[+] up 2/2
 ✔ Network book_agent_default Created                                                                                                                              0.0s
 ✔ Container book-agent-api   Created                                                                                                                              0.2s
Attaching to book-agent-api
book-agent-api  | INFO:     Started server process [1]
book-agent-api  | INFO:     Waiting for application startup.
book-agent-api  | INFO:     Application startup complete.
book-agent-api  | INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)

-- testing with powershell
Another powershell
(api-docs-rag) PS E:\P1_JOB\AI projects\book_agent> python src/stream_client.py "summarize fine-tuning in 3 bullets"
{
  "stage": "starting",
  "message": "Classifying query..."
}
---
{
  "stage": "classified",
  "query_type": "search_analyze",
  "analysis_type": "summarize"
}
---
{
  "stage": "final",
  "answer": "# Summary of Fine-Tuning\n\nBased on the provided context, here are 3 key points about fine-tuning:\n\n\u2022 **Evaluation First**: Before investing in expensive fine-tuning, it's important to evaluate models and establish quality measures to ensure fine-tuning is the right approach.\n\n\u2022 **Parameter-Efficient Techniques**: Parameter-efficient fine-tuning methods reduce memory requirements, making model adaptation accessible to developers with limited computational resources.\n\n\u2022 **Model Merging as Complement**: Fine-tuning can be complemented by model merging, which combines multiple models to create custom applications\u2014an emerging creative approach to model customization."
}
---




Summary from Docker
"Why multi-stage matters for security, not just size." 
Every tool in your image is potential attack surface. If a vulnerability is discovered in pip next month, a single-stage image running pip freeze at startup would be affected; a multi-stage image without pip in the final layer is not. Image-size framings undersell this — the security framing is stronger and shows you're thinking about production risk, not just optimization.

"What Compose costs you and when it's worth paying." 
Being honest about tradeoffs is a signal of maturity. Compose adds a YAML file to maintain and a level of abstraction between "what you typed" and "what ran." For a single-service project, that overhead is barely worth it. For a multi-service project, it pays for itself immediately. Naming when you'd not use it (e.g., a one-off docker run for a debugging tool, or a hyperscale production deployment that uses Kubernetes directly) reads as thoughtful rather than dogmatic.
