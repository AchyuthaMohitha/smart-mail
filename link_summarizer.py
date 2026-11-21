"""
link_summarizer.py - Find links in an email, read the web page safely,
and make a short 3-sentence summary (PPT slide 9).

How the summary works (no paid AI needed):
  1. Download the page and keep only the readable paragraphs.
  2. Count how often each meaningful word appears in the whole page.
  3. Give every sentence a score = average frequency of its words.
  4. Pick the 3 best sentences and show them in their original order.
This is called "extractive summarization" (we pick sentences, we don't write new ones).

Safety rules before downloading anything:
  - Only http:// and https:// links, on the normal ports (80 / 443).
  - The website's address must be a PUBLIC internet address. Links to your own
    computer (localhost) or private networks (192.168.x.x, 10.x.x.x ...) are
    refused, so a malicious email can't make SmartMail poke at your local network.
  - Short timeouts, at most 3 redirects (each one checked again), at most 2 MB.
  - Pages are only fetched when YOU click "Summarize" - never automatically,
    because some links (like "unsubscribe" links) do something when opened.
"""

import ipaddress
import re
import socket
from collections import Counter
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup
from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS

MAX_PAGE_BYTES = 2 * 1024 * 1024        # 2 MB
MAX_REDIRECTS = 3
TIMEOUT_SECONDS = (5, 10)                # (connect timeout, read timeout)
SUMMARY_SENTENCES = 3
WORDS_PER_MINUTE = 200                   # average reading speed, for "reading time"
HEADERS = {"User-Agent": "SmartMail-LinkSummarizer/1.0 (student project)"}

URL_PATTERN = re.compile(r"https?://[^\s<>\"'()\[\]{}]+", re.IGNORECASE)


class LinkError(Exception):
    """A friendly error message we can show to the user."""


# ---------------------------------------------------------------- finding links
def extract_links(text):
    """Return the unique http/https links found in the text, in order."""
    links = []
    for match in URL_PATTERN.findall(text or ""):
        link = match.rstrip(".,;:!?")          # remove punctuation stuck to the end
        if link not in links:
            links.append(link)
    return links


# ---------------------------------------------------------------- safety checks
def check_url_is_safe(url):
    """Raise LinkError if the URL is not safe to download. Returns nothing if it is fine."""
    parts = urlparse(url)
    if parts.scheme not in ("http", "https"):
        raise LinkError("Only http:// and https:// links can be summarized.")
    if not parts.hostname:
        raise LinkError("This link has no website name.")
    if parts.username or parts.password:
        raise LinkError("Links containing a username or password are not opened.")
    if parts.port not in (None, 80, 443):
        raise LinkError("Links to unusual ports are not opened.")

    try:
        addresses = socket.getaddrinfo(parts.hostname, None)
    except socket.gaierror:
        raise LinkError("This website could not be found (it may not exist or you may be offline).")

    for address in addresses:
        ip = ipaddress.ip_address(address[4][0])
        if not ip.is_global:
            raise LinkError("This link points to a private or local network address, so it was blocked.")


# ---------------------------------------------------------------- downloading
def download_page(url):
    """Download a page safely. Returns the page text (HTML). Raises LinkError on problems."""
    current_url = url
    for _ in range(MAX_REDIRECTS + 1):
        check_url_is_safe(current_url)
        try:
            response = requests.get(current_url, headers=HEADERS, timeout=TIMEOUT_SECONDS,
                                    allow_redirects=False, stream=True)
        except requests.exceptions.Timeout:
            raise LinkError("The website took too long to respond.")
        except requests.exceptions.RequestException:
            raise LinkError("Could not connect to the website.")

        if response.status_code in (301, 302, 303, 307, 308):
            next_url = response.headers.get("Location")
            response.close()
            if not next_url:
                raise LinkError("The website sent a broken redirect.")
            current_url = urljoin(current_url, next_url)   # check it again in the next loop
            continue

        if response.status_code != 200:
            response.close()
            raise LinkError(f"The website answered with an error (HTTP {response.status_code}).")

        content_type = response.headers.get("Content-Type", "").lower()
        if "text/html" not in content_type and "text/plain" not in content_type:
            response.close()
            raise LinkError("This link is not a normal web page (it may be a file or an image).")

        content = b""
        for chunk in response.iter_content(chunk_size=65536):
            content += chunk
            if len(content) > MAX_PAGE_BYTES:
                response.close()
                raise LinkError("The page is too large to summarize.")
        encoding = response.encoding or "utf-8"
        return content.decode(encoding, errors="replace")

    raise LinkError("The link redirected too many times.")


