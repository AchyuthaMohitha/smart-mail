# SmartMail – AI-Powered Mail Automation System

SmartMail reads your emails, sorts them into **Urgent / Important / Routine / Spam** with a
machine-learning model (TF-IDF + Naive Bayes), gives every email a **priority score from 0 to 100**
using transparent rules, and shows them on a colour-coded **web dashboard**. It also shows each
email in a **reading page**, prepares **reply drafts** (sent only after you confirm),
**summarizes links**, and can be protected with **Face-Lock** (with Google sign-in as the fallback).

It opens immediately with **16 DEMO emails**. Connecting Gmail and Face-Lock are optional.

---

## 1. What is real, what is demo, what is not implemented

| | Status |
|---|---|
| **DEMO emails** (`demo_emails.py`) | Made-up emails written for this project, marked **DEMO** everywhere in the app and in the message itself (`X-SmartMail-Demo` header). All addresses use the reserved `.example` domain. **They are not Gmail messages.** |
| Reading emails from **Gmail** | Implemented: Gmail API + OAuth, downloads each message in its original raw format and decodes it with Python's `email` package. Tested with fake Gmail responses that contain realistic raw emails. **Not tested against a live Gmail account by the developer** – see section 8 for how you test it. |
| Classification | Implemented: the trained TF-IDF + Naive Bayes model reads the **subject + body** of every email (demo or Gmail). Nothing is hard-coded. |
| Priority score | Implemented: transparent rules (category, sender, keywords, deadlines). Every score shows its reasons. |
| Reading page | Implemented: original From / To / Cc / date / subject / attachments / full body, with SmartMail's analysis shown **separately**. |
| Reply drafts | Implemented as **drafts only**, suggested only for real requests (meeting, notes, confirmation). Sent only when you tick a confirmation box. Demo replies are never sent. |
| Link summarizer | Implemented (extractive summary, safety checks). Needs internet. |
| Face-Lock | Implemented (OpenCV + face_recognition), optional; fallback = Google sign-in (needs Gmail set up). |
| Not implemented | Opening attachments, showing HTML emails as HTML (they are shown as safe plain text), liveness check for Face-Lock, mobile app, Outlook/Yahoo, voice reading, WhatsApp (PPT "future scope"). |

---

## 2. Project structure

```
SmartMail/
├── app.py                  Flask web app – pages, buttons, Face-Lock screen (connects all modules)
├── config.py               All settings and file paths in one place
├── email_pipeline.py       The pipeline: fetch → read → classify → score → save (PPT slide 4)
├── email_parser.py         Reads real emails (MIME): encoded headers, multipart, HTML → text
├── demo_emails.py          16 DEMO emails (made-up student inbox), built as real MIME messages
├── train_classifier.py     Trains + evaluates the ML model (run separately)
├── email_classifier.py     Loads the trained model and predicts a category
├── priority_scorer.py      0–100 score from category, sender, keywords, deadlines
├── reply_drafter.py        Detects real requests and prepares reply drafts
├── link_summarizer.py      Safely downloads a linked page and makes a 3-sentence summary
├── gmail_client.py         Gmail API + OAuth (optional)
├── face_lock.py            Face verification with OpenCV + face_recognition (optional)
├── database.py             SQLite tables and queries (metadata only, no email bodies)
├── data/emails_dataset.csv 120 labelled TRAINING emails (30 per category)
├── models/                 email_classifier.joblib + evaluation.json (made by training)
├── instance/               PRIVATE: smartmail.db, Gmail token, face data (not in Git)
├── templates/              HTML pages (Jinja2)
├── static/                 style.css + app.js (webcam code)
├── tests/                  121 automated tests (unittest)
├── docs/VIVA_GUIDE.md      Simple explanation, PPT mapping, viva Q&A
├── requirements.txt        Core packages
├── requirements-face.txt   Optional Face-Lock packages
├── .env.example            Template for your private .env file
└── .gitignore              Keeps .venv, .env and instance/ out of Git
```

---

## 3. Updating your existing SmartMail folder

1. Extract the ZIP and copy **everything inside its `SmartMail` folder** into your SmartMail folder,
   choosing **Replace** when Windows asks. Your `.venv`, `.env` and `instance` folder are not touched.
2. Delete these three files that are no longer used:
   ```powershell
   del mock_emails.py, templates\setup.html, templates\login.html
   ```
3. Your existing database is upgraded automatically on the next start: the old sample emails
   and the old SmartMail password are removed, and the new DEMO emails are loaded.
   Your settings (name, links, trusted domains) are kept.
