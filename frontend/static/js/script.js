/* ============================================================
   script.js - AI chatbot frontend logic (Steps 5 + 6)
   - sends your message to the Python backend
   - shows typing indicator while waiting
   - renders Markdown + syntax-highlighted code
   - copy button on AI answers
   - saves / opens / deletes chats in the sidebar (SQLite)
   ============================================================ */

// ---------- 0. ELEMENTS ----------
const rootEl = document.documentElement;

const themeToggle = document.getElementById("themeToggle");
const themeIcon = document.getElementById("themeIcon");
const themeText = document.getElementById("themeText");

const sidebar = document.getElementById("sidebar");
const overlay = document.getElementById("sidebarOverlay");
const menuBtn = document.getElementById("menuBtn");
const closeSidebarBtn = document.getElementById("closeSidebarBtn");

const chatForm = document.getElementById("chatForm");
const messageInput = document.getElementById("messageInput");
const sendBtn = document.getElementById("sendBtn");

const messagesEl = document.getElementById("messages");
const emptyState = document.getElementById("emptyState");
const typingIndicator = document.getElementById("typingIndicator");

const chatList = document.getElementById("chatList");
const topbarTitle = document.getElementById("topbarTitle");

// ---------- 1. STATE ----------
let conversation = [];   // full history of THIS chat (sent to the backend)
let currentChatId = null; // which saved chat is open (null = not saved yet)
let isWaiting = false;   // true while waiting for the AI answer
let abortController = null;

const REQUEST_TIMEOUT_MS = 60000; // 60 seconds max wait

// markdown settings (chat style: single Enter = new line)
if (window.marked) {
    marked.setOptions({ gfm: true, breaks: true });
}

// ---------- 2. THEME (dark / light) ----------
function applyTheme(theme) {
    rootEl.setAttribute("data-theme", theme);
    localStorage.setItem("chatbot-theme", theme);
    themeIcon.textContent = theme === "dark" ? "☀️" : "🌙";
    themeText.textContent = theme === "dark" ? "Light mode" : "Dark mode";
}

const savedTheme =
    localStorage.getItem("chatbot-theme") ||
    (window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light");
applyTheme(savedTheme);

themeToggle.addEventListener("click", () => {
    applyTheme(rootEl.getAttribute("data-theme") === "dark" ? "light" : "dark");
});

// ---------- 3. SIDEBAR (mobile open / close) ----------
function openSidebar() {
    sidebar.classList.add("open");
    overlay.classList.add("show");
}

function closeSidebar() {
    sidebar.classList.remove("open");
    overlay.classList.remove("show");
}

menuBtn.addEventListener("click", openSidebar);
closeSidebarBtn.addEventListener("click", closeSidebar);
overlay.addEventListener("click", closeSidebar);

// ---------- 4. INPUT BOX ----------
messageInput.addEventListener("input", () => {
    messageInput.style.height = "auto";
    messageInput.style.height = Math.min(messageInput.scrollHeight, 200) + "px";
    updateSendButton();
});

// Enter = send, Shift+Enter = new line
messageInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        chatForm.requestSubmit();
    }
});

function updateSendButton() {
    sendBtn.disabled = isWaiting || messageInput.value.trim() === "";
}

function setWaiting(value) {
    isWaiting = value;
    updateSendButton();
}

