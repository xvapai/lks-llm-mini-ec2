import os
import sqlite3
from typing import List, Dict

DB_TYPE = os.getenv("DATABASE_TYPE", "sqlite")
DB_URL = os.getenv("DATABASE_URL", "sqlite:///./chat.db")

def get_sqlite_conn():
    db_path = DB_URL.replace("sqlite:///./", "").replace("sqlite:///", "")
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_sqlite_conn()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()
    print("✓ Database initialized")

def save_message(role: str, content: str):
    conn = get_sqlite_conn()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO messages (role, content) VALUES (?, ?)",
        (role, content)
    )
    conn.commit()
    conn.close()

def get_history(limit: int = 50) -> List[Dict]:
    conn = get_sqlite_conn()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT role, content, timestamp FROM messages ORDER BY id DESC LIMIT ?",
        (limit,)
    )
    rows = cursor.fetchall()
    conn.close()
    return [{"role": r["role"], "content": r["content"], "timestamp": str(r["timestamp"])}
            for r in reversed(rows)]

def clear_history():
    conn = get_sqlite_conn()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM messages")
    conn.commit()
    conn.close()
