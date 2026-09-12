import os
import pickle
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.naive_bayes import MultinomialNB
from sklearn.pipeline import make_pipeline

MODEL_PATH = "./data/classifier.pkl"

def get_model():
    if os.path.exists(MODEL_PATH):
        with open(MODEL_PATH, "rb") as f:
            return pickle.load(f)
    return None

def train_model(texts, labels):
    if not texts:
        return
    model = make_pipeline(TfidfVectorizer(), MultinomialNB())
    model.fit(texts, labels)
    with open(MODEL_PATH, "wb") as f:
        pickle.dump(model, f)

def classify_text(text: str):
    model = get_model()
    if not model or not text.strip():
        return ("uncategorized", 0.0)
    
    try:
        preds = model.predict_proba([text])
        classes = model.classes_
        max_idx = preds[0].argmax()
        return (classes[max_idx], float(preds[0][max_idx]))
    except:
        return ("uncategorized", 0.0)
        
def retrain_model(texts, labels):
    train_model(texts, labels)