4. **If you registered your face in the old version**, SmartMail now starts on the lock screen.
   Unlock with your face, then open **Settings → Face-Lock → Re-register my face** (after
   connecting Gmail) so the Google sign-in fallback is set up. If you can't unlock, delete
   `instance\owner_face.npy` and start again.

No new packages are needed. The trained model is unchanged, so you don't need to retrain.

---

## 4. Run SmartMail (Windows, VS Code terminal)

Run these from your SmartMail folder:

```powershell
.\.venv\Scripts\Activate.ps1
python app.py
```

Then open **http://127.0.0.1:5000** in your browser. Stop the app with **Ctrl + C**.

First time on a new computer? Do these steps once before `python app.py`:

```powershell
pip install -r requirements.txt
copy .env.example .env
python -c "import secrets; print(secrets.token_hex(32))"
#   -> paste the printed text after FLASK_SECRET_KEY= in .env
python train_classifier.py
```

> If PowerShell says *"running scripts is disabled"*, run this once:
> `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` and activate again.
> (Or use a **Command Prompt** terminal: `.venv\Scripts\activate.bat`.)

### What you should see
- No password screen. The dashboard opens directly with the message *"Loaded 16 DEMO emails"*
  and a purple banner explaining that **DEMO** emails are made-up examples.
- Sidebar with counts per category, follow-ups, Model report and Settings.
- Summary cards, **All / Gmail / Demo** tabs, a search box, and the email list sorted by priority
  score. Every demo row has a purple **DEMO** badge.
- Click any row to open the **reading page**:
  - left: the **original email** (From, To, Received, Date header, attachments, full body)
  - right: **SmartMail analysis** (predicted category, model confidence, priority score with
    reasons), then **Reply** and **Links in this email**.

---

## 5. Demo workflow (for your presentation)

| Step | Do this | What it shows (PPT slide) |
|---|---|---|
| 1 | Open the dashboard | Colour-coded inbox, counts, priority scores (6, 7, 11) |
| 2 | Click **Urgent**, then search “placement” | Category view + search |
| 3 | Open *“Shortlisted: TechNova Systems…”* | Original email vs. SmartMail analysis; **Why this score?** (7) |
| 4 | Open *“₹1 FLASH SALE 🔥…”* | Spam, score 0; HTML-only email shown as safe text (6) |
| 5 | Open *“mini project - meet tomorrow evening?”* | Meeting request detected → suggested draft (8) |
| 6 | **Settings** → add your name + calendar link → Save → re-open step 5 | Draft now contains your link |
| 7 | Tick the box → **Send (demo email – not really sent)** | Confirmation required; demo replies are never sent (8) |
| 8 | Open *“Reminder: Odd semester 2026 fee…”* | Automatically marked for follow-up ⚑ (8) |
| 9 | Open *“Weekly Byte #14”* → **Summarize** | 3-sentence summary of a real Wikipedia page (9) |
| 10 | Open the *(no subject)* email → **Summarize** | Broken email + dead link handled gracefully (9) |
| 11 | Open *“End Semester Examinations…”* | Attachment listed (not opened), recipient is a mailing list |
| 12 | **Model report** | Measured accuracy, precision/recall/F1, confusion matrix (6) |
| 13 | **Fetch from Gmail** → **Gmail** tab | Your real inbox through Gmail API (4, 12) |
| 14 | **Settings → Face-Lock** → register → **Lock SmartMail** → verify face | Face-Lock (10) |

Step 9 needs internet. Steps 13 and 14 need the optional setup in sections 8 and 9.
Be ready to explain that the model gets several demo emails "wrong" (section 7). That is the honest output of the model.

---

## 6. Run the automated tests

```powershell
python -m unittest discover tests -v
```

The tests use a temporary database, so your real data is never touched. They don't use the internet
or a real Gmail account: Gmail is replaced by a fake that returns **realistic raw emails**
(encoded headers, quoted-printable, base64, Latin-1, HTML-only, nested multipart with attachment).

Results when this version was built (Linux, Python 3.11, same package versions as `requirements.txt`):

| Setup | Result |
|---|---|
| Core packages only (no Face-Lock) | 121 tests, all passed, 7 skipped (face tests) |
| Core + Face-Lock packages | 121 tests, all passed, 3 skipped (real-photo tests) |
| Core + Face-Lock + real test photos | 121 tests, all passed |

