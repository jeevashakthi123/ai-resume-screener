"""
tests/test_core.py
Unit tests for the core resume-screening functions.

Run with:
    pytest tests/ -v
"""

import os
import sys
import json
import tempfile
import unittest

# Ensure the project root is on the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from utils.preprocessor import preprocess_text, extract_skills
from utils.scorer import score_resume, rank_candidates, _assign_tier
from utils.extractor import _clean_extracted


# ── Fixtures ──────────────────────────────────────────────────────────────────

JD_TEXT = """
Senior Machine Learning Engineer. Required: Python, TensorFlow, PyTorch, NLP,
BERT, scikit-learn, Docker, Kubernetes, AWS, SQL, machine learning, deep learning,
CI/CD, MLflow, Apache Spark, communication, leadership, problem-solving.
Master's or PhD in Computer Science preferred.
"""

STRONG_RESUME = """
Alex Chen – Senior ML Engineer. 7 years experience. Python expert. TensorFlow, PyTorch,
scikit-learn, Keras. NLP, BERT, transformers, TF-IDF, Word2Vec. MLflow, Airflow,
Kubeflow. Docker, Kubernetes, CI/CD. AWS SageMaker, GCP Vertex AI. Apache Spark.
SQL, PostgreSQL, MongoDB. FastAPI, Flask. Machine learning, deep learning, NLP.
M.Sc. Computer Science Stanford. Leadership, communication, problem-solving. Agile Scrum.
"""

WEAK_RESUME = """
Sarah Kim – Frontend Developer. React, Next.js, Vue.js, Angular. TypeScript, JavaScript.
CSS, HTML, Tailwind. Figma, Storybook. Jest, Cypress. Webpack. Firebase. Vercel.
B.Sc. Information Technology.
"""


class TestPreprocessText(unittest.TestCase):
    """Tests for utils.preprocessor.preprocess_text"""

    def test_returns_string(self):
        result = preprocess_text("Hello world this is a test.")
        self.assertIsInstance(result, str)

    def test_lowercase(self):
        result = preprocess_text("Machine Learning Python TensorFlow")
        self.assertEqual(result, result.lower())

    def test_removes_stopwords(self):
        result = preprocess_text("This is a test of the system")
        # Common stopwords should be removed
        tokens = result.split()
        stopwords_present = [t for t in tokens if t in {"this", "is", "a", "of", "the"}]
        self.assertEqual(stopwords_present, [])

    def test_empty_string(self):
        self.assertEqual(preprocess_text(""), "")
        self.assertEqual(preprocess_text("   "), "")

    def test_special_characters_removed(self):
        result = preprocess_text("Python!!! @#$% Machine&*Learning")
        self.assertNotIn("@", result)
        self.assertNotIn("!", result)
        self.assertNotIn("$", result)

    def test_preserves_meaningful_words(self):
        result = preprocess_text("Python machine learning experience")
        self.assertIn("python", result)
        self.assertIn("learn", result)  # lemmatised form

    def test_numbers_handling(self):
        result = preprocess_text("5 years of experience in Python 3.x")
        self.assertIsInstance(result, str)


class TestExtractSkills(unittest.TestCase):
    """Tests for utils.preprocessor.extract_skills"""

    def test_detects_programming_languages(self):
        skills = extract_skills("Proficient in Python, Java, and JavaScript")
        self.assertIn("python", skills)
        self.assertIn("java", skills)

    def test_detects_ml_frameworks(self):
        skills = extract_skills("Experience with TensorFlow, PyTorch, and scikit-learn")
        # At least one should be found
        self.assertTrue(any(s in skills for s in ["tensorflow", "pytorch", "scikit-learn"]))

    def test_detects_cloud(self):
        skills = extract_skills("Deployed on AWS and GCP using Docker and Kubernetes")
        self.assertTrue(any(s in skills for s in ["aws", "gcp", "docker", "kubernetes"]))

    def test_empty_text(self):
        skills = extract_skills("")
        self.assertEqual(skills, [])

    def test_returns_list(self):
        skills = extract_skills("Python developer")
        self.assertIsInstance(skills, list)

    def test_no_duplicates(self):
        skills = extract_skills("Python Python Python developer using Python")
        self.assertEqual(len(skills), len(set(skills)))


