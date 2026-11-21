"""
train_classifier.py - Train and evaluate the SmartMail email classifier.

Run:  python train_classifier.py          (train, evaluate, save)
      python train_classifier.py --tune   (only compare settings, saves nothing)

What it does:
  1. Reads the labelled emails from data/emails_dataset.csv
  2. Splits them into a TRAINING set (75%) and a held-out TEST set (25%)
  3. Trains a TF-IDF + Multinomial Naive Bayes model on the training set
  4. Measures it on the test set (accuracy, precision, recall, F1, confusion matrix)
  5. Also runs 5-fold cross-validation (a more stable number for small datasets)
  6. Re-trains the final model on ALL the data and saves it to models/
  7. Saves the measured results to models/evaluation.json (shown on the Model page)

This file is ONLY for training. The web app loads the saved model through
email_classifier.py and never trains anything itself.
"""

import csv
import json
import sys
from datetime import datetime

import joblib
from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS, TfidfVectorizer
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
from sklearn.model_selection import GridSearchCV, StratifiedKFold, cross_val_score, train_test_split
from sklearn.naive_bayes import MultinomialNB
from sklearn.pipeline import Pipeline

import config

TEST_SIZE = 0.25     # 25% of the emails are kept aside for testing
RANDOM_SEED = 42     # fixed seed = the same split every time (reproducible results)


def load_dataset(path=config.DATASET_PATH):
    """Read the CSV file and return two lists: email texts and their categories."""
    texts = []
    labels = []
    with open(path, newline="", encoding="utf-8") as csv_file:
        for line_number, row in enumerate(csv.DictReader(csv_file), start=2):
            category = (row.get("category") or "").strip()
            text = f"{row.get('subject') or ''} {row.get('body') or ''}".strip()
            if category not in config.CATEGORIES or not text:
                print(f"  Skipping line {line_number}: missing text or unknown category '{category}'")
                continue
            texts.append(text)
            labels.append(category)
    return texts, labels


def build_model():
    """
    Create the ML pipeline:
      TfidfVectorizer -> turns text into numbers (word importance scores)
      MultinomialNB   -> learns which words are typical for each category

    These settings were chosen with "python train_classifier.py --tune", which
    tries several options using cross-validation on the TRAINING emails only.
    Interesting result: removing English stop words made the model WORSE,
    because that list also removes words like "now", "before" and "within",
    which are strong signs of an urgent email.
    """
    return Pipeline([
        ("tfidf", TfidfVectorizer(
            lowercase=True,          # "URGENT" and "urgent" count as the same word
            ngram_range=(1, 1),      # single words (two-word phrases did not help)
            sublinear_tf=True,       # a word repeated 10 times is not 10x more important
        )),
        ("naive_bayes", MultinomialNB(alpha=0.1)),  # alpha = smoothing for unseen words
    ])


def tune_settings(train_texts, train_labels):
    """Try different settings with 5-fold cross-validation on the training set only."""
    options = {
        "tfidf__ngram_range": [(1, 1), (1, 2)],
        "tfidf__stop_words": [None, "english"],
        "naive_bayes__alpha": [0.05, 0.1, 0.3, 0.5, 1.0],
    }
    folds = StratifiedKFold(n_splits=5, shuffle=True, random_state=RANDOM_SEED)
    search = GridSearchCV(build_model(), options, cv=folds, scoring="accuracy")
    search.fit(train_texts, train_labels)
    results = sorted(zip(search.cv_results_["mean_test_score"], search.cv_results_["params"]),
                     key=lambda pair: pair[0], reverse=True)
    print("\nTop 5 settings (cross-validation accuracy on the training set):")
    for score, params in results[:5]:
        print(f"  {score:.2%}  {params}")


def top_words_per_category(model, how_many=8):
    """
    Return the words the model finds most typical for each category (useful for the viva).
    Common words like "the" are skipped in this DISPLAY only - the model still uses them.
    """
    vectorizer = model.named_steps["tfidf"]
    naive_bayes = model.named_steps["naive_bayes"]
    words = vectorizer.get_feature_names_out()
    result = {}
    for index, category in enumerate(naive_bayes.classes_):
        ranked = naive_bayes.feature_log_prob_[index].argsort()[::-1]   # most typical first
        typical = [words[i] for i in ranked if words[i] not in ENGLISH_STOP_WORDS]
        result[category] = typical[:how_many]
    return result


