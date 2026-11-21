"""
gmail_client.py - Read emails from Gmail and send confirmed replies (Gmail API + OAuth).

This module is OPTIONAL. SmartMail works with DEMO emails until you set it up.

Security:
  - OAuth: you log in on Google's own page. SmartMail never sees your password.
  - Only two permissions (config.GMAIL_SCOPES): read mail, and send mail.
    SmartMail cannot delete, archive or change anything in your mailbox.
  - credentials.json (your app's ID) and token.json (your login) are stored in
    the private instance/ folder, which is excluded from Git.
  - Replies are only sent when you confirm them in the dashboard.
  - Messages are downloaded in their original ("raw") format and read by
    email_parser.py, so subjects, names and bodies are shown exactly as sent.

One-time setup (see README "Connect Gmail"):
  1. Put credentials.json from Google Cloud into the instance/ folder.
  2. Run:  python gmail_client.py
     A browser window opens, you log in and allow access, token.json is saved.
"""

import base64
from datetime import datetime
from email.message import EmailMessage

import config
from email_parser import parse_raw_email


class GmailNotReadyError(Exception):
    """Gmail is not set up yet (no credentials.json or not logged in)."""


def is_configured():
    """True if credentials.json is in the instance folder."""
    return config.GMAIL_CREDENTIALS_PATH.exists()


def is_logged_in():
    """True if a saved login (token.json) exists."""
    return config.GMAIL_TOKEN_PATH.exists()


def get_service(allow_browser_login=False):
    """
    Return a Gmail API "service" object we can use to call Gmail.
    If the saved login has expired, it is refreshed automatically.
    A browser login is only started when allow_browser_login=True (from the command line).
    """
    # Imported here so the rest of the app works even if these packages have a problem.
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build

    if not is_configured():
        raise GmailNotReadyError("Gmail is not set up: put credentials.json in the instance folder.")

    credentials = None
    if is_logged_in():
        credentials = Credentials.from_authorized_user_file(str(config.GMAIL_TOKEN_PATH), config.GMAIL_SCOPES)

    if credentials and credentials.expired and credentials.refresh_token:
        try:
            credentials.refresh(Request())
        except Exception:
            credentials = None   # refresh failed: the user must log in again

    if not credentials or not credentials.valid:
        if not allow_browser_login:
            raise GmailNotReadyError("Not logged in to Gmail. Run:  python gmail_client.py")
        flow = InstalledAppFlow.from_client_secrets_file(str(config.GMAIL_CREDENTIALS_PATH), config.GMAIL_SCOPES)
        credentials = flow.run_local_server(port=0)   # opens Google's login page in your browser

    config.GMAIL_TOKEN_PATH.write_text(credentials.to_json(), encoding="utf-8")
    return build("gmail", "v1", credentials=credentials, cache_discovery=False)


# ---------------------------------------------------------------- reading messages
def decode_base64(data):
    """Gmail sends messages in 'URL-safe base64'. Turn it back into bytes."""
    padded = data + "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(padded)


def parse_gmail_message(message):
    """
    Turn one Gmail API message (requested with format="raw") into the dict SmartMail uses.
    The email itself is read by email_parser.py; Gmail adds its id, thread id and
    the time Gmail received the message (internalDate, in milliseconds).
    """
    email = parse_raw_email(decode_base64(message.get("raw", "")))
    email["id"] = message.get("id", "")
    email["thread_id"] = message.get("threadId")
    milliseconds = int(message.get("internalDate", "0") or 0)
    if milliseconds:
        email["received_at"] = datetime.fromtimestamp(milliseconds / 1000).isoformat(timespec="seconds")
    return email


def get_full_email(gmail_id, service=None):
    """Download ONE email in its original format and read it."""
    service = service or get_service()
    message = service.users().messages().get(userId="me", id=gmail_id, format="raw").execute()
    return parse_gmail_message(message)


def fetch_recent_emails(max_results=config.GMAIL_FETCH_LIMIT):
    """Return the most recent inbox emails (with bodies, kept in memory only)."""
    service = get_service()
    result = service.users().messages().list(userId="me", labelIds=["INBOX"], maxResults=max_results).execute()
    return [get_full_email(item["id"], service) for item in result.get("messages", [])]


def get_account_email(service=None):
    """The Gmail address of the account SmartMail is connected to."""
    service = service or get_service()
    return service.users().getProfile(userId="me").execute()["emailAddress"]


# ---------------------------------------------------------------- Google sign-in (Face-Lock fallback)
def sign_in_with_google(timeout_seconds=120):
    """
    Open Google's sign-in page in a new browser tab and return the email address
    of the account the person signed in with. Used to unlock SmartMail when the
    face is not recognised. The password is typed on Google's page, never in SmartMail.
    """
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build

    if not is_configured():
        raise GmailNotReadyError("Gmail is not set up, so Google sign-in is not available.")
    flow = InstalledAppFlow.from_client_secrets_file(str(config.GMAIL_CREDENTIALS_PATH), config.GMAIL_SCOPES)
    credentials = flow.run_local_server(
        port=0, timeout_seconds=timeout_seconds, prompt="select_account",
        success_message="Signed in. You can close this tab and go back to SmartMail.")
    service = build("gmail", "v1", credentials=credentials, cache_discovery=False)
    return get_account_email(service)


# ---------------------------------------------------------------- sending (only after confirmation)
def build_reply_message(to_address, subject, body, in_reply_to=None):
    """Create the reply email. Returns the 'raw' text the Gmail API expects."""
    message = EmailMessage()
    message["To"] = to_address
    message["Subject"] = subject
    if in_reply_to:
        # These two headers make Gmail show the reply in the same conversation.
        message["In-Reply-To"] = in_reply_to
        message["References"] = in_reply_to
    message.set_content(body)
    return base64.urlsafe_b64encode(message.as_bytes()).decode("ascii")


def send_reply(to_address, subject, body, thread_id=None, in_reply_to=None):
    """Send ONE reply. app.py only calls this after the user has confirmed."""
    service = get_service()
    request_body = {"raw": build_reply_message(to_address, subject, body, in_reply_to)}
    if thread_id:
        request_body["threadId"] = thread_id
    sent = service.users().messages().send(userId="me", body=request_body).execute()
    return sent.get("id")


# One-time login + a check of your real emails:  python gmail_client.py
if __name__ == "__main__":
    config.create_folders()
    if not is_configured():
        print(f"credentials.json not found. Put it here: {config.GMAIL_CREDENTIALS_PATH}")
        print("See README section 'Connect Gmail' for how to download it.")
    else:
        from email_classifier import classify_email
        from priority_scorer import score_email

        service = get_service(allow_browser_login=True)
        print("Logged in as", get_account_email(service), "- token saved to", config.GMAIL_TOKEN_PATH)
        print("\nCheck of your 5 latest inbox emails (nothing is changed in Gmail):\n")
        for email in fetch_recent_emails(max_results=5):
            category, confidence = classify_email(email["subject"], email["body"])
            score, _ = score_email(email["sender_name"], email["sender_email"], email["subject"],
                                   email["body"], category)
            print(f"{email['received_at']}  {email['sender_email']}")
            print(f"  Subject : {email['subject'] or '(no subject)'}")
            print(f"  Body    : {len(email['body'])} characters, read from the {email['body_format']} part"
                  f"{', has HTML version' if email['has_html'] else ''}, {len(email['attachments'])} attachment(s)")
            print(f"  Preview : {email['body'][:100].replace(chr(10), ' ')}")
            print(f"  SmartMail: {category} ({confidence:.0%}), priority {score}\n")
