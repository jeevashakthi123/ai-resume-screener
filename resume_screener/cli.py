#!/usr/bin/env python3
"""
cli.py  –  Command-line interface for the Resume Screening Tool.

Usage examples
--------------
# Screen all resumes in a folder against a JD text file:
    python cli.py --jd sample_data/job_description.txt \
                  --resumes sample_data/

# Screen specific resume files:
    python cli.py --jd sample_data/job_description.txt \
                  --resumes sample_data/resume_alex_chen.txt \
                            sample_data/resume_priya_sharma.txt

# Save results to a CSV:
    python cli.py --jd sample_data/job_description.txt \
                  --resumes sample_data/ \
                  --output results.csv
"""

import argparse
import csv
import os
import sys
import textwrap

# Ensure project root on path
sys.path.insert(0, os.path.dirname(__file__))

from utils.extractor import extract_text
from utils.preprocessor import preprocess_text
from utils.scorer import score_resume, rank_candidates
from utils.database import init_db, save_screening_session

SUPPORTED = {".pdf", ".docx", ".doc", ".txt"}

# ── ANSI colours ─────────────────────────────────────────────────────────────
GREEN  = "\033[92m"
YELLOW = "\033[93m"
RED    = "\033[91m"
CYAN   = "\033[96m"
BOLD   = "\033[1m"
RESET  = "\033[0m"

TIER_COLOUR = {
    "Excellent": GREEN,
    "Strong":    CYAN,
    "Good":      YELLOW,
    "Fair":      YELLOW,
    "Low":       RED,
}


def collect_resume_paths(paths: list) -> list:
    """Expand directories and filter for supported file types."""
    result = []
    for p in paths:
        if os.path.isdir(p):
            for fname in os.listdir(p):
                if os.path.splitext(fname)[1].lower() in SUPPORTED:
                    result.append(os.path.join(p, fname))
        elif os.path.isfile(p):
            result.append(p)
        else:
            print(f"  ⚠  Path not found: {p}")
    return result


def read_jd(path: str) -> str:
    """Read job description – supports .txt or binary files via extractor."""
    if path.endswith(".txt"):
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            return fh.read()
    return extract_text(path)


def print_table(ranked: list) -> None:
    """Pretty-print ranked results to the terminal."""
    header = f"{'#':<4}{'Name':<30}{'Score':>8}{'Match%':>9}  {'Tier':<12}  Keywords"
    print(f"\n{BOLD}{header}{RESET}")
    print("─" * 90)

    for c in ranked:
        tier = c.get("tier", "")
        colour = TIER_COLOUR.get(tier, "")
        kws = ", ".join((c.get("matched_keywords") or [])[:5])
        bar_len = int(c["match_pct"] / 5)
        bar = "█" * bar_len + "░" * (20 - bar_len)

        print(
            f"{c['rank']:<4}{c['name']:<30}"
            f"{c['score']:>8.4f}{c['match_pct']:>8.1f}%  "
            f"{colour}{tier:<12}{RESET}  {kws}"
        )
        print(f"     {CYAN}{bar}{RESET} {c['match_pct']:.1f}%")
        print()


def save_csv(ranked: list, output_path: str) -> None:
    """Write results to a CSV file."""
    fieldnames = ["rank", "name", "score", "match_pct", "tier", "matched_keywords"]
    with open(output_path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for c in ranked:
            row = dict(c)
            row["matched_keywords"] = "|".join(c.get("matched_keywords") or [])
            writer.writerow(row)
    print(f"\n  ✓ Results saved to: {output_path}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="AI-Powered Resume Screening Tool – CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent(__doc__),
    )
    parser.add_argument("--jd",      required=True, help="Path to job description file (.txt, .pdf, .docx)")
    parser.add_argument("--resumes", required=True, nargs="+", help="Resume files or a folder containing them")
    parser.add_argument("--title",   default="Screening Session", help="Job title label")
    parser.add_argument("--output",  default=None, help="Optional CSV output path")
    parser.add_argument("--top",     type=int, default=0, help="Show top N candidates only (0 = all)")
    parser.add_argument("--no-db",   action="store_true", help="Skip saving to database")
    args = parser.parse_args()

    print(f"\n{BOLD}ResumeAI – CLI Screener{RESET}")
    print("=" * 60)

    # ── Job description ──────────────────────────────────────────
    print(f"\n  📄 Loading job description: {args.jd}")
    jd_raw = read_jd(args.jd)
    if not jd_raw.strip():
        print(f"{RED}  ✗ Could not read job description.{RESET}")
        sys.exit(1)
    jd_clean = preprocess_text(jd_raw)
    print(f"     {len(jd_raw)} chars extracted, {len(jd_clean.split())} tokens after preprocessing.")

    # ── Resumes ──────────────────────────────────────────────────
    resume_paths = collect_resume_paths(args.resumes)
    if not resume_paths:
        print(f"{RED}  ✗ No supported resume files found.{RESET}")
        sys.exit(1)

    print(f"\n  📂 Found {len(resume_paths)} resume(s). Scoring…\n")

    candidates = []
    errors = []

    for path in resume_paths:
        fname = os.path.basename(path)
        try:
            if path.endswith(".txt"):
                with open(path, "r", encoding="utf-8", errors="replace") as fh:
                    raw = fh.read()
            else:
                raw = extract_text(path)

            if not raw.strip():
                errors.append(f"{fname}: No text extracted.")
                continue

            clean = preprocess_text(raw)
            score, match_pct, keywords = score_resume(clean, jd_clean)
            name = os.path.splitext(fname)[0].replace("_", " ").replace("-", " ").title()

            candidates.append({
                "name": name,
                "filename": fname,
                "score": round(score, 4),
                "match_pct": round(match_pct, 2),
                "matched_keywords": keywords,
                "raw_text_snippet": raw[:300],
            })
            print(f"  ✓ {fname:<45} {match_pct:>6.1f}% match")

        except Exception as exc:
            errors.append(f"{fname}: {exc}")
            print(f"  ✗ {fname} – {exc}")

    if not candidates:
        print(f"\n{RED}  No resumes could be processed.{RESET}")
        sys.exit(1)

    ranked = rank_candidates(candidates)
    top_n  = ranked[:args.top] if args.top > 0 else ranked

    print_table(top_n)

    # ── Database ─────────────────────────────────────────────────
    if not args.no_db:
        init_db()
        session_id = save_screening_session(args.title, jd_raw, ranked)
        print(f"  💾 Session #{session_id} saved to database.")

    # ── CSV output ───────────────────────────────────────────────
    if args.output:
        save_csv(top_n, args.output)

    # ── Errors ───────────────────────────────────────────────────
    if errors:
        print(f"\n{YELLOW}  Warnings:{RESET}")
        for e in errors:
            print(f"  ⚠  {e}")

    print(f"\n{GREEN}{BOLD}  Done! Screened {len(candidates)} candidate(s).{RESET}\n")


if __name__ == "__main__":
    main()
