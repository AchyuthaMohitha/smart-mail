"""
priority_scorer.py - Give every email a priority score from 0 to 100.

PPT slide 7: the score depends on
  1. WHO sent the email
  2. KEYWORDS in the message
  3. DEADLINES or times mentioned
...plus the category predicted by the ML classifier (how urgent it is).

This is a simple, transparent POINTS system (not machine learning), so we
can always explain exactly why an email got its score. Every rule adds or
removes points and writes a short reason, which the dashboard shows.
"""

import re

# Starting points for each category predicted by the classifier.
CATEGORY_BASE_POINTS = {"Urgent": 45, "Important": 30, "Routine": 12, "Spam": 0}

# Words in the sender's NAME that usually mean an important person or office.
IMPORTANT_SENDER_WORDS = ["prof", "professor", "dr", "dean", "hod", "principal",
                          "placement", "exam", "examination", "registrar", "accounts"]

# Words in the sender's ADDRESS that usually mean bulk / marketing mail.
BULK_SENDER_WORDS = ["noreply", "no-reply", "newsletter", "offers", "deals", "promo", "marketing"]

URGENT_WORDS = ["urgent", "urgently", "immediately", "asap", "emergency", "mandatory",
                "compulsory", "final reminder", "last date", "deadline", "right away", "action required"]
IMPORTANT_WORDS = ["exam", "examination", "interview", "placement", "internship", "fee", "fees",
                   "assignment", "project", "review", "result", "results", "grade", "grades",
                   "hall ticket", "scholarship", "viva", "submission"]
PROMO_WORDS = ["sale", "discount", "% off", "offer", "cashback", "free", "winner", "won",
               "lucky draw", "prize", "deal", "coupon", "click here"]

WEEKDAYS = r"(monday|tuesday|wednesday|thursday|friday|saturday|sunday)"
MONTHS = r"(january|february|march|april|may|june|july|august|september|october|november|december|jan|feb|mar|apr|jun|jul|aug|sep|sept|oct|nov|dec)"


def find_words(text, word_list):
    """Return the words from word_list that appear in text as whole words."""
    found = []
    for word in word_list:
        if re.search(r"(?<!\w)" + re.escape(word) + r"(?!\w)", text):
            found.append(word)
    return found


def sender_points(sender_name, sender_email, trusted_domains):
    """Points for WHO sent the email. Returns (points, reasons)."""
    points = 0
    reasons = []
    name = (sender_name or "").lower()
    address = (sender_email or "").lower()
    domain = address.split("@")[-1] if "@" in address else ""

    if domain and any(domain == d or domain.endswith("." + d) for d in trusted_domains):
        points += 20
        reasons.append(f"+20 sender is from a trusted domain ({domain})")

    important_words = find_words(name, IMPORTANT_SENDER_WORDS)
    if important_words:
        points += 10
        reasons.append(f"+10 sender looks important ({', '.join(important_words)})")

    if any(word in address for word in BULK_SENDER_WORDS):
        points -= 10
        reasons.append("-10 sender looks like bulk / marketing mail")

    if not address:
        reasons.append("+0 sender is missing")
    return points, reasons


def keyword_points(text):
    """Points for KEYWORDS in the subject and body. Returns (points, reasons)."""
    points = 0
    reasons = []

    urgent = find_words(text, URGENT_WORDS)
    if urgent:
        bonus = min(5 * len(urgent), 15)
        points += bonus
        reasons.append(f"+{bonus} urgent words: {', '.join(urgent)}")

    important = find_words(text, IMPORTANT_WORDS)
    if important:
        bonus = min(4 * len(important), 12)
        points += bonus
        reasons.append(f"+{bonus} important words: {', '.join(important)}")

    promo = find_words(text, PROMO_WORDS)
    if promo:
        penalty = min(5 * len(promo), 15)
        points -= penalty
        reasons.append(f"-{penalty} promotional words: {', '.join(promo)}")
    return points, reasons


def deadline_points(text):
    """Points for DEADLINES or times. Only the closest deadline counts. Returns (points, reasons)."""
    if re.search(r"\b(today|tonight|this (morning|afternoon|evening))\b|\beod\b|within (the next )?\w+ hours?|in \w+ (minutes|hours?)", text):
        return 20, ["+20 deadline is today / within hours"]
    if re.search(r"\btomorrow\b", text):
        return 15, ["+15 deadline is tomorrow"]
    if re.search(r"\b(this|next|by|before|on|until) " + WEEKDAYS + r"\b|\bthis week\b", text):
        return 10, ["+10 deadline this week / on a named day"]
    if re.search(r"\b\d{1,2}(st|nd|rd|th)? " + MONTHS + r"\b|\b" + MONTHS + r" \d{1,2}\b|\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b", text):
        return 6, ["+6 mentions a date"]
    return 0, []


def score_email(sender_name, sender_email, subject, body, category, trusted_domains=("college.edu",)):
    """
    Calculate the priority score (0-100) for one email.
    Returns (score, reasons) where reasons is a list of short explanations.
    """
    text = f"{subject or ''} {body or ''}".lower()
    trusted = [d.strip().lower() for d in trusted_domains if d and d.strip()]

    base = CATEGORY_BASE_POINTS.get(category, 12)
    total = base
    reasons = [f"+{base} category is {category}"]

    for points, rule_reasons in (sender_points(sender_name, sender_email, trusted),
                                 keyword_points(text),
                                 deadline_points(text)):
        total += points
        reasons.extend(rule_reasons)

    if category == "Spam" and total > 15:
        total = 15
        reasons.append("score capped at 15 because the email is Spam")

    score = max(0, min(100, total))   # keep the score between 0 and 100
    return score, reasons


# Quick check with the two examples from PPT slide 7:  python priority_scorer.py
if __name__ == "__main__":
    print(score_email("Prof. Ramesh Kumar", "ramesh.kumar@college.edu",
                      "Exam moved to tomorrow", "The exam is tomorrow. Attendance is mandatory.", "Urgent"))
    print(score_email("MegaMart Deals", "offers@megamart-deals.example",
                      "Big sale: 80% off", "Limited time offer on laptops", "Spam"))
