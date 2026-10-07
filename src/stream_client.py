# scripts/stream_client.py
import requests
import json

resp = requests.post(
    "http://127.0.0.1:8000/query/stream",
    json={"question": "Summarize fine-tuning in 3 bullets"},
    stream=True,
)
for line in resp.iter_lines():
    if line:
        print(json.dumps(json.loads(line), indent=2))
        print("---")