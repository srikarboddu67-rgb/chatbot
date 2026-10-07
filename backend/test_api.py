"""
test_api.py  ->  quick manual test for the backend API.

How to run (keep the server running in another terminal):
    python backend\\test_api.py
"""

import requests

BASE = "http://127.0.0.1:5000"


def show(title, response):
    print(f"\n--- {title} ---")
    print("Status :", response.status_code)
    try:
        print("Body   :", response.json())
    except ValueError:
        print("Body   :", response.text[:200])


# 1) Is the server alive? Is the API key set?
show("GET /api/health", requests.get(f"{BASE}/api/health"))

# 2) Normal chat question (needs a real API key in .env)
show(
    "POST /api/chat  (normal question)",
    requests.post(
        f"{BASE}/api/chat",
        json={"messages": [{"role": "user", "content": "Hello! Who are you?"}]},
    ),
)

# 3) Empty message  -> must be rejected with 400
show(
    "POST /api/chat  (empty - must fail)",
    requests.post(f"{BASE}/api/chat", json={"messages": []}),
)

# 4) Not JSON at all -> must be rejected with 400
show(
    "POST /api/chat  (not JSON - must fail)",
    requests.post(
        f"{BASE}/api/chat",
        data="this is not json",
        headers={"Content-Type": "text/plain"},
    ),
)

# 5) Empty text inside message -> must be rejected with 400
show(
    "POST /api/chat  (blank text - must fail)",
    requests.post(
        f"{BASE}/api/chat",
        json={"messages": [{"role": "user", "content": "   "}]},
    ),
)
