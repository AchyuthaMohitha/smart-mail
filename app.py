"""
app.py - The SmartMail web application (Flask).

Run:   python app.py
Open:  http://127.0.0.1:5000

This file only handles web pages and buttons. The real work is done by the
other modules (parser, classifier, scorer, drafter, summarizer, Gmail, Face-Lock).

Access control:
  - There is no separate SmartMail password. The app only listens on this computer
    (127.0.0.1), and opens straight to the dashboard.
  - Optional Face-Lock: once the owner registers their face (Settings), SmartMail is
    locked until the face is verified. If the face is not recognised, the owner can
    unlock with Google sign-in instead (the same Google account connected to Gmail).
"""

import json
import secrets
import time
from datetime import datetime

from flask import (Flask, abort, flash, jsonify, redirect, render_template,
                   request, session, url_for)

import config
import database
import email_pipeline
import face_lock
import gmail_client
import link_summarizer
import reply_drafter
from email_classifier import model_is_ready

app = Flask(__name__)
app.config["SECRET_KEY"] = config.FLASK_SECRET_KEY
app.config["SESSION_COOKIE_HTTPONLY"] = True      # JavaScript can't read the session cookie
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"     # other websites can't submit our forms with it
app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024  # webcam pictures up to 5 MB

MAX_FAILED_UNLOCKS = 5     # after 5 failed unlock attempts...
LOCKOUT_SECONDS = 60       # ...unlocking is blocked for 60 seconds

# Pages that work while SmartMail is locked.
LOCK_SCREEN_ENDPOINTS = {"locked", "unlock_face", "unlock_google", "static"}

config.create_folders()
database.init_db()


# ====================================================================== helpers
def get_csrf_token():
    """A random secret per session. Every form sends it back, so other sites can't fake our forms."""
    if "csrf_token" not in session:
        session["csrf_token"] = secrets.token_hex(16)
    return session["csrf_token"]


def face_lock_enabled():
    """Face-Lock is ON once the owner has registered a face."""
    return face_lock.owner_face_registered()


def unlock_session():
    session.clear()                     # fresh session after unlocking
    session["unlocked"] = True
    database.set_setting("failed_unlocks", 0)


def seconds_locked():
    """How many seconds unlocking is still blocked after too many failed attempts."""
    locked_until = float(database.get_setting("locked_until", "0") or 0)
    return max(0, int(locked_until - time.time()))


def record_failed_unlock():
    failures = int(database.get_setting("failed_unlocks", "0") or 0) + 1
    if failures >= MAX_FAILED_UNLOCKS:
        database.set_setting("locked_until", time.time() + LOCKOUT_SECONDS)
        failures = 0
    database.set_setting("failed_unlocks", failures)


def gmail_status():
    if not gmail_client.is_configured():
        return "not_configured"
    if not gmail_client.is_logged_in():
        return "not_logged_in"
    return "ready"


def mask_email(address):
    """'demo.student@gmail.com' -> 'de***@gmail.com' (a hint without showing the full address)."""
    name, _, domain = (address or "").partition("@")
    return f"{name[:2]}***@{domain}" if domain else ""


def is_valid_link(text):
    return text == "" or text.startswith("https://") or text.startswith("http://")


# ====================================================================== every request
@app.before_request
def check_security():
    # 1. Every POST must carry the correct CSRF token.
    if request.method == "POST":
        sent_token = request.form.get("csrf_token") or request.headers.get("X-CSRF-Token")
        if not sent_token or sent_token != session.get("csrf_token"):
            abort(400, "Your form expired. Please go back, refresh the page and try again.")

    # 2. If Face-Lock is on, everything except the lock screen needs an unlocked session.
    if request.endpoint in LOCK_SCREEN_ENDPOINTS:
        return None
    if face_lock_enabled() and not session.get("unlocked"):
        return redirect(url_for("locked"))
    return None


@app.context_processor
def template_helpers():
    """Values every HTML template can use."""
    values = {"csrf_token": get_csrf_token, "categories": config.CATEGORIES,
              "lock_enabled": face_lock_enabled()}
    if request.endpoint not in LOCK_SCREEN_ENDPOINTS:
        values["counts"] = database.count_emails()
        values["gmail_state"] = gmail_status()
    return values