class TestScoreResume(unittest.TestCase):
    """Tests for utils.scorer.score_resume"""

    def setUp(self):
        self.jd = preprocess_text(JD_TEXT)
        self.strong = preprocess_text(STRONG_RESUME)
        self.weak = preprocess_text(WEAK_RESUME)

    def test_returns_tuple_of_three(self):
        result = score_resume(self.strong, self.jd)
        self.assertIsInstance(result, tuple)
        self.assertEqual(len(result), 3)

    def test_score_in_range(self):
        score, match_pct, _ = score_resume(self.strong, self.jd)
        self.assertGreaterEqual(score, 0.0)
        self.assertLessEqual(score, 1.0)

    def test_match_pct_in_range(self):
        _, match_pct, _ = score_resume(self.strong, self.jd)
        self.assertGreaterEqual(match_pct, 0.0)
        self.assertLessEqual(match_pct, 100.0)

    def test_strong_resume_scores_higher_than_weak(self):
        strong_score, _, _ = score_resume(self.strong, self.jd)
        weak_score, _, _ = score_resume(self.weak, self.jd)
        self.assertGreater(strong_score, weak_score)

    def test_matched_keywords_is_list(self):
        _, _, keywords = score_resume(self.strong, self.jd)
        self.assertIsInstance(keywords, list)

    def test_matched_keywords_are_strings(self):
        _, _, keywords = score_resume(self.strong, self.jd)
        for kw in keywords:
            self.assertIsInstance(kw, str)

    def test_identical_texts_high_score(self):
        score, _, _ = score_resume(self.jd, self.jd)
        self.assertGreater(score, 0.8)

    def test_empty_resume(self):
        score, match_pct, keywords = score_resume("", self.jd)
        self.assertEqual(score, 0.0)
        self.assertEqual(match_pct, 0.0)
        self.assertEqual(keywords, [])

    def test_empty_job_desc(self):
        score, match_pct, keywords = score_resume(self.strong, "")
        self.assertEqual(score, 0.0)

    def test_keyword_boost_parameter(self):
        score_low_boost, _, _  = score_resume(self.strong, self.jd, keyword_boost=0.1)
        score_high_boost, _, _ = score_resume(self.strong, self.jd, keyword_boost=0.5)
        # Scores should differ; both valid floats in [0,1]
        self.assertGreaterEqual(score_low_boost, 0.0)
        self.assertGreaterEqual(score_high_boost, 0.0)


class TestRankCandidates(unittest.TestCase):
    """Tests for utils.scorer.rank_candidates"""

    def _make_candidates(self):
        return [
            {"name": "Alice", "score": 0.72, "match_pct": 72.0, "matched_keywords": []},
            {"name": "Bob",   "score": 0.45, "match_pct": 45.0, "matched_keywords": []},
            {"name": "Carol", "score": 0.88, "match_pct": 88.0, "matched_keywords": []},
            {"name": "Dave",  "score": 0.15, "match_pct": 15.0, "matched_keywords": []},
        ]

    def test_sorted_descending(self):
        ranked = rank_candidates(self._make_candidates())
        scores = [c["score"] for c in ranked]
        self.assertEqual(scores, sorted(scores, reverse=True))

    def test_ranks_assigned(self):
        ranked = rank_candidates(self._make_candidates())
        for i, c in enumerate(ranked, start=1):
            self.assertEqual(c["rank"], i)

    def test_first_rank_is_highest_score(self):
        ranked = rank_candidates(self._make_candidates())
        self.assertEqual(ranked[0]["name"], "Carol")

    def test_tiers_assigned(self):
        ranked = rank_candidates(self._make_candidates())
        for c in ranked:
            self.assertIn("tier", c)
            self.assertIn(c["tier"], {"Excellent", "Strong", "Good", "Fair", "Low"})

    def test_empty_input(self):
        self.assertEqual(rank_candidates([]), [])

    def test_single_candidate(self):
        candidates = [{"name": "Solo", "score": 0.5, "match_pct": 50.0, "matched_keywords": []}]
        ranked = rank_candidates(candidates)
        self.assertEqual(len(ranked), 1)
        self.assertEqual(ranked[0]["rank"], 1)

    def test_carol_is_excellent(self):
        ranked = rank_candidates(self._make_candidates())
        carol = next(c for c in ranked if c["name"] == "Carol")
        self.assertEqual(carol["tier"], "Excellent")

    def test_dave_is_low(self):
        ranked = rank_candidates(self._make_candidates())
        dave = next(c for c in ranked if c["name"] == "Dave")
        self.assertEqual(dave["tier"], "Low")


