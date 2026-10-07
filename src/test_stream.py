"""Simple streaming client to test /query/stream."""
import requests
import json

url = "http://127.0.0.1:8000/query/stream"
payload = {"question": "Please describe fine-tuning in five bullet points."}

print(f"Sending: {payload['question']}\n")

# stream=True means don't wait for the whole response — process as it arrives
response = requests.post(url, json=payload, stream=True)

for line in response.iter_lines():
    if line:
        # Each line is a JSON object
        data = json.loads(line)
        print(f"[{data.get('stage', 'unknown')}]")
        # Print any of the fields present
        for key, value in data.items():
            if key != "stage":
                # Truncate long values for display
                display_value = str(value)[:200]
                print(f"  {key}: {display_value}")
        print()