The app was also checked in a real browser (Chromium):
- clicking rows opens the correct reading page
- category and score are identical in the list and the reading page for every email checked
- scripts inside HTML emails do not run, and tabs and search work
- reply drafts appear only for real requests
- lock screen with a simulated webcam: stranger rejected, owner unlocked, Lock button locks again

It has **not** been run on Windows or against a live Gmail account.

Optional real-photo face test: put `owner1.jpg`, `owner2.jpg` (two photos of you) and `other.jpg`
(someone else) in a folder, then:

```powershell
$env:SMARTMAIL_FACE_TEST_DIR = "C:\path\to\that\folder"
python -m unittest tests.test_face_lock tests.test_app -v
```

---

## 7. Classifier results (measured, not made up)

**On the training dataset** (`python train_classifier.py`, 120 short labelled emails, 90 train / 30 held-out test):

| Measurement | Result |
|---|---|
| Accuracy on the 30 held-out test emails | **66.67 %** |
| 5-fold cross-validation accuracy | **79.17 % ± 4.56 %** |

**On the 16 DEMO emails** (`python demo_emails.py` compares the model with *our own* label;
the app never uses our label):

| Measurement | Result |
|---|---|
| Model agrees with our label | **9 of 16** |
| Predicted Urgent | 10 of 16 (we think only 3 are really urgent) |
| Typical mistakes | Open-mic night, a message from Amma and a phishing email predicted *Urgent* |

**Why:** the training emails are short one-line sentences, while real emails are longer and use
many words the model has never seen (about one third of the distinct words in the demo emails are unknown to it).
In training, words like "pm", "at", "tonight" and "24 hours" appeared mostly in Urgent examples,
so long, natural emails drift towards Urgent. The dashboard shows the model's real output; nothing is
adjusted to make it look better.
**How to improve (next step):** add longer, realistic labelled emails to `data/emails_dataset.csv`
(for example your own anonymised emails), run `python train_classifier.py`, then
`python demo_emails.py` to measure again. Don't copy the demo emails into the training data,
or the demo check stops being a fair test.

---

## 8. Connect Gmail (optional) and test with your own emails

SmartMail uses the official **Gmail API with OAuth 2.0**: you sign in on Google's own page, and
SmartMail never sees your Gmail password. It asks for only two permissions:
**read mail** (`gmail.readonly`) and **send mail** (`gmail.send`, used only after you confirm a reply).
It cannot delete or change anything in your mailbox.

1. Go to <https://console.cloud.google.com/> and create a project, e.g. *SmartMail*.
2. **APIs & Services → Library**, search **Gmail API**, click **Enable**.
3. Open **Google Auth Platform** (called *OAuth consent screen* in older menus):
   - App name *SmartMail*, your email as support and developer contact, audience **External**.
   - Under **Audience → Test users**, add **your own Gmail address**.
4. **Clients → Create client → Application type: Desktop app** → Create → **Download JSON**.
5. Rename the file to `credentials.json` and move it to `SmartMail\instance\credentials.json`.
   **Never paste its contents into code or chat.** `instance/` is excluded from Git.
6. Stop the app, then sign in once and run the built-in check:
   ```powershell
   python gmail_client.py
   ```
   A browser opens. Choose your account; Google warns *"Google hasn't verified this app"* – that is
   normal for your own test app, click **Continue** and allow access. The terminal then prints a
   check of your 5 latest emails: sender, subject, body length, whether it came from the plain-text
   or HTML part, attachments, and SmartMail's category and score. Nothing in Gmail is changed.
7. Start the app (`python app.py`), click **Fetch from Gmail** (your 25 latest inbox emails),
   then use the **Gmail** tab to see only real emails.

**Checklist for testing with your Gmail** (please tell me anything that looks wrong):
- [ ] Subjects and sender names with non-English characters or emoji look the same as in Gmail.
- [ ] Opening an email shows the same text as Gmail (for HTML-only newsletters, as plain text).
- [ ] To / Cc / date are correct; attachments are listed by name.
- [ ] Category and score are the same in the list and on the reading page.
- [ ] Sending a reply to **your own second address** works only after ticking the confirmation box.

Notes:
- Email **bodies are not stored** in SQLite. They are downloaded again from Gmail when you open an email,
  so the reading page always shows the original message.
- While your Google app is in *Testing* mode, Google expires the sign-in after about 7 days.
  If fetching fails with a sign-in message, run `python gmail_client.py` again.
- Add your college's email domain under **Settings → Trusted sender domains** so real college emails
  get the trusted-sender bonus (the default only covers the demo domain `university.example`).

---

## 9. Face-Lock (optional)