class TestAssignTier(unittest.TestCase):
    """Tests for utils.scorer._assign_tier"""

    def test_excellent(self):
        self.assertEqual(_assign_tier(85.0), "Excellent")
        self.assertEqual(_assign_tier(80.0), "Excellent")

    def test_strong(self):
        self.assertEqual(_assign_tier(75.0), "Strong")
        self.assertEqual(_assign_tier(60.0), "Strong")

    def test_good(self):
        self.assertEqual(_assign_tier(55.0), "Good")
        self.assertEqual(_assign_tier(40.0), "Good")

    def test_fair(self):
        self.assertEqual(_assign_tier(35.0), "Fair")
        self.assertEqual(_assign_tier(20.0), "Fair")

    def test_low(self):
        self.assertEqual(_assign_tier(10.0), "Low")
        self.assertEqual(_assign_tier(0.0),  "Low")


class TestCleanExtracted(unittest.TestCase):
    """Tests for utils.extractor._clean_extracted"""

    def test_strips_whitespace(self):
        result = _clean_extracted("  hello world  ")
        self.assertEqual(result, "hello world")

    def test_collapses_multiple_spaces(self):
        result = _clean_extracted("hello   world")
        self.assertNotIn("  ", result)

    def test_empty_string(self):
        self.assertEqual(_clean_extracted(""), "")

    def test_none_like_empty(self):
        self.assertEqual(_clean_extracted(""), "")

    def test_removes_non_printable(self):
        result = _clean_extracted("hello\x00world")
        self.assertNotIn("\x00", result)


class TestDatabaseIntegration(unittest.TestCase):
    """Integration tests for the database layer."""

    def setUp(self):
        """Use a temporary DB file for each test."""
        import utils.database as db
        self._original_path = db.DB_PATH
        self._tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        db.DB_PATH = self._tmp.name
        db.init_db()
        self.db = db

    def tearDown(self):
        self.db.DB_PATH = self._original_path
        self._tmp.close()
        os.unlink(self._tmp.name)

    def test_save_and_retrieve_session(self):
        candidates = [
            {"rank": 1, "name": "Alice", "filename": "alice.pdf",
             "score": 0.85, "match_pct": 85.0, "tier": "Excellent",
             "matched_keywords": ["python", "nlp"], "raw_text_snippet": "..."},
        ]
        session_id = self.db.save_screening_session("ML Engineer", "Job desc text", candidates)
        self.assertIsInstance(session_id, int)
        self.assertGreater(session_id, 0)

        result = self.db.get_session_results(session_id)
        self.assertIsNotNone(result)
        self.assertEqual(result["job_title"], "ML Engineer")
        self.assertEqual(len(result["candidates"]), 1)
        self.assertEqual(result["candidates"][0]["name"], "Alice")

    def test_matched_keywords_json_roundtrip(self):
        keywords = ["python", "tensorflow", "nlp"]
        candidates = [
            {"rank": 1, "name": "Bob", "filename": "bob.pdf",
             "score": 0.7, "match_pct": 70.0, "tier": "Strong",
             "matched_keywords": keywords, "raw_text_snippet": ""},
        ]
        session_id = self.db.save_screening_session("Test Job", "Desc", candidates)
        result = self.db.get_session_results(session_id)
        self.assertEqual(result["candidates"][0]["matched_keywords"], keywords)

    def test_get_all_sessions(self):
        self.db.save_screening_session("Job A", "Desc A", [])
        self.db.save_screening_session("Job B", "Desc B", [])
        sessions = self.db.get_all_sessions()
        self.assertGreaterEqual(len(sessions), 2)

    def test_missing_session_returns_none(self):
        result = self.db.get_session_results(99999)
        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main(verbosity=2)
