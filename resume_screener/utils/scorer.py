"""
utils/scorer.py
TF-IDF + cosine similarity scoring and candidate ranking.
"""

import logging
from typing import Dict, List, Tuple, Any

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

logger = logging.getLogger(__name__)

# ── Core Scoring ─────────────────────────────────────────────────────────────

def score_resume(
    resume_text: str,
    job_desc_text: str,
    keyword_boost: float = 0.3,
) -> Tuple[float, float, List[str]]:
    """
    Score a single resume against a job description.

    Strategy
    --------
    1. TF-IDF cosine similarity between resume and JD  (70 % weight)
    2. Keyword overlap ratio                            (30 % weight)

    Parameters
    ----------
    resume_text : str
        Preprocessed resume text.
    job_desc_text : str
        Preprocessed job-description text.
    keyword_boost : float
        Weight of keyword-overlap component (default 0.3).

    Returns
    -------
    score : float
        Composite score in [0, 1].
    match_pct : float
        Percentage representation of the score.
    matched_keywords : List[str]
        Keywords from the JD that appear in the resume.
    """
    if not resume_text.strip() or not job_desc_text.strip():
        return 0.0, 0.0, []

    # ── TF-IDF similarity ────────────────────────────────────────────────
    try:
        vectorizer = TfidfVectorizer(
            ngram_range=(1, 2),   # unigrams + bigrams
            min_df=1,
            sublinear_tf=True,
        )
        tfidf_matrix = vectorizer.fit_transform([job_desc_text, resume_text])
        similarity = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0]
    except Exception as exc:
        logger.error("TF-IDF scoring failed: %s", exc)
        similarity = 0.0

    # ── Keyword overlap ──────────────────────────────────────────────────
    jd_words = set(job_desc_text.lower().split())
    resume_words = set(resume_text.lower().split())

    # Filter out very short tokens
    jd_keywords = {w for w in jd_words if len(w) > 2}
    matched_keywords = sorted(jd_keywords & resume_words)

    keyword_ratio = len(matched_keywords) / max(len(jd_keywords), 1)

    # ── Composite score ──────────────────────────────────────────────────
    tfidf_weight = 1.0 - keyword_boost
    composite = tfidf_weight * similarity + keyword_boost * keyword_ratio

    # Clamp to [0, 1]
    composite = float(np.clip(composite, 0.0, 1.0))
    match_pct = round(composite * 100, 2)

    return composite, match_pct, matched_keywords[:20]   # return top-20 keywords


def rank_candidates(candidates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Sort candidates by descending score and assign ranks.

    Parameters
    ----------
    candidates : list of dict
        Each dict must contain at least ``score`` and ``name`` keys.

    Returns
    -------
    list of dict
        Same dicts sorted and annotated with ``rank`` and ``tier``.
    """
    if not candidates:
        return []

    ranked = sorted(candidates, key=lambda c: c["score"], reverse=True)

    for i, candidate in enumerate(ranked, start=1):
        candidate["rank"] = i
        candidate["tier"] = _assign_tier(candidate["match_pct"])

    return ranked


def _assign_tier(match_pct: float) -> str:
    """Map match percentage to a human-readable tier."""
    if match_pct >= 80:
        return "Excellent"
    elif match_pct >= 60:
        return "Strong"
    elif match_pct >= 40:
        return "Good"
    elif match_pct >= 20:
        return "Fair"
    else:
        return "Low"


# ── Batch Scoring (convenience) ───────────────────────────────────────────────

def batch_score(
    resumes: Dict[str, str],
    job_desc_text: str,
) -> List[Dict[str, Any]]:
    """
    Score multiple resumes in one call.

    Parameters
    ----------
    resumes : dict
        Mapping of candidate_name -> preprocessed_resume_text.
    job_desc_text : str
        Preprocessed job-description text.

    Returns
    -------
    list of dict
        Ranked candidate records.
    """
    candidates = []
    for name, text in resumes.items():
        score, match_pct, keywords = score_resume(text, job_desc_text)
        candidates.append({
            "name": name,
            "score": round(score, 4),
            "match_pct": round(match_pct, 2),
            "matched_keywords": keywords,
        })
    return rank_candidates(candidates)
