"""
database.py - Everything SmartMail stores in SQLite.

What we store (only what the app needs):
  emails   - metadata only: sender, subject, date, category, score, reasons, follow-up flag.
             The email BODY is NOT stored. It is read again from Gmail (or from the
             demo data) when you open an email, so private message text stays in Gmail.
  replies  - a log of replies you confirmed: to, subject, time, status (no body text).
  settings - app settings: your name, calendar link, drive link, trusted domains,
             the Gmail address allowed to unlock Face-Lock, failed-unlock counter.
"""

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime

import config

DEFAULT_SETTINGS = {
    "user_name": "",
    "calendar_link": "",
    "drive_link": "",
    "trusted_domains": "university.example",
}


@contextmanager
def open_db():
    """Open the database, give it to the caller, then save (commit) and close it."""
    connection = sqlite3.connect(config.DATABASE_PATH)
    connection.row_factory = sqlite3.Row      # lets us use row["subject"] instead of row[3]
    try:
        yield connection
        connection.commit()
    finally:
        connection.close()


def init_db():
    """Create the tables if they don't exist yet. Safe to run every time the app starts."""
    config.create_folders()
    with open_db() as db:
        db.executescript("""
            CREATE TABLE IF NOT EXISTS emails (
                id             INTEGER PRIMARY KEY AUTOINCREMENT,
                source         TEXT NOT NULL,          -- 'demo' or 'gmail'
                message_id     TEXT NOT NULL UNIQUE,   -- Gmail id or demo id
                thread_id      TEXT,
                header_message_id TEXT,                -- needed to reply in the same thread
                sender_name    TEXT,
                sender_email   TEXT,
                subject        TEXT,
                received_at    TEXT,
                category       TEXT,
                confidence     REAL,
                priority_score INTEGER,
                score_reasons  TEXT,                   -- JSON list of strings
                follow_up      INTEGER DEFAULT 0,      -- 1 = marked for follow-up
                processed_at   TEXT
            );
            CREATE TABLE IF NOT EXISTS replies (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                email_id   INTEGER NOT NULL,
                to_address TEXT,
                subject    TEXT,
                status     TEXT,                       -- 'sent' or 'not sent (demo email)'
                created_at TEXT
            );
            CREATE TABLE IF NOT EXISTS settings (
                key   TEXT PRIMARY KEY,
                value TEXT
            );
        """)
        # Clean-up of data from older SmartMail versions:
        # the old sample emails were replaced by the new demo emails,
        # and the old SmartMail password was replaced by Face-Lock + Google sign-in.
        db.execute("DELETE FROM replies WHERE email_id IN (SELECT id FROM emails WHERE source = 'sample')")
        db.execute("DELETE FROM emails WHERE source = 'sample'")
        db.execute("DELETE FROM settings WHERE key IN ('password_hash', 'samples_loaded_once')")


def now_text():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


# ---------------------------------------------------------------- emails
def save_email(record):
    """
    Insert a processed email, or update it if we already have it (same message_id).
    The follow-up flag is only set when the email is new, so your own changes stay.
    """
    with open_db() as db:
        db.execute("""
            INSERT INTO emails (source, message_id, thread_id, header_message_id, sender_name,
                                sender_email, subject, received_at, category, confidence,
                                priority_score, score_reasons, follow_up, processed_at)
            VALUES (:source, :message_id, :thread_id, :header_message_id, :sender_name,
                    :sender_email, :subject, :received_at, :category, :confidence,
                    :priority_score, :score_reasons, :follow_up, :processed_at)
            ON CONFLICT(message_id) DO UPDATE SET
                sender_name = excluded.sender_name, sender_email = excluded.sender_email,
                subject = excluded.subject, received_at = excluded.received_at,
                category = excluded.category, confidence = excluded.confidence,
                priority_score = excluded.priority_score, score_reasons = excluded.score_reasons,
                processed_at = excluded.processed_at
        """, {
            "source": record["source"],
            "message_id": record["message_id"],
            "thread_id": record.get("thread_id"),
            "header_message_id": record.get("header_message_id"),
            "sender_name": record.get("sender_name"),
            "sender_email": record.get("sender_email"),
            "subject": record.get("subject"),
            "received_at": record.get("received_at"),
            "category": record["category"],
            "confidence": record.get("confidence", 0.0),
            "priority_score": record["priority_score"],
            "score_reasons": json.dumps(record.get("score_reasons", [])),
            "follow_up": 1 if record.get("follow_up") else 0,
            "processed_at": now_text(),
        })


