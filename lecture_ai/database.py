"""
SQLite database layer.
Handles sessions, transcripts, and QR codes with transaction safety.
"""

import sqlite3
import threading
from datetime import datetime
from pathlib import Path

from . import config

_lock = threading.Lock()


def _get_connection() -> sqlite3.Connection:
    """Create a new connection (one per call — thread safe)."""
    conn = sqlite3.connect(str(config.DB_PATH), timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db():
    """Create tables if they don't exist."""
    with _lock:
        conn = _get_connection()
        try:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    start_time TEXT NOT NULL,
                    end_time TEXT,
                    last_activity TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS transcripts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id INTEGER NOT NULL,
                    timestamp TEXT NOT NULL,
                    text TEXT NOT NULL,
                    FOREIGN KEY (session_id) REFERENCES sessions(id)
                );

                CREATE TABLE IF NOT EXISTS qr_codes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id INTEGER NOT NULL,
                    url TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    image_path TEXT,
                    FOREIGN KEY (session_id) REFERENCES sessions(id)
                );
            """)
            conn.commit()
        finally:
            conn.close()


# ---- Session CRUD ----

def create_session() -> int:
    """Create a new session. Returns the session id."""
    now = datetime.now().isoformat()
    with _lock:
        conn = _get_connection()
        try:
            cur = conn.execute(
                "INSERT INTO sessions (start_time, last_activity) VALUES (?, ?)",
                (now, now),
            )
            conn.commit()
            return cur.lastrowid
        finally:
            conn.close()


def end_session(session_id: int):
    """Mark a session as ended."""
    now = datetime.now().isoformat()
    with _lock:
        conn = _get_connection()
        try:
            conn.execute(
                "UPDATE sessions SET end_time = ?, last_activity = ? WHERE id = ?",
                (now, now, session_id),
            )
            conn.commit()
        finally:
            conn.close()


def touch_session(session_id: int):
    """Update last_activity timestamp for stale detection."""
    now = datetime.now().isoformat()
    with _lock:
        conn = _get_connection()
        try:
            conn.execute(
                "UPDATE sessions SET last_activity = ? WHERE id = ?",
                (now, session_id),
            )
            conn.commit()
        finally:
            conn.close()


def get_active_session():
    """Return the currently active (un-ended) session row, or None."""
    conn = _get_connection()
    try:
        row = conn.execute(
            "SELECT * FROM sessions WHERE end_time IS NULL ORDER BY id DESC LIMIT 1"
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def get_stale_sessions(minutes: int):
    """Return sessions that have been inactive for more than `minutes`."""
    from datetime import timedelta

    cutoff = (datetime.now() - timedelta(minutes=minutes)).isoformat()
    conn = _get_connection()
    try:
        rows = conn.execute(
            """
            SELECT * FROM sessions
            WHERE end_time IS NULL
              AND last_activity < ?
            """,
            (cutoff,),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


# ---- Transcript CRUD ----

def add_transcript(session_id: int, text: str):
    """Insert a transcript chunk."""
    now = datetime.now().isoformat()
    with _lock:
        conn = _get_connection()
        try:
            conn.execute(
                "INSERT INTO transcripts (session_id, timestamp, text) VALUES (?, ?, ?)",
                (session_id, now, text),
            )
            conn.commit()
        finally:
            conn.close()


def get_session_transcripts(session_id: int) -> list[dict]:
    """Get all transcripts for a session, ordered by time."""
    conn = _get_connection()
    try:
        rows = conn.execute(
            "SELECT * FROM transcripts WHERE session_id = ? ORDER BY timestamp",
            (session_id,),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


# ---- QR Code CRUD ----

def add_qr_code(session_id: int, url: str, image_path: str | None) -> int:
    """Insert a QR code entry. Returns the row id."""
    now = datetime.now().isoformat()
    with _lock:
        conn = _get_connection()
        try:
            cur = conn.execute(
                "INSERT INTO qr_codes (session_id, url, timestamp, image_path) VALUES (?, ?, ?, ?)",
                (session_id, url, now, image_path),
            )
            conn.commit()
            return cur.lastrowid
        finally:
            conn.close()


def get_session_qr_codes(session_id: int) -> list[dict]:
    """Get all QR code entries for a session."""
    conn = _get_connection()
    try:
        rows = conn.execute(
            "SELECT * FROM qr_codes WHERE session_id = ? ORDER BY timestamp",
            (session_id,),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_session_qr_urls(session_id: int) -> list[dict]:
    """Get all QR URLs with their latest timestamps for dedup logic."""
    conn = _get_connection()
    try:
        rows = conn.execute(
            """
            SELECT url, MAX(timestamp) as last_seen, image_path
            FROM qr_codes
            WHERE session_id = ?
            GROUP BY url
            """,
            (session_id,),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()
