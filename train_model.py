import json
import os
import re
import joblib
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
from sklearn.model_selection import train_test_split
from labeling import CATEGORIES, CATEGORY_RULES, rule_severity

DATA_PATH = os.path.join("data", "ticket_dataset.csv")
AUDIT_PATH = os.path.join("data", "audit_sample.csv")
MODEL_PATH = os.path.join("models", "ticket_classifier.pkl")
REPORT_PATH = os.path.join("data", "evaluation_report.json")


def pct(value):
    return round(float(value) * 100, 2)


def mask_keywords(text):
    """Remove the words the labelling rules look for, to test whether the model generalises."""
    for pattern in CATEGORY_RULES.values():
        text = re.sub(pattern, " ", text)
    return re.sub(r"\s+", " ", text).strip()


def make_vectorizer():
    return TfidfVectorizer(ngram_range=(1, 2), min_df=2, max_features=30000, sublinear_tf=True)


def main():
    data = pd.read_csv(DATA_PATH).dropna(subset=["text", "category", "severity"])
    audit = pd.read_csv(AUDIT_PATH)
    data = data[~data["text"].isin(set(audit["text"]))]  # audit tickets are never used for training

    train, test = train_test_split(data, test_size=0.2, random_state=42, stratify=data["category"])
    vectorizer = make_vectorizer()
    x_train = vectorizer.fit_transform(train["text"])
    x_test = vectorizer.transform(test["text"])

    category_model = LogisticRegression(max_iter=3000, C=8.0, class_weight="balanced")
    category_model.fit(x_train, train["category"])

    cat_pred = category_model.predict(x_test)
    sev_pred = test["text"].map(rule_severity)

    masked_pred = category_model.predict(vectorizer.transform(test["text"].map(mask_keywords)))

    # Independent check: 120 tickets labelled by hand (see data/audit_sample.csv).
    a_vec = vectorizer.transform(audit["text"])
    a_cat = category_model.predict(a_vec)
    a_rule_sev = audit["text"].map(rule_severity)
    on_topic = audit["true_category"].isin(CATEGORIES)

    report = {
        "dataset_records": int(len(data)),
        "train_records": int(len(train)),
        "test_records": int(len(test)),
        "model": "TF-IDF (1-2 grams) + Logistic Regression for category; rule engine for severity",
        "split": "80:20 stratified split, random_state=42; audit tickets excluded from training",
        "category_test_accuracy_percent": pct(accuracy_score(test["category"], cat_pred)),
        "category_test_accuracy_keywords_masked_percent": pct(accuracy_score(test["category"], masked_pred)),
                "manual_audit": {
            "tickets": int(len(audit)),
            "on_topic_tickets": int(on_topic.sum()),
            "category_accuracy_on_topic_percent": pct(accuracy_score(audit.loc[on_topic, "true_category"], a_cat[on_topic.values])),
            "severity_accuracy_percent": pct(accuracy_score(audit["true_severity"], a_rule_sev)),
            "training_label_precision_on_topic_percent": pct(
                (audit.loc[on_topic, "true_category"] == audit.loc[on_topic, "rule_category"]).mean()),
        },
        "targets": {"category_percent": 90, "severity_percent": 85},
        "class_labels": category_model.classes_.tolist(),
        "category_report": classification_report(test["category"], cat_pred, output_dict=True, zero_division=0),
        "category_confusion_matrix": confusion_matrix(test["category"], cat_pred, labels=category_model.classes_).tolist(),
    }

    os.makedirs("models", exist_ok=True)
    joblib.dump({"vectorizer": vectorizer, "model": category_model}, MODEL_PATH)
    with open(REPORT_PATH, "w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2)

    audit_info = report["manual_audit"]
    print(f"Records: {len(data)} (train {len(train)}, test {len(test)})")
    print(f"Category accuracy (held-out test):         {report['category_test_accuracy_percent']}%")
    print(f"Category accuracy (trigger words masked):  {report['category_test_accuracy_keywords_masked_percent']}%")
    print(f"Manual audit category accuracy (on-topic): {audit_info['category_accuracy_on_topic_percent']}%")
    print(f"Manual audit severity accuracy (rules):    {audit_info['severity_accuracy_percent']}%")


if __name__ == "__main__":
    main()