@app.template_filter("nice_date")
def nice_date(value):
    """'2026-10-25T08:15:00' -> '25 Oct 2026, 08:15'"""
    try:
        return datetime.fromisoformat(value).strftime("%d %b %Y, %H:%M")
    except (TypeError, ValueError):
        return "Unknown date"


@app.template_filter("people")
def people(addresses):
    """[{"name": "Rahul", "email": "r@x"}] -> 'Rahul <r@x>'"""
    parts = []
    for person in addresses or []:
        if person["name"] and person["email"]:
            parts.append(f"{person['name']} <{person['email']}>")
        else:
            parts.append(person["name"] or person["email"])
    return ", ".join(parts)


# ====================================================================== Face-Lock screen
@app.route("/locked")
def locked():
    if not face_lock_enabled() or session.get("unlocked"):
        return redirect(url_for("inbox"))
    owner_email = database.get_setting("owner_google_email")
    return render_template("locked.html",
                           face_available=face_lock.is_available(),
                           google_available=bool(owner_email) and gmail_client.is_configured(),
                           owner_hint=mask_email(owner_email))


@app.route("/unlock/face", methods=["POST"])
def unlock_face():
    """Receives a webcam picture from the lock screen (JavaScript) and answers in JSON."""
    wait = seconds_locked()
    if wait:
        return jsonify(ok=False, message=f"Too many failed attempts. Try again in {wait} seconds.")
    data = request.get_json(silent=True) or {}
    try:
        image_bytes = face_lock.data_url_to_bytes(data.get("image"))
        is_match, distance = face_lock.verify_face(image_bytes)
    except face_lock.FaceLockError as error:
        return jsonify(ok=False, message=str(error))

    if not is_match:
        record_failed_unlock()
        return jsonify(ok=False, message="Face did not match the owner. Try again or sign in with Google.")
    unlock_session()
    flash(f"Face verified (distance {distance:.2f}). Welcome back!", "success")
    return jsonify(ok=True, redirect=url_for("inbox"))


@app.route("/unlock/google", methods=["POST"])
def unlock_google():
    """Fallback: unlock by signing in with the owner's Google account."""
    wait = seconds_locked()
    if wait:
        flash(f"Too many failed attempts. Try again in {wait} seconds.", "error")
        return redirect(url_for("locked"))
    owner_email = database.get_setting("owner_google_email")
    if not owner_email:
        flash("Google sign-in is not set up for this Face-Lock.", "error")
        return redirect(url_for("locked"))
    try:
        signed_in_email = gmail_client.sign_in_with_google()
    except Exception:
        flash("Google sign-in was not completed. Please try again.", "error")
        return redirect(url_for("locked"))

    if signed_in_email.strip().lower() != owner_email.strip().lower():
        record_failed_unlock()
        flash("That Google account is not the owner's account.", "error")
        return redirect(url_for("locked"))
    unlock_session()
    flash("Unlocked with Google sign-in.", "success")
    return redirect(url_for("inbox"))


@app.route("/lock", methods=["POST"])
def lock():
    session.clear()
    return redirect(url_for("locked"))


# ====================================================================== inbox
@app.route("/")
def inbox():
    category = request.args.get("category")
    if category not in config.CATEGORIES:
        category = None
    source = request.args.get("source")
    if source not in ("demo", "gmail"):
        source = None
    search = request.args.get("q", "").strip()
    follow_up_only = request.args.get("follow_up") == "1"

    model_ready = model_is_ready()
    # First visit: fill the dashboard with the DEMO emails automatically.
    if model_ready and database.get_setting("demo_loaded_once") != "1":
        count = email_pipeline.load_demo_emails()
        database.set_setting("demo_loaded_once", "1")
        flash(f"Loaded {count} DEMO emails (made-up examples, not your Gmail). "
              "Connect Gmail in Settings to read your real inbox.", "info")
        return redirect(url_for("inbox"))

    emails = database.get_emails(category=category, search=search,
                                 follow_up_only=follow_up_only, source=source)
    title = f"{category} emails" if category else ("Follow-ups" if follow_up_only else "All mail")
    return render_template("inbox.html", emails=emails, title=title, category=category,
                           source=source, search=search, follow_up_only=follow_up_only,
                           model_ready=model_ready, view_counts=database.count_emails(source),
                           active=category or ("follow_up" if follow_up_only else "all"))


