"""
utils/database.py
SQLite persistence layer for screening sessions and results.
"""

import json
import sqlite3
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

DB_PATH = "screening_results.db"


# ── Schema ────────────────────────────────────────────────────────────────────

_DDL = """
CREATE TABLE IF NOT EXISTS sessions (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    job_title   TEXT    NOT NULL,
    job_desc    TEXT    NOT NULL,
    created_at  TEXT    NOT NULL
);

CREATE TABLE IF NOT EXISTS candidates (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id       INTEGER NOT NULL REFERENCES sessions(id),
    rank             INTEGER NOT NULL,
    name             TEXT    NOT NULL,
    filename         TEXT,
    score            REAL    NOT NULL,
    match_pct        REAL    NOT NULL,
    tier             TEXT,
    matched_keywords TEXT,
    raw_text_snippet TEXT
);
"""


def _get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """Create tables if they don't exist."""
    with _get_conn() as conn:
        conn.executescript(_DDL)
    logger.info("Database initialised at %s", DB_PATH)


# ── Write ─────────────────────────────────────────────────────────────────────

def save_screening_session(
    job_title: str,
    job_desc: str,
    ranked_candidates: List[Dict[str, Any]],
) -> int:
    """
    Persist a screening session and its candidate results.

    Returns
    -------
    int
        The new session ID.
    """
    now = datetime.utcnow().isoformat(sep=" ", timespec="seconds")

    with _get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO sessions (job_title, job_desc, created_at) VALUES (?, ?, ?)",
            (job_title, job_desc, now),
        )
        session_id = cur.lastrowid

        for candidate in ranked_candidates:
            conn.execute(
                """INSERT INTO candidates
                   (session_id, rank, name, filename, score, match_pct,
                    tier, matched_keywords, raw_text_snippet)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    session_id,
                    candidate.get("rank", 0),
                    candidate.get("name", "Unknown"),
                    candidate.get("filename", ""),
                    candidate.get("score", 0.0),
                    candidate.get("match_pct", 0.0),
                    candidate.get("tier", ""),
                    json.dumps(candidate.get("matched_keywords", [])),
                    candidate.get("raw_text_snippet", ""),
                ),
            )

    logger.info("Saved session %d with %d candidates.", session_id, len(ranked_candidates))
    return session_id


# ── Read ──────────────────────────────────────────────────────────────────────

def get_all_sessions() -> List[Dict[str, Any]]:
    """Return summary rows for all sessions (newest first)."""
    with _get_conn() as conn:
        rows = conn.execute(
            """SELECT s.id, s.job_title, s.created_at,
                      COUNT(c.id) AS candidate_count
               FROM sessions s
               LEFT JOIN candidates c ON c.session_id = s.id
               GROUP BY s.id
               ORDER BY s.id DESC"""
        ).fetchall()
    return [dict(r) for r in rows]


def get_session_results(session_id: int) -> Optional[Dict[str, Any]]:
    """Return full session record plus all candidates."""
    with _get_conn() as conn:
        session_row = conn.execute(
            "SELECT * FROM sessions WHERE id = ?", (session_id,)
        ).fetchone()

        if not session_row:
            return None

        candidate_rows = conn.execute(
            """SELECT * FROM candidates
               WHERE session_id = ?
               ORDER BY rank ASC""",
            (session_id,),
        ).fetchall()

    candidates = []
    for row in candidate_rows:
        c = dict(row)
        try:
            c["matched_keywords"] = json.loads(c.get("matched_keywords") or "[]")
        except (json.JSONDecodeError, TypeError):
            c["matched_keywords"] = []
        candidates.append(c)

    return {
        **dict(session_row),
        "candidates": candidates,
    }
