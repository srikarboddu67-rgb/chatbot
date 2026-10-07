"""
test_db.py  ->  tests backend/database.py directly (no server needed).

Run:  python backend\\test_db.py
It creates a demo chat, reads it back, then deletes it (self-cleaning).
"""

import sys

# Windows terminals use cp1252 by default -> force UTF-8 so
# symbols (✅ etc.) print without UnicodeEncodeError
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import database


def main():
    database.init_db()
    print("init_db()            -> OK (tables ready)")

    print("1) create chat       ", end="")
    chat_id = database.create_chat("Hello, how are you?")
    print("-> id =", chat_id)

    print("2) add messages      ", end="")
    database.add_message(chat_id, "user", "Hello, how are you?")
    database.add_message(chat_id, "assistant", "I am doing great, thanks!")
    print("-> OK")

    print("3) list chats        ->", database.list_chats())

    print("4) open chat", chat_id, "       ->", database.get_chat(chat_id))
    for m in database.get_messages(chat_id):
        print("     -", m["role"], ":", m["content"])

    print("5) unknown chat 999  ->", database.get_chat(99999))

    print("6) delete chat       ", end="")
    print("-> deleted =", database.delete_chat(chat_id))

    print("7) list after delete ->", database.list_chats())
    print("\nALL DATABASE TESTS PASSED ✅")


if __name__ == "__main__":
    main()