@app.route("/emails/load-demo", methods=["POST"])
def load_demo():
    if not model_is_ready():
        flash("The ML model is missing. Run:  python train_classifier.py", "error")
    else:
        count = email_pipeline.load_demo_emails()
        flash(f"{count} DEMO emails classified and scored by the model.", "success")
    return redirect(url_for("inbox"))


@app.route("/emails/fetch-gmail", methods=["POST"])
def fetch_gmail():
    if not model_is_ready():
        flash("The ML model is missing. Run:  python train_classifier.py", "error")
        return redirect(url_for("inbox"))
    try:
        count = email_pipeline.fetch_gmail_emails()
        flash(f"Fetched and classified {count} emails from Gmail.", "success")
    except gmail_client.GmailNotReadyError as error:
        flash(str(error), "error")
    except Exception as error:
        flash(f"Could not fetch from Gmail: {error}", "error")
    return redirect(url_for("inbox", source="gmail"))


@app.route("/emails/clear/<source>", methods=["POST"])
def clear_emails(source):
    if source not in ("demo", "gmail"):
        abort(404)
    count = database.delete_emails_from_source(source)
    flash(f"Removed {count} {source} emails from SmartMail (your Gmail account was not changed).", "success")
    return redirect(url_for("settings"))


# ====================================================================== reading one email
def show_email_page(email_id, summary=None):
    email = database.get_email(email_id)
    if email is None:
        abort(404)

    original = None
    load_error = None
    try:
        original = email_pipeline.get_full_email(email)   # the ORIGINAL message, read again
    except Exception as error:
        load_error = f"Could not load the original email: {error}"

    drafts = []
    links = []
    if original:
        drafts = reply_drafter.draft_replies(
            {"sender_name": original["sender_name"], "sender_email": email["sender_email"],
             "subject": original["subject"], "body": original["body"]},
            database.get_user_settings(), email["category"])
        links = link_summarizer.extract_links(original["body"])

    return render_template(
        "email_detail.html", email=email, original=original, load_error=load_error,
        links=links, summary=summary, drafts=drafts,
        has_draft=any(d["action"] == "draft" for d in drafts),
        can_reply=email["category"] != "Spam" and bool(email["sender_email"])
                  and not reply_drafter.is_automated_sender(email["sender_email"]),
        reply_subject=reply_drafter.reply_subject(email["subject"]),
        replies=database.get_replies(email_id), active=email["category"])


@app.route("/email/<int:email_id>")
def email_detail(email_id):
    return show_email_page(email_id)


@app.route("/email/<int:email_id>/summarize", methods=["POST"])
def summarize(email_id):
    email = database.get_email(email_id)
    if email is None:
        abort(404)
    url = request.form.get("url", "")
    # Only links that are really inside this email can be summarized.
    try:
        allowed_links = link_summarizer.extract_links(email_pipeline.get_full_email(email)["body"])
    except Exception:
        allowed_links = []
    if url not in allowed_links:
        flash("That link is not part of this email.", "error")
        return redirect(url_for("email_detail", email_id=email_id))
    return show_email_page(email_id, summary=link_summarizer.summarize_link(url))


@app.route("/email/<int:email_id>/send", methods=["POST"])
def send_reply(email_id):
    """Send a reply ONLY if the user ticked the confirmation box."""
    email = database.get_email(email_id)
    if email is None:
        abort(404)
    back = redirect(url_for("email_detail", email_id=email_id))
    subject = request.form.get("subject", "").strip()
    body = request.form.get("body", "").strip()

    if request.form.get("confirm") != "yes":
        flash("Reply NOT sent: tick the confirmation box first.", "error")
        return back
    if email["category"] == "Spam":
        flash("SmartMail does not reply to spam.", "error")
        return back
    if not email["sender_email"] or reply_drafter.is_automated_sender(email["sender_email"]):
        flash("This email has no address that accepts replies.", "error")
        return back
    if not subject or not body:
        flash("The reply needs a subject and a message.", "error")
        return back
    if "[add your" in body:
        flash("Replace the [add your ... link] placeholder first (or set the link in Settings).", "error")
        return back

    if email["source"] == "demo":
        database.save_reply(email_id, email["sender_email"], subject, "not sent (demo email)")
        flash("DEMO email: the reply was saved in SmartMail but NOT sent, because this email is made up.", "success")
        return back

    try:
        gmail_client.send_reply(email["sender_email"], subject, body,
                                email.get("thread_id"), email.get("header_message_id"))
    except gmail_client.GmailNotReadyError as error:
        flash(str(error), "error")
        return back
    except Exception as error:
        flash(f"Gmail could not send the reply: {error}", "error")
        return back
    database.save_reply(email_id, email["sender_email"], subject, "sent")
    flash(f"Reply sent to {email['sender_email']}.", "success")
    return back