def row_to_dict(row):
    """Turn a database row into a normal dict and decode the JSON reasons list."""
    email = dict(row)
    email["score_reasons"] = json.loads(email.get("score_reasons") or "[]")
    return email


def get_emails(category=None, search=None, follow_up_only=False, source=None):
    """Return emails, highest priority first. Optional filters: category, search, follow-up, source."""
    sql = "SELECT * FROM emails WHERE 1=1"
    params = []
    if source:
        sql += " AND source = ?"
        params.append(source)
    if category:
        sql += " AND category = ?"
        params.append(category)
    if follow_up_only:
        sql += " AND follow_up = 1"
    if search:
        sql += " AND (subject LIKE ? OR sender_name LIKE ? OR sender_email LIKE ?)"
        like = f"%{search}%"
        params += [like, like, like]
    sql += " ORDER BY priority_score DESC, received_at DESC"
    with open_db() as db:
        return [row_to_dict(row) for row in db.execute(sql, params).fetchall()]


def get_email(email_id):
    """Return one email by its database id, or None."""
    with open_db() as db:
        row = db.execute("SELECT * FROM emails WHERE id = ?", (email_id,)).fetchone()
    return row_to_dict(row) if row else None


def count_emails(source=None):
    """
    Return counts like {"total": 16, "Urgent": 3, ..., "follow_up": 1, "demo": 16, "gmail": 0}.
    With source="demo" or "gmail", the category counts only include that source.
    """
    where, params = ("WHERE source = ?", (source,)) if source else ("", ())
    counts = {category: 0 for category in config.CATEGORIES}
    with open_db() as db:
        for row in db.execute(f"SELECT category, COUNT(*) AS n FROM emails {where} GROUP BY category", params):
            counts[row["category"]] = row["n"]
        follow_where = "WHERE follow_up = 1" + (" AND source = ?" if source else "")
        counts["follow_up"] = db.execute(f"SELECT COUNT(*) FROM emails {follow_where}", params).fetchone()[0]
        for name in ("demo", "gmail"):
            counts[name] = db.execute("SELECT COUNT(*) FROM emails WHERE source = ?", (name,)).fetchone()[0]
    counts["total"] = sum(counts[c] for c in config.CATEGORIES)
    return counts


def set_follow_up(email_id, value):
    with open_db() as db:
        db.execute("UPDATE emails SET follow_up = ? WHERE id = ?", (1 if value else 0, email_id))


def delete_emails_from_source(source):
    """Delete stored metadata for 'demo' or 'gmail' emails (this never touches Gmail itself)."""
    with open_db() as db:
        ids = [row[0] for row in db.execute("SELECT id FROM emails WHERE source = ?", (source,))]
        db.executemany("DELETE FROM replies WHERE email_id = ?", [(i,) for i in ids])
        db.execute("DELETE FROM emails WHERE source = ?", (source,))
    return len(ids)


# ---------------------------------------------------------------- replies
def save_reply(email_id, to_address, subject, status):
    with open_db() as db:
        db.execute("INSERT INTO replies (email_id, to_address, subject, status, created_at) VALUES (?, ?, ?, ?, ?)",
                   (email_id, to_address, subject, status, now_text()))


def get_replies(email_id):
    with open_db() as db:
        rows = db.execute("SELECT * FROM replies WHERE email_id = ? ORDER BY id DESC", (email_id,)).fetchall()
    return [dict(row) for row in rows]


# ---------------------------------------------------------------- settings
def get_setting(key, default=None):
    with open_db() as db:
        row = db.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
    if row is not None:
        return row["value"]
    return DEFAULT_SETTINGS.get(key, default)


def set_setting(key, value):
    with open_db() as db:
        db.execute("INSERT INTO settings (key, value) VALUES (?, ?) "
                   "ON CONFLICT(key) DO UPDATE SET value = excluded.value", (key, str(value)))


def get_user_settings():
    """The settings used by reply drafts and priority scoring."""
    return {key: get_setting(key) for key in DEFAULT_SETTINGS}


def get_trusted_domains():
    text = get_setting("trusted_domains") or ""
    return [d.strip().lower() for d in text.split(",") if d.strip()]


# Quick check:  python database.py
if __name__ == "__main__":
    init_db()
    print("Database ready at", config.DATABASE_PATH)
    print("Email counts:", count_emails())
