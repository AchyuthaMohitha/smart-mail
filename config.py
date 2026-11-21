"""
config.py - All SmartMail settings in one place.

Every other file imports its settings from here, so if a path or
option needs to change, we only change it in this one file.
"""

import os
import secrets
from pathlib import Path

from dotenv import load_dotenv

# The folder that contains this file = the project folder.
BASE_DIR = Path(__file__).resolve().parent

# Read the private .env file (if it exists) into environment variables.
load_dotenv(BASE_DIR / ".env")

# ---------- Folders ----------
DATA_DIR = BASE_DIR / "data"          # training dataset (safe to share)
MODELS_DIR = BASE_DIR / "models"      # trained ML model + evaluation report
INSTANCE_DIR = BASE_DIR / "instance"  # PRIVATE: database, Gmail token, face data

# ---------- Files ----------
DATASET_PATH = DATA_DIR / "emails_dataset.csv"
MODEL_PATH = MODELS_DIR / "email_classifier.joblib"
EVALUATION_PATH = MODELS_DIR / "evaluation.json"            # written by train_classifier.py
DATABASE_PATH = INSTANCE_DIR / "smartmail.db"
GMAIL_CREDENTIALS_PATH = INSTANCE_DIR / "credentials.json"  # downloaded from Google Cloud
GMAIL_TOKEN_PATH = INSTANCE_DIR / "token.json"              # created after first Gmail login
FACE_DATA_PATH = INSTANCE_DIR / "owner_face.npy"            # owner's face "fingerprint"

# ---------- Options ----------
# The four email categories from the PPT (slide 6).
CATEGORIES = ["Urgent", "Important", "Routine", "Spam"]

# Minimum Gmail permissions: read mail + send a reply the user confirmed.
# (No permission to delete or modify the mailbox.)
GMAIL_SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send",
]
GMAIL_FETCH_LIMIT = 25  # how many recent inbox emails to fetch at a time

# Flask needs a secret key to sign the session cookie (Face-Lock state, CSRF token).
FLASK_SECRET_KEY = os.getenv("FLASK_SECRET_KEY", "").strip()
if not FLASK_SECRET_KEY:
    # No key in .env: make a temporary random one.
    # (Works, but you are logged out whenever the app restarts.)
    FLASK_SECRET_KEY = secrets.token_hex(32)
    print("[config] Warning: FLASK_SECRET_KEY not set in .env - using a temporary key.")


def create_folders():
    """Create the data, models and instance folders if they don't exist yet."""
    for folder in (DATA_DIR, MODELS_DIR, INSTANCE_DIR):
        folder.mkdir(exist_ok=True)


# Run "python config.py" to check that the settings load correctly.
if __name__ == "__main__":
    create_folders()
    print("Project folder :", BASE_DIR)
    print("Dataset file   :", DATASET_PATH)
    print("Model file     :", MODEL_PATH)
    print("Database file  :", DATABASE_PATH)
    print("Categories     :", CATEGORIES)
    print("Secret key set :", "yes" if os.getenv("FLASK_SECRET_KEY") else "no (temporary key)")
    print("Folders created: data/, models/, instance/")
