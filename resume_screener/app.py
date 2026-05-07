"""
AI-Powered Resume Screening Tool
Main Flask application entry point.
"""

import os
import json
import sqlite3
import traceback
from datetime import datetime
from flask import Flask, request, jsonify, render_template, redirect, url_for, flash
from werkzeug.utils import secure_filename

from utils.extractor import extract_text
from utils.preprocessor import preprocess_text
from utils.scorer import score_resume, rank_candidates
from utils.database import init_db, save_screening_session, get_all_sessions, get_session_results
from utils.visualizer import generate_chart

# ── App Configuration ────────────────────────────────────────────────────────
app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "resume-screener-secret-2024")

UPLOAD_FOLDER = os.path.join("static", "uploads")
ALLOWED_EXTENSIONS = {"pdf", "docx", "doc"}
MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["MAX_CONTENT_LENGTH"] = MAX_CONTENT_LENGTH

os.makedirs(UPLOAD_FOLDER, exist_ok=True)


# ── Helpers ──────────────────────────────────────────────────────────────────
def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


# ── Routes ───────────────────────────────────────────────────────────────────
@app.route("/")
def index():
    """Landing page."""
    return render_template("index.html")


@app.route("/screen", methods=["POST"])
def screen():
    """
    Main screening endpoint.
    Accepts a job description (text or file) + multiple resume files.
    Returns ranked candidate results.
    """
    try:
        # ── 1. Job description ───────────────────────────────────────────
        job_desc_text = request.form.get("job_description", "").strip()
        job_title = request.form.get("job_title", "Untitled Position").strip()

        if "job_desc_file" in request.files:
            jd_file = request.files["job_desc_file"]
            if jd_file and jd_file.filename and allowed_file(jd_file.filename):
                jd_filename = secure_filename(jd_file.filename)
                jd_path = os.path.join(app.config["UPLOAD_FOLDER"], f"jd_{jd_filename}")
                jd_file.save(jd_path)
                extracted = extract_text(jd_path)
                if extracted:
                    job_desc_text = extracted

        if not job_desc_text:
            return jsonify({"error": "Job description is required."}), 400

        # ── 2. Resume files ──────────────────────────────────────────────
        resume_files = request.files.getlist("resumes")
        if not resume_files or all(f.filename == "" for f in resume_files):
            return jsonify({"error": "At least one resume file is required."}), 400

        candidates = []
        errors = []

        for resume_file in resume_files:
            if not resume_file or resume_file.filename == "":
                continue
            if not allowed_file(resume_file.filename):
                errors.append(f"{resume_file.filename}: Unsupported format.")
                continue

            filename = secure_filename(resume_file.filename)
            filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
            resume_file.save(filepath)

            try:
                raw_text = extract_text(filepath)
                if not raw_text:
                    errors.append(f"{filename}: Could not extract text.")
                    continue

                clean_text = preprocess_text(raw_text)
                score, match_pct, matched_keywords = score_resume(
                    clean_text, preprocess_text(job_desc_text)
                )

                # Derive candidate name from filename (strip extension)
                name = os.path.splitext(filename)[0].replace("_", " ").replace("-", " ").title()

                candidates.append({
                    "name": name,
                    "filename": filename,
                    "score": round(score, 4),
                    "match_pct": round(match_pct, 2),
                    "matched_keywords": matched_keywords,
                    "raw_text_snippet": raw_text[:300] + "..." if len(raw_text) > 300 else raw_text,
                })
            except Exception as exc:
                errors.append(f"{filename}: {str(exc)}")

        if not candidates:
            return jsonify({"error": "No resumes could be processed.", "details": errors}), 400

        # ── 3. Rank candidates ───────────────────────────────────────────
        ranked = rank_candidates(candidates)

        # ── 4. Generate chart ────────────────────────────────────────────
        chart_path = generate_chart(ranked)

        # ── 5. Persist to DB ─────────────────────────────────────────────
        session_id = save_screening_session(job_title, job_desc_text, ranked)

        return jsonify({
            "session_id": session_id,
            "job_title": job_title,
            "candidates": ranked,
            "chart_url": f"/{chart_path}" if chart_path else None,
            "errors": errors,
        })

    except Exception as exc:
        traceback.print_exc()
        return jsonify({"error": "Internal server error.", "details": str(exc)}), 500


@app.route("/history")
def history():
    """View past screening sessions."""
    sessions = get_all_sessions()
    return render_template("history.html", sessions=sessions)


@app.route("/session/<int:session_id>")
def session_detail(session_id: int):
    """View results of a specific session."""
    results = get_session_results(session_id)
    if not results:
        flash("Session not found.", "error")
        return redirect(url_for("history"))
    return render_template("session.html", session=results)


@app.route("/api/sessions")
def api_sessions():
    """REST endpoint: list all sessions."""
    return jsonify(get_all_sessions())


@app.route("/api/session/<int:session_id>")
def api_session(session_id: int):
    """REST endpoint: get session details."""
    return jsonify(get_session_results(session_id))


# ── Startup ──────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    init_db()
    print("=" * 60)
    print("  AI-Powered Resume Screening Tool")
    print("  Running at http://127.0.0.1:5000")
    print("=" * 60)
    app.run(debug=True, host="0.0.0.0", port=5000)
