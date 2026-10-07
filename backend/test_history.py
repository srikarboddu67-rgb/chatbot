"""
test_history.py  ->  tests the chat history API (server must be running).

Run (with the server running in another terminal):
    python backend\\test_history.py
"""

import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import requests

BASE = "http://127.0.0.1:5000"
ok_count = 0


def check(label, condition, extra=""):
    global ok_count
    mark = "PASS" if condition else "FAIL"
    if condition:
        ok_count += 1
    print(f"[{mark}] {label} {extra}")


# --- 1) history starts (nearly) empty ---------------------------------
r = requests.get(f"{BASE}/api/chats")
before = r.json().get("chats", [])
check("GET /api/chats", r.status_code == 200, f"-> {len(before)} chat(s)")

# --- 2) a REJECTED request must NOT create a chat ---------------------
requests.post(f"{BASE}/api/chat", json={"messages": []})   # invalid -> 400
r = requests.get(f"{BASE}/api/chats")
check("invalid request creates no chat", len(r.json().get("chats", [])) == len(before))

# --- 3) seed one chat directly (as if an AI answer was saved) ---------
import database  # noqa: E402  (backend folder must be on the path)

database.init_db()
chat_id = database.create_chat("Demo: what is Python?")
database.add_message(chat_id, "user", "what is Python?")
database.add_message(chat_id, "assistant", "Python is a popular programming language.")
print(f"seeded demo chat id = {chat_id}")

# --- 4) list shows it --------------------------------------------------
r = requests.get(f"{BASE}/api/chats")
chats = r.json().get("chats", [])
check("GET /api/chats lists the demo", any(c["id"] == chat_id for c in chats))

# --- 5) open it with messages -----------------------------------------
r = requests.get(f"{BASE}/api/chats/{chat_id}")
data = r.json()
check(
    "GET /api/chats/<id>",
    r.status_code == 200 and len(data.get("messages", [])) == 2,
    f"-> title={data.get('chat', {}).get('title')!r}, {len(data.get('messages', []))} messages",
)

# --- 6) unknown id -> 404 --------------------------------------------
r = requests.get(f"{BASE}/api/chats/99999")
check("GET unknown chat -> 404", r.status_code == 404, f"-> {r.json()}")

# --- 7) delete it ------------------------------------------------------
r = requests.delete(f"{BASE}/api/chats/{chat_id}")
check("DELETE /api/chats/<id>", r.status_code == 200, f"-> {r.json()}")

r = requests.delete(f"{BASE}/api/chats/{chat_id}")
check("DELETE same chat again -> 404", r.status_code == 404)

# --- 8) history empty again -------------------------------------------
r = requests.get(f"{BASE}/api/chats")
check("history is empty after delete", len(r.json().get("chats", [])) == len(before))

print(f"\n{ok_count}/8 TESTS PASSED")
