# ⚡ AI Chatbot — ChatGPT-style Website

A modern AI chatbot website built with **HTML/CSS/JS** (frontend), **Python Flask** (backend),
**SQLite** (database) and **Google Gemini** (AI).

> 🔐 API keys live only in `.env` (backend). They are **never** sent to the browser.
>
> 🤖 **No API key yet?** No problem — the server runs in **DEMO MODE**: it answers with
> clearly-labeled local sample replies (with Markdown + code blocks) so the whole app can be
> tested. Add `AI_API_KEY` to `.env` and restart → **real Google Gemini** answers take over automatically.

---

## ✨ Features

- 💬 Chat with an AI (Google Gemini) — remembers the whole conversation
- 📁 Sidebar **chat history**: new chat, open old chats, delete chats (saved in SQLite)
- 🌗 **Dark mode / light mode** (remembered in the browser)
- 📱 Fully responsive — works on desktop and mobile (hamburger menu)
- ⏳ Typing indicator + smooth message animations
- 📝 **Markdown** rendering (tables, lists, links) + **syntax-highlighted code** with copy buttons
- 🔐 Copy button on every AI answer
- 🛡️ Security: input validation, XSS protection (DOMPurify), API key backend-only, `.env` in `.gitignore`
- ⚠️ Friendly error messages: network fail, rate limit, empty message, timeout, bad key

---

## 📁 Project structure

```
chatbot-project/
├── backend/
│   ├── app.py            # Flask server + all REST API routes
│   ├── ai_service.py     # calls Google Gemini (reads .env key)
│   ├── database.py       # SQLite operations (chats + messages)
│   ├── test_api.py       # tests the chat API (5 checks)
│   ├── test_history.py   # tests the history API (8 checks)
│   └── test_db.py        # tests the database layer (7 checks)
├── frontend/
│   ├── templates/index.html        # the chat page
│   └── static/
│       ├── css/style.css           # layout, themes, animations
│       └── js/script.js            # chat logic, history, markdown
├── database/chatbot.db   # SQLite file (auto-created)
├── .env                  # SECRET API keys  (never push to Git!)
├── .gitignore
├── requirements.txt
├── run.bat               # Windows: double-click to start
└── README.md
```

---

## 🚀 Setup (Windows 11)

### 1. Get a free Gemini API key
https://aistudio.google.com/apikey → **Create API key** → copy it.

### 2. Put the key in `.env`
```
AI_API_KEY=AIzaSy........................ your real key
```

### 3. Install (first time only)
```powershell
cd "C:\Users\SRIKAR\OneDrive\Desktop\ai chatbot\chatbot-project"
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 4. Run
```powershell
python backend\app.py
```
Open **http://127.0.0.1:5000** 🎉

*Shortcut: double-click `run.bat` (creates venv + installs + starts automatically).*

Stop the server: `Ctrl + C`

---

## 🧪 Testing

With the server running, open a **second terminal**:
```powershell
.\venv\Scripts\Activate.ps1
python backend\test_api.py        # chat API  (5 checks)
python backend\test_history.py    # history API (8 checks)
python backend\test_db.py         # database (7 checks, no server needed)
```

Quick browser check: http://127.0.0.1:5000/api/health → `{"status": "ok", ...}`

---

## 🔌 API reference

| Endpoint | Method | Body / Params | Returns |
|---|---|---|---|
| `/api/health` | GET | — | `{"status","model","api_key_set"}` |
| `/api/chat` | POST | `{"messages":[{role,content},...], "chat_id": 1?}` | `{"reply","chat_id"}` |
| `/api/chats` | GET | — | `{"chats":[{id,title,updated_at},...]}` |
| `/api/chats/<id>` | GET | — | `{"chat":{...},"messages":[...]}` |
| `/api/chats/<id>` | DELETE | — | `{"deleted": id}` |

Errors always return: `{"error": "friendly message"}` with HTTP 400/404/429/500/502.

---

## 🗄️ Database (SQLite)

```
chats(id, title, created_at, updated_at)
messages(id, chat_id, role[user|assistant], content, created_at)
```
A chat is created **automatically after the first successful AI answer**
(title = first 40 characters of your question).

---

## 🔒 Security notes

- `AI_API_KEY` exists only in `.env` → read only by Python (backend)
- `.env` is in `.gitignore` → can never be pushed to GitHub
- Server validates every message (type, empty, length ≤ 4000, valid role)
- Only the newest 40 messages are forwarded to the AI (request size limit)
- AI output is sanitized with **DOMPurify** before entering the page (XSS)
- User input is shown via `textContent` → cannot inject HTML

---

## 🔮 Future features — where to add them

| Feature | Where to add |
|---|---|
| Image generation | new route `/api/image` in `app.py` + new service in a `image_service.py` |
| Voice input / output | Web Speech API in `script.js` (no backend change) |
| Chat with a PDF | new upload route + `pdf_service.py`, save extracted text into `messages` |
| User authentication | new `users` table + login routes (messages already have `chat_id` to attach) |
| File upload | new `/api/upload` route (Flask handles the file) |
| AI model selection | dropdown in UI → send `model` in `/api/chat` body → `ai_service.py` uses it |
| Chat export | new `/api/chats/<id>/export` route → download `.md` / `.txt` |

---

## 🛠️ Troubleshooting quick fixes

| Problem | Fix |
|---|---|
| `'python' is not recognized` | Reinstall Python with ✅ **Add to PATH** ticked |
| PowerShell blocks activation | `Set-ExecutionPolicy -ExecutionPolicy Bypass -Scope Process` |
| `Address already in use` | Old server still running → close its terminal / change `PORT` in `.env` |
| Red bubble "API key not configured" | Should not happen anymore — without a key the server answers in **DEMO MODE**. For real AI: paste key in `.env` → **restart server** |
| Red bubble "Network error" | Start the server: `python backend\app.py` |
| "Too many requests" (429) | Wait 10–30 seconds, try again |
| Page unstyled / JS dead | Internet needed for CDN libs → hard refresh `Ctrl+Shift+R` |
| `no such table` / weird DB errors | Stop server → delete `database\chatbot.db` → restart |
| `UnicodeEncodeError: 'charmap'` | Old Windows console encoding → files already use `sys.stdout.reconfigure(encoding="utf-8")` |

---

## 📋 Build steps (completed)

- [x] Step 1 — Architecture & folder structure
- [x] Step 2 — Python virtual environment + packages
- [x] Step 3 — Backend API (Flask + Gemini)
- [x] Step 4 — Frontend UI (HTML/CSS, dark/light mode)
- [x] Step 5 — Frontend chat logic (markdown, copy, errors)
- [x] Step 6 — SQLite database (save/open/delete chats)
- [x] Step 7 — Error handling, polish, final testing
