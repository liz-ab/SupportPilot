import os
import joblib
from labeling import clean_text, rule_severity

MODEL_PATH = os.path.join("models", "ticket_classifier.pkl")
_bundle = None


def preprocess_text(text):
    return clean_text(text)


def load_model():
    global _bundle
    if _bundle is None:
        if not os.path.exists(MODEL_PATH):
            raise FileNotFoundError("Model not found. Run: python train_model.py")
        _bundle = joblib.load(MODEL_PATH)
    return _bundle


def predict_category(text, bundle=None):
    bundle = bundle or load_model()
    vector = bundle["vectorizer"].transform([preprocess_text(text)])
    probabilities = bundle["model"].predict_proba(vector)[0]
    best = probabilities.argmax()
    return bundle["model"].classes_[best], float(probabilities[best])


def predict_severity(text):
    """Severity comes from the rule engine, which scored best against the hand-labelled audit set."""
    return rule_severity(preprocess_text(text))
