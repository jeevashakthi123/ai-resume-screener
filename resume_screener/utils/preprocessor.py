"""
utils/preprocessor.py
NLP preprocessing: tokenisation, stop-word removal, lemmatisation.
"""

import re
import logging
from typing import List

logger = logging.getLogger(__name__)

# ── NLTK bootstrap ────────────────────────────────────────────────────────────
def _ensure_nltk():
    """Download required NLTK corpora if missing."""
    import nltk
    for resource in ("stopwords", "wordnet", "punkt", "punkt_tab", "averaged_perceptron_tagger"):
        try:
            nltk.data.find(f"corpora/{resource}" if resource in ("stopwords", "wordnet") else f"tokenizers/{resource}")
        except LookupError:
            try:
                nltk.download(resource, quiet=True)
            except Exception:
                pass


def preprocess_text(text: str) -> str:
    """
    Full NLP pipeline:
      1. Lowercase
      2. Remove special characters / numbers (keep hyphens in compound words)
      3. Tokenise
      4. Remove stop words
      5. Lemmatise

    Parameters
    ----------
    text : str
        Raw resume or job-description text.

    Returns
    -------
    str
        Space-joined lemmatised tokens.
    """
    if not text or not text.strip():
        return ""

    try:
        _ensure_nltk()
        from nltk.tokenize import word_tokenize
        from nltk.corpus import stopwords
        from nltk.stem import WordNetLemmatizer

        stop_words = set(stopwords.words("english"))
        lemmatizer = WordNetLemmatizer()

        # Lowercase
        text = text.lower()

        # Keep alphanumeric and hyphens (useful for skill names like "machine-learning")
        text = re.sub(r"[^a-z0-9\s\-]", " ", text)
        text = re.sub(r"\s+", " ", text).strip()

        tokens: List[str] = word_tokenize(text)

        # Filter & lemmatise
        cleaned = []
        for tok in tokens:
            tok = tok.strip("-")          # strip leading/trailing hyphens
            if len(tok) < 2:
                continue
            if tok in stop_words:
                continue
            lemma = lemmatizer.lemmatize(tok)
            cleaned.append(lemma)

        return " ".join(cleaned)

    except Exception as exc:
        logger.warning("NLTK preprocessing failed, using basic fallback: %s", exc)
        return _basic_preprocess(text)


def _basic_preprocess(text: str) -> str:
    """Regex-only fallback when NLTK is unavailable."""
    BASIC_STOPWORDS = {
        "a", "an", "the", "and", "or", "but", "in", "on", "at", "to",
        "for", "of", "with", "by", "from", "is", "are", "was", "were",
        "be", "been", "being", "have", "has", "had", "do", "does", "did",
        "will", "would", "could", "should", "may", "might", "shall",
        "this", "that", "these", "those", "i", "you", "he", "she", "we", "they",
    }
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s\-]", " ", text)
    tokens = text.split()
    return " ".join(t for t in tokens if t not in BASIC_STOPWORDS and len(t) > 1)


def extract_skills(text: str) -> List[str]:
    """
    Heuristic skill extractor.
    Looks for common technical and soft skills in the preprocessed text.
    """
    SKILL_PATTERNS = [
        # Programming languages
        r"\b(python|java|javascript|typescript|c\+\+|c#|ruby|php|swift|kotlin|go|rust|scala|r)\b",
        # Web / cloud
        r"\b(react|angular|vue|node\.?js|django|flask|fastapi|spring|express)\b",
        r"\b(aws|azure|gcp|docker|kubernetes|terraform|ci/?cd)\b",
        # Data / ML
        r"\b(machine.?learning|deep.?learning|nlp|tensorflow|pytorch|keras|scikit.?learn|pandas|numpy)\b",
        r"\b(sql|mysql|postgresql|mongodb|redis|elasticsearch|spark|hadoop)\b",
        # Soft skills
        r"\b(leadership|communication|teamwork|problem.?solving|agile|scrum|kanban)\b",
        # Degrees / certs
        r"\b(b\.?sc|m\.?sc|phd|mba|bachelor|master|doctor)\b",
    ]

    found = []
    text_lower = text.lower()
    for pattern in SKILL_PATTERNS:
        matches = re.findall(pattern, text_lower)
        found.extend(matches)

    # Deduplicate while preserving order
    seen = set()
    unique = []
    for skill in found:
        if skill not in seen:
            seen.add(skill)
            unique.append(skill)
    return unique
