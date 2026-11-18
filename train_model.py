import os
import json
import pandas as pd
import joblib
from sklearn.model_selection import train_test_split
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
from classifier import preprocess_text

DATA_PATH = os.path.join("data", "ticket_dataset.csv")
MODEL_PATH = os.path.join("models", "ticket_classifier.pkl")
REPORT_PATH = os.path.join("data", "evaluation_report.json")


def main():
    data = pd.read_csv(DATA_PATH)
    data = data.dropna(subset=["ticket_text", "category", "data_source"])
    data["clean_text"] = data["ticket_text"].apply(preprocess_text)
    data = data[data["clean_text"].str.len() >= 10]
    data = data.drop_duplicates(subset=["clean_text"])

    x_train, x_test, y_train, y_test = train_test_split(
        data["clean_text"], data["category"],
        test_size=0.2, random_state=42, stratify=data["category"]
    )

    vectorizer = TfidfVectorizer(
        ngram_range=(1, 1), min_df=1, max_features=12000, sublinear_tf=True
    )
    x_train_vector = vectorizer.fit_transform(x_train)
    x_test_vector = vectorizer.transform(x_test)

    model = LogisticRegression(
        max_iter=1500, class_weight="balanced", C=2.0
    )
    model.fit(x_train_vector, y_train)
    predictions = model.predict(x_test_vector)

    test_sources = data.loc[y_test.index, "data_source"]
    kaggle_mask = test_sources.eq("Kaggle")
    synthetic_mask = test_sources.eq("Synthetic")
    overall_accuracy = accuracy_score(y_test, predictions)
    kaggle_accuracy = accuracy_score(y_test[kaggle_mask], predictions[kaggle_mask])
    synthetic_accuracy = accuracy_score(y_test[synthetic_mask], predictions[synthetic_mask])

    report = {
        "dataset_records_after_cleaning": int(len(data)),
        "train_records": int(len(x_train)),
        "test_records": int(len(x_test)),
        "model": "TF-IDF (unigrams, sublinear term frequency) + Logistic Regression (C=2.0)",
        "split": "80:20 stratified split, random_state=42",
        "mixed_test_accuracy_percent": round(overall_accuracy * 100, 2),
        "kaggle_only_test_records": int(kaggle_mask.sum()),
        "kaggle_only_test_accuracy_percent": round(kaggle_accuracy * 100, 2),
        "synthetic_only_test_records": int(synthetic_mask.sum()),
        "synthetic_only_test_accuracy_percent": round(synthetic_accuracy * 100, 2),
        "target_percent": 90,
        "target_met_on_kaggle_only_test": bool(kaggle_accuracy >= 0.90),
        "kaggle_only_classification_report": classification_report(
            y_test[kaggle_mask], predictions[kaggle_mask], output_dict=True, zero_division=0
        ),
        "mixed_classification_report": classification_report(
            y_test, predictions, output_dict=True, zero_division=0
        ),
        "confusion_matrix": confusion_matrix(y_test, predictions, labels=model.classes_).tolist(),
        "class_labels": model.classes_.tolist(),
        "preprocessing": [
            "lowercase text", "remove template placeholders", "remove URLs and email addresses",
            "remove punctuation while preserving letters and digits", "normalize whitespace",
            "remove empty/very short records", "remove duplicate cleaned ticket text"
        ],
        "evaluation_warning": (
            "Kaggle-only accuracy is the honest real-source check for this dataset, but the source labels "
            "are mapped from Ticket Subject while the free-text descriptions are noisy and may contain "
            "unrelated or contradictory content. The synthetic-only score is not real-world validation. "
            "The mixed score must not be presented as real-world accuracy."
        )
    }

    os.makedirs("models", exist_ok=True)
    joblib.dump({"vectorizer": vectorizer, "model": model}, MODEL_PATH)
    with open(REPORT_PATH, "w", encoding="utf-8") as file:
        json.dump(report, file, indent=2)

    print("Training completed.")
    print(f"Records after cleaning: {len(data)}")
    print(f"Training records: {len(x_train)} | Test records: {len(x_test)}")
    print(f"Mixed test accuracy: {overall_accuracy * 100:.2f}%")
    print(f"Kaggle-only test accuracy: {kaggle_accuracy * 100:.2f}% ({kaggle_mask.sum()} real-source test records)")
    print(f"Synthetic-only test accuracy: {synthetic_accuracy * 100:.2f}% ({synthetic_mask.sum()} test records)")
    print(f"90% target met on Kaggle-only test: {'YES' if kaggle_accuracy >= 0.90 else 'NO'}")
    print(f"Saved model: {MODEL_PATH}")
    print(f"Saved report: {REPORT_PATH}")


if __name__ == "__main__":
    main()