// ---------- 5. RENDER MESSAGES ----------
function escapeHtml(text) {
    return text.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

// AI text -> safe HTML (markdown + cleaned by DOMPurify against XSS)
function renderMarkdown(text) {
    if (window.marked && window.DOMPurify) {
        return DOMPurify.sanitize(marked.parse(text));
    }
    return escapeHtml(text).replace(/\n/g, "<br>");
}

function scrollToBottom() {
    messagesEl.scrollTop = messagesEl.scrollHeight;
}

function hideEmptyState() {
    emptyState.classList.add("hidden");
}

function showTyping(show) {
    typingIndicator.classList.toggle("hidden", !show);
    if (show) scrollToBottom();
}

function clearMessageWindow() {
    messagesEl.querySelectorAll(".message:not(.typing-indicator)").forEach((el) => el.remove());
}

async function copyText(text, btn) {
    const oldLabel = btn.textContent;
    try {
        await navigator.clipboard.writeText(text);
        btn.textContent = "Copied!";
    } catch (err) {
        // fallback for older browsers
        const ta = document.createElement("textarea");
        ta.value = text;
        document.body.appendChild(ta);
        ta.select();
        try {
            document.execCommand("copy");
            btn.textContent = "Copied!";
        } catch (e2) {
            btn.textContent = "Failed";
        }
        ta.remove();
    }
    setTimeout(() => { btn.textContent = oldLabel; }, 1500);
}

// language label + copy button for every code block
function enhanceCodeBlocks(container) {
    container.querySelectorAll("pre").forEach((pre) => {
        if (pre.parentElement && pre.parentElement.classList.contains("code-block")) return;

        const code = pre.querySelector("code");
        const match = code ? (code.className || "").match(/language-(\w+)/) : null;
        const lang = match ? match[1] : "code";

        const wrapper = document.createElement("div");
        wrapper.className = "code-block";

        const header = document.createElement("div");
        header.className = "code-header";

        const langLabel = document.createElement("span");
        langLabel.className = "code-lang";
        langLabel.textContent = lang;

        const copyBtn = document.createElement("button");
        copyBtn.className = "code-copy-btn";
        copyBtn.type = "button";
        copyBtn.textContent = "Copy";
        copyBtn.addEventListener("click", () => {
            copyText(code ? code.textContent : pre.textContent, copyBtn);
        });

        header.appendChild(langLabel);
        header.appendChild(copyBtn);

        pre.parentNode.insertBefore(wrapper, pre);
        wrapper.appendChild(header);
        wrapper.appendChild(pre);

        if (code && window.hljs) {
            try { hljs.highlightElement(code); } catch (e) { /* keep plain colors */ }
        }
    });
}

/**
 * Create one message bubble.
 * role    = "user" | "assistant"
 * options = { error: true }  -> red friendly error bubble (plain text)
 */
function createMessage(role, text, options = {}) {
    const isError = options.error === true;

    const msg = document.createElement("div");
    msg.className = isError ? "message assistant error" : "message " + role;

    const avatar = document.createElement("div");
    avatar.className = "avatar";
    avatar.textContent = role === "user" ? "U" : "🤖";

    const bubble = document.createElement("div");
    bubble.className = "bubble";

    const content = document.createElement("div");
    content.className = "msg-content";

    if (role === "user" || isError) {
        content.textContent = text;               // plain text = no HTML injection
    } else {
        content.innerHTML = renderMarkdown(text); // AI answer = markdown
        enhanceCodeBlocks(content);
    }
    bubble.appendChild(content);

    // copy button for AI answers only
    if (role === "assistant" && !isError) {
        const copyBtn = document.createElement("button");
        copyBtn.className = "copy-btn";
        copyBtn.type = "button";
        copyBtn.textContent = "Copy";
        copyBtn.addEventListener("click", () => copyText(text, copyBtn));
        bubble.appendChild(copyBtn);
    }

    msg.appendChild(avatar);
    msg.appendChild(bubble);

    messagesEl.insertBefore(msg, typingIndicator);
    scrollToBottom();
    return msg;
}

// ---------- 6. SEND MESSAGE (frontend -> backend -> AI) ----------
async function sendMessage() {
    const text = messageInput.value.trim();

    // --- validation (same rules as the backend) ---
    if (!text) return;
    if (isWaiting) return;
    hideEmptyState();
    if (text.length > 4000) {
        createMessage("assistant", "⚠️ Message is too long (max 4000 characters).", { error: true });
        return;
    }

    createMessage("user", text);
    conversation.push({ role: "user", content: text });

    messageInput.value = "";
    messageInput.style.height = "auto";
    setWaiting(true);
    showTyping(true);

    abortController = new AbortController();
    const timer = setTimeout(() => abortController.abort(), REQUEST_TIMEOUT_MS);

    try {
        const response = await fetch("/api/chat", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ messages: conversation, chat_id: currentChatId }),
            signal: abortController.signal,
        });

        let data = null;
        try { data = await response.json(); } catch (e) { /* not JSON */ }

        if (!response.ok || !data || data.error) {
            throw new Error(data && data.error ? data.error : "Server error (HTTP " + response.status + ").");
        }

        // --- success: show the AI answer ---
        conversation.push({ role: "assistant", content: data.reply });
        createMessage("assistant", data.reply);

        // remember which chat this is (created on first message)
        if (data.chat_id) currentChatId = data.chat_id;
        loadChatList(); // refresh sidebar (new chat appears / order updates)

    } catch (err) {
        // remove failed user message so the next attempt has a valid history
        conversation.pop();

        let friendly;
        if (err.name === "AbortError") {
            friendly = "⏱ The AI took too long to respond. Please try again.";
        } else if (err instanceof TypeError) {
            friendly = "⚠️ Network error: cannot reach the server. Is the backend running?";
        } else {
            friendly = "⚠️ " + (err.message || "Something went wrong. Please try again.");
        }
        createMessage("assistant", friendly, { error: true });

    } finally {
        clearTimeout(timer);
        abortController = null;
        showTyping(false);
        setWaiting(false);
        messageInput.focus();
    }
}

