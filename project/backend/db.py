import os
import sqlite3
import asyncio
from typing import List, Dict, Optional
from datetime import datetime

DB_TYPE = os.getenv("DATABASE_TYPE", "sqlite")
DB_URL = os.getenv("DATABASE_URL", "sqlite:///./chat.db")

# SQLite connection
def get_sqlite_conn():
    conn = sqlite3.connect(DB_URL.replace("sqlite:///", ""))
    conn.row_factory = sqlite3.Row
    return conn

# PostgreSQL connection (if needed)
def get_postgres_conn():
    import psycopg2
    import psycopg2.extras
    # Parse postgres URL: postgresql://user:pass@host/db
    url = DB_URL.replace("postgresql://", "")
    if "@" in url:
        auth, host_db = url.split("@")
        user, password = auth.split(":")
        host, db = host_db.split("/")
    else:
        raise ValueError("Invalid PostgreSQL URL")
    
    conn = psycopg2.connect(
        user=user,
        password=password,
        host=host,
        database=db
    )
    return conn

def init_db():
    """Initialize database schema"""
    if DB_TYPE == "sqlite":
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
    else:
        conn = get_postgres_conn()
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id SERIAL PRIMARY KEY,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
        conn.close()

def save_message(role: str, content: str):
    """Save a message to database"""
    if DB_TYPE == "sqlite":
        conn = get_sqlite_conn()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO messages (role, content) VALUES (?, ?)",
            (role, content)
        )
        conn.commit()
        conn.close()
    else:
        conn = get_postgres_conn()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO messages (role, content) VALUES (%s, %s)",
            (role, content)
        )
        conn.commit()
        conn.close()

def get_history(limit: int = 50) -> List[Dict]:
    """Get recent chat history"""
    if DB_TYPE == "sqlite":
        conn = get_sqlite_conn()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT role, content, timestamp FROM messages ORDER BY id DESC LIMIT ?",
            (limit,)
        )
        rows = cursor.fetchall()
        conn.close()
        return [{"role": r["role"], "content": r["content"], "timestamp": r["timestamp"]} 
                for r in reversed(rows)]
    else:
        conn = get_postgres_conn()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cursor.execute(
            "SELECT role, content, timestamp FROM messages ORDER BY id DESC LIMIT %s",
            (limit,)
        )
        rows = cursor.fetchall()
        conn.close()
        return [dict(r) for r in reversed(rows)]

def clear_history():
    """Clear all chat history"""
    if DB_TYPE == "sqlite":
        conn = get_sqlite_conn()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM messages")
        conn.commit()
        conn.close()
    else:
        conn = get_postgres_conn()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM messages")
        conn.commit()
        conn.close()
