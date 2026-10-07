"""
database.py  ->  all SQLite (chatbot.db) operations.

Tables (created automatically on first run):

  chats                          messages
  +----+-----------+------+      +----+---------+------+---------+
  | id | title     | ...  |      | id | chat_id | role | content |
  +----+-----------+------+      +----+---------+------+---------+
  |  1 | Hello...  |      |      |  1 |    1    | user | Hello   |
  |  2 | Python... |      |      |  2 |    1    | assi | Hi!     |
  +----+-----------+------+      +----+---------+------+---------+

How to run the self-test:  python backend\\test_db.py
"""

import os
import sqlite3
from contextlib import contextmanager

# project folder = one level above this file
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_FOLDER = os.path.join(BASE_DIR, "database")
DB_PATH = os.path.join(DB_FOLDER, "chatbot.db")


# ---------------------------------------------------------------
# Connection helper: opens -> runs -> commits -> closes (always!)
# ---------------------------------------------------------------
@contextmanager
def db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # rows can be used like dictionaries
    try:
        yield conn
        conn.commit()     # save the changes
    finally:
        conn.close()      # always close (avoids "database is locked")


def init_db():
    """Create the tables if they don't exist yet (safe to run many times)."""
    os.makedirs(DB_FOLDER, exist_ok=True)
    with db_connection() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS chats (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                title      TEXT    NOT NULL,
                created_at TEXT    NOT NULL DEFAULT (datetime('now')),
                updated_at TEXT    NOT NULL DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS messages (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id    INTEGER NOT NULL,
                role       TEXT    NOT NULL CHECK (role IN ('user', 'assistant')),
                content    TEXT    NOT NULL,
                created_at TEXT    NOT NULL DEFAULT (datetime('now')),
                FOREIGN KEY (chat_id) REFERENCES chats(id) ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_messages_chat
                ON messages(chat_id);
            """
        )


# ---------------------------------------------------------------
# CHATS
# ---------------------------------------------------------------
def create_chat(title):
    """Insert a new chat and return its id."""
    with db_connection() as conn:
        cur = conn.execute("INSERT INTO chats (title) VALUES (?)", (title,))
        return cur.lastrowid


def list_chats():
    """All chats, newest activity first (sidebar history)."""
    with db_connection() as conn:
        rows = conn.execute(
            "SELECT id, title, created_at, updated_at "
            "FROM chats ORDER BY updated_at DESC, id DESC"
        ).fetchall()
        return [dict(row) for row in rows]


def get_chat(chat_id):
    """One chat by id, or None if it doesn't exist."""
    with db_connection() as conn:
        row = conn.execute(
            "SELECT id, title, created_at, updated_at FROM chats WHERE id = ?",
            (chat_id,),
        ).fetchone()
        return dict(row) if row else None


def delete_chat(chat_id):
    """Delete a chat + all its messages. Returns True if something was deleted."""
    with db_connection() as conn:
        conn.execute("DELETE FROM messages WHERE chat_id = ?", (chat_id,))
        cur = conn.execute("DELETE FROM chats WHERE id = ?", (chat_id,))
        return cur.rowcount > 0


# ---------------------------------------------------------------
# MESSAGES
# ---------------------------------------------------------------
def add_message(chat_id, role, content):
    """Save one message and bump the chat's updated_at time."""
    with db_connection() as conn:
        conn.execute(
            "INSERT INTO messages (chat_id, role, content) VALUES (?, ?, ?)",
            (chat_id, role, content),
        )
        conn.execute(
            "UPDATE chats SET updated_at = datetime('now') WHERE id = ?",
            (chat_id,),
        )


def get_messages(chat_id):
    """All messages of one chat, oldest first."""
    with db_connection() as conn:
        rows = conn.execute(
            "SELECT role, content, created_at FROM messages "
            "WHERE chat_id = ? ORDER BY id",
            (chat_id,),
        ).fetchall()
        return [dict(row) for row in rows]