@app.route("/email/<int:email_id>/follow-up", methods=["POST"])
def toggle_follow_up(email_id):
    if database.get_email(email_id) is None:
        abort(404)
    marked = request.form.get("value") == "1"
    database.set_follow_up(email_id, marked)
    flash("Marked for follow-up." if marked else "Follow-up removed.", "success")
    return redirect(url_for("email_detail", email_id=email_id))


# ====================================================================== settings
@app.route("/settings", methods=["GET", "POST"])
def settings():
    if request.method == "POST":
        calendar_link = request.form.get("calendar_link", "").strip()
        drive_link = request.form.get("drive_link", "").strip()
        if not is_valid_link(calendar_link) or not is_valid_link(drive_link):
            flash("Links must start with https:// (or http://).", "error")
        else:
            database.set_setting("user_name", request.form.get("user_name", "").strip())
            database.set_setting("calendar_link", calendar_link)
            database.set_setting("drive_link", drive_link)
            database.set_setting("trusted_domains", request.form.get("trusted_domains", "").strip())
            flash("Settings saved. Reload demo emails or fetch Gmail again to update priority scores.", "success")
        return redirect(url_for("settings"))
    return render_template("settings.html", settings=database.get_user_settings(),
                           face_available=face_lock.is_available(),
                           face_registered=face_lock.owner_face_registered(),
                           owner_email=database.get_setting("owner_google_email"),
                           credentials_path=config.GMAIL_CREDENTIALS_PATH, active="settings")


@app.route("/settings/face", methods=["POST"])
def register_face():
    """Turn on Face-Lock. Needs Gmail, because Google sign-in is the fallback."""
    if gmail_status() != "ready":
        return jsonify(ok=False, message="Connect Gmail first: Google sign-in is the fallback if your face is not recognised.")
    try:
        owner_email = gmail_client.get_account_email()
    except Exception:
        return jsonify(ok=False, message="Could not read your Gmail address. Run  python gmail_client.py  and try again.")
    data = request.get_json(silent=True) or {}
    try:
        face_lock.register_owner_face(face_lock.data_url_to_bytes(data.get("image")))
    except face_lock.FaceLockError as error:
        return jsonify(ok=False, message=str(error))
    database.set_setting("owner_google_email", owner_email)
    session["unlocked"] = True   # the owner is here right now, so don't lock them out
    flash(f"Face-Lock is ON. Fallback: Google sign-in as {owner_email}.", "success")
    return jsonify(ok=True, redirect=url_for("settings"))


@app.route("/settings/face/remove", methods=["POST"])
def remove_face():
    face_lock.remove_owner_face()
    database.set_setting("owner_google_email", "")
    flash("Face-Lock turned off and the registered face was deleted.", "success")
    return redirect(url_for("settings"))


# ====================================================================== model report
@app.route("/model")
def model_report():
    evaluation = None
    if config.EVALUATION_PATH.exists():
        evaluation = json.loads(config.EVALUATION_PATH.read_text(encoding="utf-8"))
    return render_template("model.html", evaluation=evaluation, active="model")


# ====================================================================== errors
@app.errorhandler(400)
@app.errorhandler(404)
@app.errorhandler(413)
@app.errorhandler(500)
def show_error(error):
    code = getattr(error, "code", 500)
    messages = {404: "Page not found.", 413: "The uploaded picture is too large.",
                500: "Something went wrong inside SmartMail."}
    message = getattr(error, "description", None) if code == 400 else messages.get(code)
    return render_template("error.html", code=code, message=message), code


if __name__ == "__main__":
    print("SmartMail is running. Open http://127.0.0.1:5000 in your browser (Ctrl+C to stop).")
    app.run(host="127.0.0.1", port=5000, debug=False)
