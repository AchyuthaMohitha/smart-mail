"""
email_classifier.py - Use the trained model to classify an email.

The model is created by train_classifier.py. This file only LOADS it and
asks it for a prediction. Training and using are kept separate on purpose.
"""

import joblib

import config

_model = None  # the loaded model is kept here so we only read the file once


class ModelNotReadyError(Exception):
    """Raised when the model file has not been created yet."""


def model_is_ready():
    """True if train_classifier.py has already produced the model file."""
    return config.MODEL_PATH.exists()


def load_model():
    """Load the saved model from disk (only the first time it is needed)."""
    global _model
    if _model is None:
        if not model_is_ready():
            raise ModelNotReadyError("Model not found. Run:  python train_classifier.py")
        _model = joblib.load(config.MODEL_PATH)
    return _model


def classify_email(subject, body):
    """
    Predict the category of one email.
    Returns (category, confidence), for example ("Urgent", 0.87).
    Confidence is the model's probability for the chosen category (0 to 1).
    """
    text = f"{subject or ''} {body or ''}".strip()
    if not text:
        # Nothing to read: we cannot guess, so treat it as everyday mail.
        return "Routine", 0.0

    model = load_model()
    probabilities = model.predict_proba([text])[0]   # one probability per category
    best_index = probabilities.argmax()
    category = model.classes_[best_index]
    return str(category), float(probabilities[best_index])


# Quick manual test:  python email_classifier.py
if __name__ == "__main__":
    examples = [
        ("Exam moved to tomorrow 9 AM", "Report to Hall B with your hall ticket. This is mandatory."),
        ("Big sale - 80% off!", "Limited time offer, click now to grab the deal."),
        ("Club newsletter", "Photos from last week's meetup are now online."),
        ("Internship applications open", "Apply before the end of next week."),
    ]
    for subject, body in examples:
        category, confidence = classify_email(subject, body)
        print(f"{category:<10} ({confidence:.0%})  <- {subject}")
