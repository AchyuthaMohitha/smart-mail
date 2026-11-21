"""
reply_drafter.py - Detect common requests and prepare reply DRAFTS.

PPT slide 8:
    "Meeting request" -> reply with your calendar link
    "Share notes"     -> reply with your drive link
    "Fee reminder"    -> mark the email for follow-up
We also added "Please confirm" -> a short confirmation reply.

IMPORTANT: this file never sends anything. It only prepares text.
Sending happens in app.py, and only after the user ticks a confirmation
box and clicks "Send".
"""

import re

# Each rule: a name, the phrases that trigger it, and what to do.
# action "draft"     -> prepare a reply
# action "follow_up" -> mark the email for follow-up (no reply)
REQUEST_RULES = [
    {
        "name": "Meeting request",
        # Only real REQUESTS count ("can we meet", "meet me"), not every use of the
        # word "meet" (e.g. "meet your HoD" in a notice is not a request to you).
        "patterns": [r"\b(can|could|shall|should) (we|you) meet\b", r"\bmeet (me|us)\b",
                     r"\b(schedule|set up|arrange|book) a (call|meeting|slot)\b", r"\bmeeting request\b",
                     r"\bavailable (to|for) (meet|discuss|talk|a call)\b", r"\bcatch up\b"],
        "action": "draft",
        "needs_setting": "calendar_link",
        "template": (
            "Hello {sender_first_name},\n\n"
            "Thank you for reaching out. I would be happy to meet. "
            "Please pick a time that suits you from my calendar:\n{calendar_link}\n\n"
            "Regards,\n{user_name}"
        ),
    },
    {
        "name": "Share notes",
        "patterns": [r"share (the |your )?(\w+ )?notes", r"send (me )?(the |your )?(\w+ )?notes",
                     r"\bnotes\b.*\b(please|share|send)\b", r"share (the )?slides"],
        "action": "draft",
        "needs_setting": "drive_link",
        "template": (
            "Hi {sender_first_name},\n\n"
            "Sure! You can find the notes in this folder:\n{drive_link}\n\n"
            "Let me know if you have any trouble opening it.\n\n"
            "Cheers,\n{user_name}"
        ),
    },
    {
        "name": "Fee reminder",
        "patterns": [r"\bfees?\b.*\b(due|reminder|payment|pay)\b", r"\b(due|reminder|payment)\b.*\bfees?\b",
                     r"payment (is )?due"],
        "action": "follow_up",
        "needs_setting": None,
        "template": None,
    },
    {
        "name": "Confirmation request",
        "patterns": [r"\b(please|kindly|can you) (please )?confirm\b", r"\brsvp\b"],
        "action": "draft",
        "needs_setting": None,
        "template": (
            "Hi {sender_first_name},\n\n"
            "Yes, I confirm. Thank you for checking.\n\n"
            "Regards,\n{user_name}"
        ),
    },
]

MISSING_LINK_TEXT = {
    "calendar_link": "[add your calendar link in Settings]",
    "drive_link": "[add your drive link in Settings]",
}


AUTOMATED_SENDER_WORDS = ["noreply", "no-reply", "donotreply", "do-not-reply", "mailer-daemon"]


def is_automated_sender(sender_email):
    """True for addresses like no-reply@... - nobody reads replies sent to them."""
    address = (sender_email or "").lower()
    return any(word in address for word in AUTOMATED_SENDER_WORDS)


def detect_requests(subject, body):
    """Return the list of rules whose patterns appear in the email."""
    text = f"{subject or ''} {body or ''}".lower()
    matched = []
    for rule in REQUEST_RULES:
        if any(re.search(pattern, text) for pattern in rule["patterns"]):
            matched.append(rule)
    return matched


def needs_follow_up(subject, body):
    """True if the email matches a 'follow_up' rule (for example a fee reminder)."""
    return any(rule["action"] == "follow_up" for rule in detect_requests(subject, body))


def reply_subject(subject):
    """Add 'Re: ' in front of the subject, unless it is already there."""
    subject = (subject or "").strip() or "(no subject)"
    return subject if subject.lower().startswith("re:") else f"Re: {subject}"


def first_name(sender_name):
    """'Dr. Meera Nair' -> 'Meera'.  Empty name -> 'there' (as in 'Hello there')."""
    titles = {"dr", "dr.", "prof", "prof.", "mr", "mr.", "ms", "ms.", "mrs", "mrs."}
    words = [w for w in (sender_name or "").split() if w.lower() not in titles]
    return words[0] if words else "there"


def draft_replies(email, settings, category=None):
    """
    Build reply drafts for one email.
    email    = dict with sender_name, sender_email, subject, body
    settings = dict with user_name, calendar_link, drive_link
    Returns a list of dicts: name, action, subject, body, warning
    A reply is only suggested when it makes sense: never for spam, and never
    for automated "no-reply" senders (follow-up flags still work for those).
    """
    if category == "Spam":
        return []   # never suggest replying to spam
    automated = is_automated_sender(email.get("sender_email"))

    drafts = []
    for rule in detect_requests(email.get("subject"), email.get("body")):
        if rule["action"] == "follow_up":
            drafts.append({"name": rule["name"], "action": "follow_up",
                           "subject": None, "body": None, "warning": None})
            continue
        if automated:
            continue   # nobody would read a reply to a no-reply address

        warning = None
        setting_name = rule["needs_setting"]
        values = {
            "sender_first_name": first_name(email.get("sender_name")),
            "user_name": settings.get("user_name") or "SmartMail user",
            "calendar_link": settings.get("calendar_link") or MISSING_LINK_TEXT["calendar_link"],
            "drive_link": settings.get("drive_link") or MISSING_LINK_TEXT["drive_link"],
        }
        if setting_name and not settings.get(setting_name):
            warning = f"Your {setting_name.replace('_', ' ')} is not set yet - add it in Settings or edit the draft."

        drafts.append({
            "name": rule["name"],
            "action": "draft",
            "subject": reply_subject(email.get("subject")),
            "body": rule["template"].format(**values),
            "warning": warning,
        })
    return drafts


# Quick check:  python reply_drafter.py
if __name__ == "__main__":
    test_email = {"sender_name": "Dr. Meera Nair", "subject": "Meeting request",
                  "body": "Could we schedule a meeting this week?"}
    for draft in draft_replies(test_email, {"user_name": "Student", "calendar_link": "https://calendar.example/student"}):
        print(draft["name"], "|", draft["subject"])
        print(draft["body"])