def main():
    config.create_folders()
    print(f"Loading dataset: {config.DATASET_PATH}")
    texts, labels = load_dataset()
    print(f"  {len(texts)} emails loaded")
    for category in config.CATEGORIES:
        print(f"    {category:<10} {labels.count(category)}")

    # ---- 1. Hold out a test set the model never sees during training ----
    train_texts, test_texts, train_labels, test_labels = train_test_split(
        texts, labels, test_size=TEST_SIZE, stratify=labels, random_state=RANDOM_SEED
    )
    print(f"\nTraining on {len(train_texts)} emails, testing on {len(test_texts)} held-out emails")

    if "--tune" in sys.argv:
        tune_settings(train_texts, train_labels)
        return

    model = build_model()
    model.fit(train_texts, train_labels)
    predictions = model.predict(test_texts)

    # ---- 2. Measure on the held-out test set ----
    accuracy = accuracy_score(test_labels, predictions)
    report_text = classification_report(test_labels, predictions, labels=config.CATEGORIES, zero_division=0)
    report_dict = classification_report(test_labels, predictions, labels=config.CATEGORIES,
                                        zero_division=0, output_dict=True)
    matrix = confusion_matrix(test_labels, predictions, labels=config.CATEGORIES)

    print("\n=== Results on the held-out test set (measured) ===")
    print(f"Accuracy: {accuracy:.2%}\n")
    print(report_text)
    print("Confusion matrix (rows = true category, columns = predicted category):")
    print(" " * 11 + "".join(f"{c[:9]:>10}" for c in config.CATEGORIES))
    for category, row in zip(config.CATEGORIES, matrix):
        print(f"{category:<11}" + "".join(f"{value:>10}" for value in row))

    # ---- 3. Cross-validation: train/test 5 times on different splits ----
    folds = StratifiedKFold(n_splits=5, shuffle=True, random_state=RANDOM_SEED)
    cv_scores = cross_val_score(build_model(), texts, labels, cv=folds, scoring="accuracy")
    print(f"\n5-fold cross-validation accuracy: {cv_scores.mean():.2%} (+/- {cv_scores.std():.2%})")
    print("  per fold:", ", ".join(f"{score:.2%}" for score in cv_scores))

    # ---- 4. Train the final model on ALL emails and save it ----
    final_model = build_model()
    final_model.fit(texts, labels)
    joblib.dump(final_model, config.MODEL_PATH)
    print(f"\nFinal model trained on all {len(texts)} emails and saved to {config.MODEL_PATH}")

    top_words = top_words_per_category(final_model)
    print("\nMost typical words per category:")
    for category, words in top_words.items():
        print(f"  {category:<10} {', '.join(words)}")

    # ---- 5. Save the measured results for the dashboard's Model page ----
    evaluation = {
        "trained_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "dataset_size": len(texts),
        "train_size": len(train_texts),
        "test_size": len(test_texts),
        "test_accuracy": round(accuracy, 4),
        "per_category": {
            c: {
                "precision": round(report_dict[c]["precision"], 4),
                "recall": round(report_dict[c]["recall"], 4),
                "f1": round(report_dict[c]["f1-score"], 4),
                "support": int(report_dict[c]["support"]),
            }
            for c in config.CATEGORIES
        },
        "confusion_matrix": matrix.tolist(),
        "categories": config.CATEGORIES,
        "cv_accuracy_mean": round(float(cv_scores.mean()), 4),
        "cv_accuracy_std": round(float(cv_scores.std()), 4),
        "top_words": top_words,
    }
    with open(config.EVALUATION_PATH, "w", encoding="utf-8") as json_file:
        json.dump(evaluation, json_file, indent=2)
    print(f"Evaluation saved to {config.EVALUATION_PATH}")


if __name__ == "__main__":
    main()