# ---------------------------------------------------------------- reading + summarizing
def extract_readable_text(html):
    """Return (title, text) with only the readable paragraphs of a web page."""
    soup = BeautifulSoup(html, "html.parser")
    title = soup.title.get_text(strip=True) if soup.title else ""

    # Remove parts of the page that are not the article itself.
    for tag in soup(["script", "style", "noscript", "nav", "header", "footer", "aside", "form"]):
        tag.decompose()

    paragraphs = [p.get_text(" ", strip=True) for p in soup.find_all("p")]
    paragraphs = [p for p in paragraphs if len(p.split()) >= 6]
    text = " ".join(paragraphs) if paragraphs else soup.get_text(" ", strip=True)
    text = re.sub(r"\[\d+\]", "", text)          # remove reference marks like [12]
    text = re.sub(r"\s+", " ", text).strip()
    return title, text


def split_sentences(text):
    """Split text into sentences at . ! or ? followed by a space."""
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()]


def summarize_text(text, sentence_count=SUMMARY_SENTENCES):
    """Pick the most important sentences from the text (extractive summary)."""
    sentences = [s for s in split_sentences(text) if 6 <= len(s.split()) <= 60]
    if len(sentences) <= sentence_count:
        return sentences

    def content_words(sentence):
        words = re.findall(r"[a-z]+", sentence.lower())
        return [w for w in words if w not in ENGLISH_STOP_WORDS and len(w) > 2]

    frequency = Counter(word for s in sentences for word in content_words(s))
    if not frequency:
        return sentences[:sentence_count]
    highest = max(frequency.values())

    scores = []
    for index, sentence in enumerate(sentences):
        words = content_words(sentence)
        score = sum(frequency[w] / highest for w in words) / len(words) if words else 0
        scores.append((score, index))

    best_indexes = sorted(index for _, index in sorted(scores, reverse=True)[:sentence_count])
    return [sentences[i] for i in best_indexes]


def summarize_html(html):
    """Summarize a page that has already been downloaded. Returns a result dict."""
    title, text = extract_readable_text(html)
    word_count = len(text.split())
    summary = summarize_text(text)
    if not summary:
        raise LinkError("The page has no readable text to summarize.")
    return {
        "title": title or "Untitled page",
        "summary": summary,
        "word_count": word_count,
        "reading_minutes": max(1, round(word_count / WORDS_PER_MINUTE)),
    }


def summarize_link(url):
    """
    Download and summarize one link.
    Always returns a dict: {"ok": True, "url", "title", "summary", ...}
                       or  {"ok": False, "url", "error": "friendly message"}
    """
    try:
        result = summarize_html(download_page(url))
        result.update({"ok": True, "url": url})
        return result
    except LinkError as error:
        return {"ok": False, "url": url, "error": str(error)}
    except Exception:   # anything unexpected: never crash the dashboard
        return {"ok": False, "url": url, "error": "Something went wrong while reading this page."}


# Quick check:  python link_summarizer.py https://en.wikipedia.org/wiki/Email
if __name__ == "__main__":
    import sys
    test_url = sys.argv[1] if len(sys.argv) > 1 else "https://en.wikipedia.org/wiki/Email"
    result = summarize_link(test_url)
    if result["ok"]:
        print(result["title"], f"({result['word_count']} words, ~{result['reading_minutes']} min read)")
        for sentence in result["summary"]:
            print(" -", sentence)
    else:
        print("Could not summarize:", result["error"])
