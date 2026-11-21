"""
email_parser.py - Read an email in its original internet format (MIME) safely.

Gmail gives us every email in the standard format used by all mail servers
(RFC 5322 / MIME). That format can contain:
  - encoded headers, e.g.  Subject: =?utf-8?b?8J+OuCBPcGVuIE1pYw==?=  (emoji, Telugu, ₹ ...)
  - several versions of the body, e.g. plain text AND HTML ("multipart/alternative")
  - attachments and inline images ("multipart/mixed", "multipart/related")
  - different character sets (utf-8, iso-8859-1, windows-1252 ...)
  - "transfer encodings" such as base64 or quoted-printable
Python's built-in `email` package understands all of this, so we use it instead of
writing our own decoder. The text we show is the ORIGINAL message content.

The demo emails are turned into the same format and read by this same file,
so demo emails and Gmail emails follow exactly the same path.

Safety: HTML is never shown as HTML. It is converted to plain text, so scripts,
tracking images and fake buttons inside an email cannot run in SmartMail.
"""

import re
from email import policy
from email.parser import BytesParser
from email.utils import getaddresses, parsedate_to_datetime

from bs4 import BeautifulSoup

# HTML tags that start a new line when the email is turned into plain text.
BLOCK_TAGS = ["p", "div", "tr", "table", "ul", "ol", "li", "h1", "h2", "h3", "h4",
              "h5", "h6", "blockquote", "section", "article", "header", "footer", "hr"]


# ---------------------------------------------------------------- HTML -> text
def html_to_text(html):
    """Turn an HTML email into readable plain text (keeps link addresses visible)."""
    soup = BeautifulSoup(html or "", "html.parser")
    for tag in soup(["script", "style", "head", "title", "meta", "noscript"]):
        tag.decompose()   # remove parts that are not readable text

    # Keep link addresses, e.g. "Register here (https://...)", so the user can see
    # where a button really goes, and the link summarizer can find it.
    for link in soup.find_all("a", href=True):
        address = link["href"].strip()
        if address.startswith(("http://", "https://")) and address not in link.get_text():
            link.append(f" ({address})")

    for line_break in soup.find_all("br"):
        line_break.replace_with("\n")
    for item in soup.find_all("li"):
        item.insert(0, "• ")          # bullet goes INSIDE the list item, on the same line
    for cell in soup.find_all(["td", "th"]):
        cell.insert_after("  ")
    for block in soup.find_all(BLOCK_TAGS):
        block.insert_before("\n")
        block.insert_after("\n")

    lines = [re.sub(r"[ \t\xa0]+", " ", line).strip() for line in soup.get_text().splitlines()]
    text = "\n".join(lines)
    return re.sub(r"\n{3,}", "\n\n", text).strip()   # at most one empty line in a row


# ---------------------------------------------------------------- small helpers
def header_text(message, name):
    """Return a header as normal text (encoded headers are decoded automatically)."""
    try:
        value = message.get(name)
    except Exception:      # a badly broken header: treat it as missing
        return ""
    return str(value).strip() if value is not None else ""


def parse_addresses(value):
    """'Rahul <rahul@x.com>, sneha@y.com' -> [{"name": "Rahul", "email": "rahul@x.com"}, ...]"""
    people = []
    for name, address in getaddresses([value or ""]):
        if name or address:
            people.append({"name": name.strip(), "email": address.strip()})
    return people


def parse_date(value):
    """Turn a Date header into 'YYYY-MM-DDTHH:MM:SS' in this computer's time zone ('' if invalid)."""
    try:
        moment = parsedate_to_datetime(value)
    except (TypeError, ValueError, IndexError):
        return ""
    if moment.tzinfo is not None:
        moment = moment.astimezone()          # convert to local time
    return moment.replace(tzinfo=None).isoformat(timespec="seconds")


def part_text(part):
    """Decode one text part using its own character set, without crashing on bad data."""
    try:
        text = part.get_content()
    except Exception:      # unknown character set or broken encoding
        payload = part.get_payload(decode=True) or b""
        text = payload.decode("utf-8", errors="replace")
    return text.replace("\r\n", "\n")


def find_body(message):
    """
    Choose the body to show. Returns (text, body_format, has_html).
    We prefer the plain-text version. If there is none, we convert the HTML version.
    """
    try:
        plain_part = message.get_body(preferencelist=("plain",))
        html_part = message.get_body(preferencelist=("html",))
    except Exception:
        plain_part = html_part = None

    if plain_part is not None:
        text = part_text(plain_part).strip()
        if text:
            return text, "plain", html_part is not None
    if html_part is not None:
        return html_to_text(part_text(html_part)), "html", True
    return "", "none", False


def list_attachments(message):
    """Names and types of attachments. Attachments are NOT opened or saved."""
    attachments = []
    try:
        for part in message.iter_attachments():
            attachments.append({"filename": part.get_filename() or "(unnamed file)",
                                "content_type": part.get_content_type()})
    except Exception:
        pass
    return attachments


# ---------------------------------------------------------------- main function
def parse_raw_email(raw_bytes):
    """
    Read one complete email (bytes) and return a simple dict:
      sender_name, sender_email, to, cc, subject, date_header, received_at,
      header_message_id, body, body_format ("plain" / "html" / "none"), has_html, attachments
    """
    message = BytesParser(policy=policy.default).parsebytes(raw_bytes or b"")

    senders = parse_addresses(header_text(message, "From"))
    sender = senders[0] if senders else {"name": "", "email": ""}
    date_header = header_text(message, "Date")
    body, body_format, has_html = find_body(message)

    return {
        "sender_name": sender["name"],
        "sender_email": sender["email"],
        "to": parse_addresses(header_text(message, "To")),
        "cc": parse_addresses(header_text(message, "Cc")),
        "subject": header_text(message, "Subject"),
        "date_header": date_header,
        "received_at": parse_date(date_header),
        "header_message_id": header_text(message, "Message-ID"),
        "body": body,
        "body_format": body_format,
        "has_html": has_html,
        "attachments": list_attachments(message),
    }
