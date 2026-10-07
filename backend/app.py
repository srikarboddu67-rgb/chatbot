"""
app.py  ->  main Flask server (REST API) for the AI chatbot.

How to run (from the project folder, with venv activated):
    python backend\\app.py

Then open:  http://127.0.0.1:5000

API endpoints:
    GET    /                 -> chat UI (index.html)
    GET    /api/health       -> server status
    POST   /api/chat         -> ask the AI (saves the chat)
    GET    /api/chats        -> list all chats (sidebar history)
    GET    /api/chats/<id>   -> open one old chat (with messages)
    DELETE /api/chats/<id>   -> delete a chat
"""

import os
import sqlite3
import sys

# Windows terminals default to cp1252 -> force UTF-8 so
# emoji/⚠ symbols print without UnicodeEncodeError
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from flask import Flask, jsonify, render_template, request
from dotenv import load_dotenv

import database
from ai_service import ask_ai, AIServiceError

# ---------------------------------------------------------------
# 1. Load secrets from .env  (project root, one folder above this file)
# ---------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(BASE_DIR, ".env"))

# ---------------------------------------------------------------
# 2. App setup + database (tables are created on first run)
# ---------------------------------------------------------------
app = Flask(
    __name__,
    # tell Flask where our frontend files live
    template_folder=os.path.join(BASE_DIR, "frontend", "templates"),
    static_folder=os.path.join(BASE_DIR, "frontend", "static"),
)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "dev-secret-change-me")

database.init_db()  # creates database/chatbot.db if missing

# Input limits (security)
MAX_MESSAGE_LENGTH = 4000      # max characters per message
MAX_CONTEXT_MESSAGES = 40      # only send the newest 40 messages to the AI


# ---------------------------------------------------------------
# 3. Input validation  (never trust the frontend!)
# ---------------------------------------------------------------
def validate_messages(payload):
    """Returns (clean_messages, error_message). One of them is always None."""
    if not isinstance(payload, dict):
        return None, "Invalid request: expected a JSON object."

    messages = payload.get("messages")
    if not isinstance(messages, list) or not messages:
        return None, "Message is empty. Please type something."

    # keep only the newest messages so the request cannot be huge
    if len(messages) > MAX_CONTEXT_MESSAGES:
        messages = messages[-MAX_CONTEXT_MESSAGES:]

    clean = []
    for m in messages:
        if not isinstance(m, dict):
            return None, "Invalid message format."
        role = m.get("role")
        content = m.get("content")
        if role not in ("user", "assistant"):
            return None, "Invalid message role."
        if not isinstance(content, str) or not content.strip():
            return None, "Empty messages are not allowed."
        if len(content) > MAX_MESSAGE_LENGTH:
            return None, f"Message is too long (max {MAX_MESSAGE_LENGTH} characters)."
        clean.append({"role": role, "content": content.strip()})

    return clean, None


def save_conversation(chat_id, messages, reply):
    """
    Save the newest user message + the AI reply to SQLite.
    If chat_id is missing/unknown -> a NEW chat is created
    (title = first user message, max 40 characters).
    Returns the chat id.
    """
    if not isinstance(chat_id, int) or database.get_chat(chat_id) is None:
        first_user = next(
            (m["content"] for m in reversed(messages) if m["role"] == "user"),
            "New chat",
        )
        title = first_user[:40] + ("..." if len(first_user) > 40 else "")
        chat_id = database.create_chat(title)

    last_user = next(
        (m["content"] for m in reversed(messages) if m["role"] == "user"), ""
    )
    if last_user:
        database.add_message(chat_id, "user", last_user)
    database.add_message(chat_id, "assistant", reply)
    return chat_id


# ---------------------------------------------------------------
# 4. Routes (REST API)
# ---------------------------------------------------------------
@app.route("/")
def home():
    """Serve the chat UI (index.html)."""
    return render_template("index.html")


