import joblib
import os

MODEL_PATH = 'models/injection_classifier.pkl'
model = None

def load_model():
    global model
    if model is None:
        if os.path.exists(MODEL_PATH):
            model = joblib.load(MODEL_PATH)
    return model

def classify_with_dataset(text: str) -> dict:
    clf = load_model()

    if clf is None:
        return {
            "verdict": "unknown",
            "confidence": 0.0,
            "reason": "Dataset model not found."
        }

    try:
        proba = clf.predict_proba([text])[0]
        predicted = clf.predict([text])[0]

        safe_conf = float(proba[0])
        malicious_conf = float(proba[1])

        if predicted == 1:
            return {
                "verdict": "blocked",
                "confidence": round(malicious_conf, 2),
                "reason": f"Dataset classifier detected injection pattern ({malicious_conf*100:.0f}% confidence)"
            }
        else:
            return {
                "verdict": "safe",
                "confidence": round(safe_conf, 2),
                "reason": f"Dataset classifier passed ({safe_conf*100:.0f}% confidence)"
            }

    except Exception as e:
        return {
            "verdict": "unknown",
            "confidence": 0.0,
            "reason": f"Dataset classifier error: {str(e)}"
        }
