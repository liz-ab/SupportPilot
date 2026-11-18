import os
import re
import joblib

MODEL_PATH = os.path.join("models", "ticket_classifier.pkl")


def preprocess_text(text):
    text = str(text).lower()
    text = re.sub(r"\{[^}]*\}", " ", text)
    text = re.sub(r"https?://\S+|www\.\S+", " ", text)
    text = re.sub(r"\b[\w.+-]+@[\w.-]+\.[a-z]{2,}\b", " ", text)
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def load_model():
    if not os.path.exists(MODEL_PATH):
        raise FileNotFoundError("Model not found. Run: python train_model.py")
    return joblib.load(MODEL_PATH)


def predict_category(text, bundle=None):
    if bundle is None:
        bundle = load_model()
    cleaned = preprocess_text(text)
    vector = bundle["vectorizer"].transform([cleaned])
    category = bundle["model"].predict(vector)[0]
    probabilities = bundle["model"].predict_proba(vector)[0]
    confidence = float(max(probabilities))
    return category, confidence
