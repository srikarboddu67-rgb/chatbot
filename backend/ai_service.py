"""
ai_service.py  ->  talks to Google Gemini API.

IMPORTANT RULE:
    The API key is read from the .env file (backend only).
    It is NEVER sent to the browser / frontend.
"""

import os
import requests

# ---------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------
GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

# Instructions given to the AI about how it should behave
SYSTEM_PROMPT = (
    "You are a friendly and helpful AI assistant. "
    "Answer clearly and concisely. Use Markdown formatting when it helps, "
    "and use ``` code blocks for code."
)

TIMEOUT_SECONDS = 60  # don't wait forever for the AI


# ---------------------------------------------------------------
# Custom error class - so we can send friendly messages to frontend
# ---------------------------------------------------------------
class AIServiceError(Exception):
    def __init__(self, message, status_code=502):
        super().__init__(message)
        self.message = message      # friendly text shown in the chat UI
        self.status_code = status_code  # HTTP status code for the API


# ---------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------
def _get_api_key():
    """Returns the key, or None when .env still has the placeholder."""
    key = os.getenv("AI_API_KEY", "").strip()
    if not key or key.startswith("paste-your"):
        return None
    return key


def _demo_reply(messages):
    """
    No API key yet -> local DEMO answer (clearly labeled).
    This lets the student test the whole UI (markdown, code blocks,
    history) before getting a key. As soon as AI_API_KEY is set,
    real Google Gemini answers are used instead.
    """
    question = ""
    for m in reversed(messages):
        if m["role"] == "user":
            question = m["content"]
            break

    notice = (
        "🤖 **DEMO MODE** — `.env` lo `AI_API_KEY` inka set cheyyaledu, "
        "so this is a **local sample reply**.\n\n"
    )

    lower = question.lower()
    if any(w in lower for w in ("hello", "hi ", "hey", "namaste", "who are you")):
        body = (
            "Hello! 👋 I'm the demo reply of your chatbot.\n\n"
            "Paste a real key into `.env` (`AI_API_KEY=AIzaSy...`) and restart "
            "the server → **Google Gemini** will answer here for real."
        )
    elif any(w in lower for w in ("code", "python", "fibonacci", "javascript", "program")):
        body = (
            "Here is a code block to show **syntax highlighting**:\n\n"
            "```python\n"
            "def fibonacci(n):\n"
            "    a, b = 0, 1\n"
            "    for _ in range(n):\n"
            "        a, b = b, a + b\n"
            "    return a\n\n"
            "print(fibonacci(10))  # 55\n"
            "```\n\n"
            "Hover the block → **Copy** button works too ✅"
        )
    else:
        body = (
            f"You asked: **{question}**\n\n"
            "Demo reply showing Markdown support:\n\n"
            "| Feature | Status |\n"
            "|---|---|\n"
            "| Markdown + code | ✅ working |\n"
            "| Chat history (SQLite) | ✅ working |\n"
            "| Dark / light mode | ✅ working |\n"
            "| Real Google Gemini | ⏳ waiting for API key |\n"
        )

    return notice + body


def _convert_messages(messages):
    """Frontend uses roles: user / assistant. Gemini expects: user / model."""
    contents = []
    for m in messages:
        role = "user" if m["role"] == "user" else "model"
        contents.append({"role": role, "parts": [{"text": m["content"]}]})
    return contents


def _extract_text(data):
    """Pull the answer text out of Gemini's JSON response (safely)."""
    candidates = data.get("candidates") or []
    if not candidates:
        # Gemini blocked the prompt (safety filter)
        block_reason = (data.get("promptFeedback") or {}).get("blockReason")
        if block_reason:
            raise AIServiceError(
                "Your message was blocked by the AI safety filter. Please rephrase it.",
                400,
            )
        raise AIServiceError("The AI returned no response. Please try again.", 502)

    parts = (candidates[0].get("content") or {}).get("parts") or []
    # skip "thought" parts (internal reasoning of 2.5 models)
    text = "".join(p.get("text", "") for p in parts if not p.get("thought")).strip()

    if not text:
        raise AIServiceError("The AI returned an empty response. Please try again.", 502)
    return text


# ---------------------------------------------------------------
# Main function: send conversation -> get AI reply
# ---------------------------------------------------------------
def ask_ai(messages):
    """
    messages = [
        {"role": "user",      "content": "Hello!"},
        {"role": "assistant", "content": "Hi there!"},
        {"role": "user",      "content": "Who are you?"},
    ]
    Returns the AI reply as a plain string.
    """
    model = os.getenv("AI_MODEL", "gemini-2.5-flash").strip()
    api_key = _get_api_key()
    if api_key is None:
        # No key yet -> local demo answer so the whole UI can be tested
        return _demo_reply(messages)

    payload = {
        "systemInstruction": {"parts": [{"text": SYSTEM_PROMPT}]},
        "contents": _convert_messages(messages),
        "generationConfig": {"temperature": 0.7},
    }
    headers = {
        "Content-Type": "application/json",
        "x-goog-api-key": api_key,  # key sent in header, never in frontend
    }
    url = GEMINI_URL.format(model=model)

    # ---- 1. call the API ----
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=TIMEOUT_SECONDS)
    except requests.exceptions.Timeout:
        raise AIServiceError("The AI took too long to respond. Please try again.", 504)
    except requests.exceptions.RequestException:
        raise AIServiceError(
            "Could not reach the AI service. Check your internet connection and try again.",
            502,
        )

    # ---- 2. handle HTTP errors nicely ----
    if response.status_code == 429:
        raise AIServiceError(
            "Too many requests! Wait a few seconds, then try again.", 429
        )
    if response.status_code in (401, 403):
        raise AIServiceError(
            "Invalid API key. Check AI_API_KEY in your .env file.", 502
        )
    if response.status_code == 404:
        raise AIServiceError(
            f"AI model '{model}' not found. Check AI_MODEL in your .env file.", 502
        )
    if response.status_code >= 400:
        raise AIServiceError(
            "The AI service returned an error. Please try again later.", 502
        )

    # ---- 3. parse JSON answer ----
    try:
        data = response.json()
    except ValueError:
        raise AIServiceError("The AI service sent an unreadable response. Please try again.", 502)

    return _extract_text(data)
