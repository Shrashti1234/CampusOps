"""Privacy-scoped complaint similarity with optional local sentence embeddings.

Enable with CAMPUSOPS_SIMILARITY=semantic and install requirements-ai.txt.
No issue text is sent to an external API; the model is downloaded once and
runs locally. If loading fails, the system falls back to TF-IDF.
"""
from functools import lru_cache
import os
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"

@lru_cache(maxsize=1)
def get_encoder():
    from sentence_transformers import SentenceTransformer
    return SentenceTransformer(MODEL_NAME)

def compare(title, description, location, existing, *, mode=None):
    """Return (matches, engine). Caller must scope existing to authorized issues."""
    if not existing:
        return [], "none"
    texts = [f"{title}. {description}. Location: {location}"] + [
        f"{item.title}. {item.description}. Location: {item.location}" for item in existing
    ]
    engine = "tfidf"
    configured = (mode or os.getenv("CAMPUSOPS_SIMILARITY", "tfidf")).lower()
    if configured == "semantic":
        try:
            encoder = get_encoder()
            vectors = encoder.encode(texts, normalize_embeddings=True)
            scores = cosine_similarity(vectors[:1], vectors[1:]).ravel()
            engine = "sentence-transformers"
        except (ImportError, OSError, RuntimeError, ValueError):
            # Optional dependency missing, model download failed, or model
            # initialization failed: remain usable in local demo mode.
            scores = _tfidf_scores(texts)
    else:
        scores = _tfidf_scores(texts)
    threshold = 0.52 if engine == "sentence-transformers" else 0.25
    ranked = sorted(zip(existing, scores), key=lambda pair: pair[1], reverse=True)
    matches = [
        {"id": issue.id, "title": issue.title, "similarity": round(float(score), 3)}
        for issue, score in ranked if float(score) >= threshold
    ][:3]
    return matches, engine

def _tfidf_scores(texts):
    matrix = TfidfVectorizer(stop_words="english", ngram_range=(1, 2)).fit_transform(texts)
    return cosine_similarity(matrix[0:1], matrix[1:]).ravel()