There is **no separate SmartMail password**. The app only listens on your own computer
(`127.0.0.1`) and opens directly. If you want a lock, turn on Face-Lock:

```powershell
pip install -r requirements-face.txt
pip install --no-deps face_recognition==1.3.0
python face_lock.py
```

The last command should print *"Face libraries are installed."* Then:

1. **Connect Gmail first** (section 8). If your face is not recognised, you unlock SmartMail by
   signing in with the **same Google account**, so Face-Lock needs Gmail.
2. **Settings → Face-Lock** → **Start camera** (allow camera access) → sit alone in good light →
   **Register my face and turn on Face-Lock**.
3. Click **🔒 Lock SmartMail** in the sidebar. Closing the browser usually locks it too, unless
   your browser restores sessions on restart.
4. On the lock screen: **Start camera** → **Verify my face**, or **Sign in with Google instead**.

How it works: the browser takes one picture → OpenCV checks the face is bright enough →
face_recognition turns the face into 128 numbers → these are compared with the owner's numbers
(match if the distance is ≤ 0.5). **Detecting a face is not enough – it must match.**
Only the 128 numbers are saved (`instance/owner_face.npy`), never the photo.
After 5 failed attempts (face or Google), unlocking is blocked for 60 seconds.

**Recovery:** if you can't unlock at all (for example Gmail credentials were deleted), delete
`instance\owner_face.npy` on your computer. That turns Face-Lock off.

---

## 10. Security decisions

- **Secrets** live in `.env` and `instance/`, never in source code; `.gitignore` excludes them.
- **No SmartMail password**: the server listens only on `127.0.0.1`. Optional Face-Lock with a
  Google sign-in fallback (the password is typed on Google's page, never in SmartMail).
- **CSRF protection**: every form sends a secret token; cookies are `HttpOnly` and `SameSite=Lax`.
- **Minimum Gmail permissions** (read + send); nothing is sent, deleted or changed without your
  explicit confirmation. No reply is ever suggested to spam or to `no-reply` addresses.
- **Safe email display**: HTML emails are converted to plain text, so scripts, tracking images and
  fake buttons in an email never run; link addresses are written out so you can see where they go.
  Attachments are listed by name only and never opened.
- **Link summarizer** opens links only when you click, only http/https on ports 80/443, blocks
  localhost/private network addresses (also after redirects), uses timeouts and a 2 MB limit, and
  can only summarize links that are inside that email.
- **Privacy**: SQLite stores metadata only (sender, subject, date, category, score); no email bodies.

---

## 11. Troubleshooting

| Problem | Fix |
|---|---|
| `ModuleNotFoundError` | Activate the venv first: `.\.venv\Scripts\Activate.ps1` |
| Red banner “ML model is missing” | Run `python train_classifier.py`, then restart `python app.py` |
| “This demo email no longer exists” | You still have old sample rows: click **Load demo emails** |
| “Your form expired” | Refresh the page (happens after a restart without `FLASK_SECRET_KEY` in `.env`) |
| Gmail: “Not logged in” / fetching fails | Run `python gmail_client.py` again |
| Gmail email opens with “Could not load the original email” | Check your internet connection; the body is read live from Gmail |
| Face-Lock button missing in Settings | Connect Gmail first, and install the face packages |
| Camera doesn't open | Use `http://127.0.0.1:5000`, allow camera access, close other apps using the webcam |
| Locked out | Use **Sign in with Google instead**, or delete `instance\owner_face.npy` |
| Port 5000 already in use | Close the other program, or change `port=5000` at the bottom of `app.py` |
| Database is locked | OneDrive can lock files while syncing: pause OneDrive or move the project outside it |

---

## 12. Known limitations

- The classifier was trained on 120 short, hand-written examples, so it over-predicts *Urgent* on
  longer, natural emails (section 7). This is the main thing to improve.
- Gmail reading was tested with realistic fake Gmail responses, not with a live account.
- Very large Gmail messages (big attachments) take longer to open, because the whole original
  message is downloaded to read it. Attachments are never saved.
- HTML emails are shown as plain text: layout, colours and images are not shown.
- Face-Lock has no liveness check, so a good printed photo of the owner might pass. The Google
  fallback is only as strong as your Google account. If your browser is already signed in to Google,
  anyone at your computer can use it.
- Stored categories are calculated when an email is loaded. After retraining, click
  **Load demo emails** / **Fetch from Gmail** to classify again with the new model.
- Flask's built-in server is for your own computer only, not for public hosting.