// ---------- 7. CHAT HISTORY (sidebar) ----------
function updateActiveChatItem(activeId) {
    chatList.querySelectorAll(".chat-item").forEach((item) => {
        item.classList.toggle("active", Number(item.dataset.id) === activeId);
    });
}

function renderChatList(chats) {
    chatList.innerHTML = "";

    if (!chats.length) {
        const p = document.createElement("p");
        p.className = "chat-list-empty";
        p.textContent = "No conversations yet.";
        chatList.appendChild(p);
    }

    chats.forEach((chat) => {
        const item = document.createElement("div");
        item.className = "chat-item";
        item.dataset.id = chat.id;

        const title = document.createElement("span");
        title.className = "chat-item-title";
        title.textContent = chat.title;

        const del = document.createElement("button");
        del.className = "chat-item-delete";
        del.type = "button";
        del.textContent = "✕";
        del.title = "Delete chat";
        del.addEventListener("click", (e) => {
            e.stopPropagation(); // don't open the chat, just delete it
            deleteChat(chat.id);
        });

        item.appendChild(title);
        item.appendChild(del);
        item.addEventListener("click", () => openChat(chat.id));
        chatList.appendChild(item);
    });

    updateActiveChatItem(currentChatId);

    // keep the top bar title in sync with the open chat
    const active = chats.find((c) => c.id === currentChatId);
    topbarTitle.textContent = active ? active.title : "AI Chatbot";
}

async function loadChatList() {
    try {
        const res = await fetch("/api/chats");
        const data = await res.json();
        if (!res.ok) throw new Error(data && data.error ? data.error : "load failed");
        renderChatList(data.chats || []);
    } catch (err) {
        // history is not critical - the chat itself still works
        console.warn("Could not load chat list:", err);
    }
}

async function openChat(chatId) {
    if (isWaiting) return; // don't switch while the AI is working
    try {
        const res = await fetch("/api/chats/" + chatId);
        const data = await res.json();
        if (!res.ok || !data.chat) {
            throw new Error(data && data.error ? data.error : "Could not open this chat.");
        }

        currentChatId = data.chat.id;
        conversation = (data.messages || []).map((m) => ({
            role: m.role,
            content: m.content,
        }));

        // rebuild the chat window
        clearMessageWindow();
        if (conversation.length === 0) {
            emptyState.classList.remove("hidden");
        } else {
            hideEmptyState();
            conversation.forEach((m) => createMessage(m.role, m.content));
        }

        topbarTitle.textContent = data.chat.title || "AI Chatbot";
        updateActiveChatItem(chatId);
        closeSidebar();
    } catch (err) {
        hideEmptyState();
        createMessage("assistant", "⚠️ " + (err.message || "Could not open that chat."), { error: true });
    }
}

async function deleteChat(chatId) {
    if (isWaiting) return;
    if (!window.confirm("Delete this chat permanently?")) return;
    try {
        const res = await fetch("/api/chats/" + chatId, { method: "DELETE" });
        const data = await res.json();
        if (!res.ok) throw new Error(data && data.error ? data.error : "Delete failed.");

        if (currentChatId === chatId) startNewChat(); // it was open -> reset window
        loadChatList();
    } catch (err) {
        window.alert("Could not delete the chat: " + (err.message || err));
    }
}

// ---------- 8. NEW CHAT ----------
function startNewChat() {
    if (isWaiting) return; // don't reset while the AI is working
    conversation = [];
    currentChatId = null;
    clearMessageWindow();
    emptyState.classList.remove("hidden");
    messagesEl.scrollTop = 0;
    topbarTitle.textContent = "AI Chatbot";
    updateActiveChatItem(null);
    closeSidebar();
    messageInput.focus();
}

chatForm.addEventListener("submit", (e) => {
    e.preventDefault();
    sendMessage();
});

document.getElementById("newChatBtn").addEventListener("click", startNewChat);
document.getElementById("topNewChatBtn").addEventListener("click", startNewChat);

// ---------- 9. SUGGESTION CHIPS (fill + send) ----------
document.querySelectorAll(".suggestion-chip").forEach((chip) => {
    chip.addEventListener("click", () => {
        messageInput.value = chip.textContent.trim();
        messageInput.dispatchEvent(new Event("input"));
        chatForm.requestSubmit();
    });
});

// ---------- 10. START ----------
loadChatList();   // show saved chats in the sidebar
updateSendButton();
messageInput.focus();
