"""
email_pipeline.py - The SmartMail pipeline from PPT slide 4:

    Fetch emails -> AI Classifier -> Priority Score -> save to Database -> Dashboard

Emails come from two sources:
    "demo"  - DEMO DATA from demo_emails.py (works immediately, no setup)
    "gmail" - your real Gmail (after the one-time Gmail setup)

Both sources are read by the SAME parser (email_parser.py), and classified by the
SAME trained model, using the email's subject + body. Nothing is hard-coded.
"""

from datetime import datetime

import database
import demo_emails
import gmail_client
from email_classifier import classify_email
from email_parser import parse_raw_email
from priority_scorer import score_email
from reply_drafter import needs_follow_up


def clean_email(raw):
    """
    Make sure an email has every field we need, even if it is broken or incomplete.
    Bad or missing values are replaced with safe defaults instead of crashing.
    """
    def text(key):
        value = raw.get(key)
        return str(value).strip() if value is not None else ""

    received_at = text("received_at")
    try:
        received_at = datetime.fromisoformat(received_at).isoformat(timespec="seconds")
    except ValueError:
        received_at = ""   # unknown date

    sender_email = text("sender_email")
    return {
        "id": text("id"),
        "thread_id": raw.get("thread_id"),
        "header_message_id": raw.get("header_message_id"),
        "sender_name": text("sender_name") or sender_email or "Unknown sender",
        "sender_email": sender_email,
        "subject": text("subject") or "(no subject)",
        "body": text("body"),
        "received_at": received_at,
    }


def process_email(raw, source, trusted_domains):
    """Run ONE email through the pipeline and return the record to store (without the body)."""
    email = clean_email(raw)
    real_subject = "" if email["subject"] == "(no subject)" else email["subject"]

    # The model reads the email's real subject + body. Nothing else decides the category.
    category, confidence = classify_email(real_subject, email["body"])
    score, reasons = score_email(email["sender_name"], email["sender_email"],
                                 real_subject, email["body"], category, trusted_domains)
    return {
        "source": source,
        "message_id": email["id"],
        "thread_id": email["thread_id"],
        "header_message_id": email["header_message_id"],
        "sender_name": email["sender_name"],
        "sender_email": email["sender_email"],
        "subject": email["subject"],
        "received_at": email["received_at"],
        "category": category,
        "confidence": round(confidence, 3),
        "priority_score": score,
        "score_reasons": reasons,
        "follow_up": needs_follow_up(real_subject, email["body"]),
    }


def process_and_save(raw_emails, source):
    """Process a list of emails and save them. Returns how many were saved."""
    trusted_domains = database.get_trusted_domains()
    saved = 0
    for raw in raw_emails:
        if not raw.get("id"):
            continue   # without an id we can't store it or find it again
        database.save_email(process_email(raw, source, trusted_domains))
        saved += 1
    return saved


def read_demo_email(demo_id):
    """Read one DEMO email through the same parser that reads Gmail messages."""
    raw_bytes = demo_emails.get_demo_raw(demo_id)
    if raw_bytes is None:
        raise LookupError("This demo email no longer exists. Click 'Load demo emails' again.")
    email = parse_raw_email(raw_bytes)
    email["id"] = demo_id
    return email


def load_demo_emails():
    """Run all DEMO emails through the pipeline."""
    return process_and_save([read_demo_email(i) for i in demo_emails.get_demo_ids()], "demo")


def fetch_gmail_emails():
    """Fetch recent Gmail emails and run them through the pipeline."""
    return process_and_save(gmail_client.fetch_recent_emails(), "gmail")


def get_full_email(email_record):
    """
    Read the ORIGINAL email again from where it came from (the body is not stored in
    the database). Returns the parsed email: sender, to, cc, subject, date, body, attachments.
    """
    if email_record["source"] == "demo":
        return read_demo_email(email_record["message_id"])
    return gmail_client.get_full_email(email_record["message_id"])