@app.route("/api/health")
def health():
    """Quick check: is the server alive? Is the API key configured?"""
    key = os.getenv("AI_API_KEY", "")
    key_ready = bool(key) and not key.startswith("paste-your")
    return jsonify({
        "status": "ok",
        "model": os.getenv("AI_MODEL", "not set"),
        "api_key_set": key_ready,
        "mode": "ai" if key_ready else "demo",
    })


@app.route("/api/chat", methods=["POST"])
def chat():
    """
    Main endpoint. Frontend sends:
        {"messages": [{"role": "user", "content": "Hi!"}], "chat_id": 1}
    We return:
        {"reply": "Hello! ...", "chat_id": 1}
    or on error:
        {"error": "friendly message"}
    """
    payload = request.get_json(silent=True)
    messages, error = validate_messages(payload)
    if error:
        return jsonify({"error": error}), 400

    chat_id = payload.get("chat_id") if isinstance(payload, dict) else None

    try:
        reply = ask_ai(messages)                    # 1) call Google Gemini
        chat_id = save_conversation(chat_id, messages, reply)  # 2) save it
        return jsonify({"reply": reply, "chat_id": chat_id})
    except AIServiceError as e:
        return jsonify({"error": e.message}), e.status_code
    except sqlite3.Error:
        app.logger.exception("Database error in /api/chat")
        return jsonify({"error": "Could not save this chat. Please try again."}), 500
    except Exception:
        app.logger.exception("Unexpected error in /api/chat")
        return jsonify({"error": "Something went wrong on the server. Please try again."}), 500


# ---------- chat history ----------
@app.route("/api/chats", methods=["GET"])
def list_all_chats():
    """Sidebar history: every chat, newest activity first."""
    try:
        return jsonify({"chats": database.list_chats()})
    except sqlite3.Error:
        app.logger.exception("Database error in GET /api/chats")
        return jsonify({"error": "Could not load chat history."}), 500


@app.route("/api/chats/<int:chat_id>", methods=["GET"])
def open_chat(chat_id):
    """Open one old conversation (chat info + all its messages)."""
    try:
        chat = database.get_chat(chat_id)
        if chat is None:
            return jsonify({"error": "Chat not found."}), 404
        return jsonify({"chat": chat, "messages": database.get_messages(chat_id)})
    except sqlite3.Error:
        app.logger.exception("Database error in GET /api/chats/<id>")
        return jsonify({"error": "Could not open this chat."}), 500


@app.route("/api/chats/<int:chat_id>", methods=["DELETE"])
def remove_chat(chat_id):
    """Delete a chat (and its messages) from the history."""
    try:
        if not database.delete_chat(chat_id):
            return jsonify({"error": "Chat not found."}), 404
        return jsonify({"deleted": chat_id})
    except sqlite3.Error:
        app.logger.exception("Database error in DELETE /api/chats/<id>")
        return jsonify({"error": "Could not delete this chat."}), 500


# ---------------------------------------------------------------
# 5. Start the server
# ---------------------------------------------------------------
if __name__ == "__main__":
    port = int(os.getenv("PORT", "5000"))

    # --- friendly security warnings for beginners ---
    if os.getenv("FLASK_SECRET_KEY", "") == "change-me-to-a-random-long-string":
        print("\n  ⚠ WARNING: FLASK_SECRET_KEY is still the placeholder.")
        print("    Put any long random text in .env (session security).")
    api_key = os.getenv("AI_API_KEY", "")
    if api_key is None or api_key.startswith("paste-your"):
        print("\n  ⚠ WARNING: AI_API_KEY is not set in .env yet.")
        print("    Until you add it, the chatbot sends local DEMO replies.")
        print("    Real AI (free key): https://aistudio.google.com/apikey")

    print(f"\n  AI chatbot backend running on  http://127.0.0.1:{port}")
    print("  Press Ctrl+C to stop.\n")
    app.run(host="127.0.0.1", port=port, debug=True)
