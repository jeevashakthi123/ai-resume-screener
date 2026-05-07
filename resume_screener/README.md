# ResumeAI – AI-Powered Resume Screening Tool

> Automatically screen and rank job candidates using NLP, TF-IDF vectorisation, and cosine similarity.  
> Built with Python · Flask · scikit-learn · NLTK · SQLite

---

## Table of Contents

1. [Overview](#overview)
2. [Features](#features)
3. [Project Structure](#project-structure)
4. [Tech Stack](#tech-stack)
5. [Quick Start](#quick-start)
6. [Running the Web App](#running-the-web-app)
7. [Using the CLI](#using-the-cli)
8. [Running Tests](#running-tests)
9. [How It Works](#how-it-works)
10. [API Reference](#api-reference)
11. [Configuration](#configuration)
12. [Sample Data](#sample-data)
13. [Troubleshooting](#troubleshooting)

---

## Overview

ResumeAI analyses PDF and DOCX resumes against a job description using Natural Language Processing.  
It ranks candidates by a composite score combining **TF-IDF cosine similarity** and **keyword overlap ratio**, stores every session in SQLite, and presents results in both a web dashboard and a command-line interface.

---

## Features

| Feature | Details |
|---|---|
| **File support** | PDF (pdfminer.six + PyPDF2 fallback), DOCX |
| **NLP pipeline** | Tokenisation → stopword removal → lemmatisation (NLTK) |
| **Scoring** | TF-IDF + cosine similarity (70%) + keyword overlap (30%) |
| **Ranking** | Tiered labels: Excellent / Strong / Good / Fair / Low |
| **Visualisation** | Horizontal bar chart (matplotlib) saved per session |
| **Persistence** | SQLite database; full session history |
| **Web interface** | Flask app with drag-and-drop upload |
| **CLI** | Batch processing with optional CSV export |
| **Tests** | 30+ unit & integration tests (pytest) |
| **Modular code** | `extract_text()`, `preprocess_text()`, `score_resume()`, `rank_candidates()` |

---

## Project Structure

```
resume_screener/
├── app.py                  # Flask application (entry point)
├── cli.py                  # Command-line interface
├── requirements.txt        # Python dependencies
├── README.md
│
├── utils/
│   ├── __init__.py
│   ├── extractor.py        # PDF/DOCX text extraction
│   ├── preprocessor.py     # NLP preprocessing & skill extraction
│   ├── scorer.py           # TF-IDF scoring & candidate ranking
│   ├── database.py         # SQLite persistence layer
│   └── visualizer.py       # Matplotlib bar-chart generation
│
├── templates/
│   ├── index.html          # Main screening page
│   ├── history.html        # Session history list
│   └── session.html        # Session detail view
│
├── static/
│   ├── css/style.css       # Dark-mode design system
│   ├── js/main.js          # Frontend logic (fetch API, drag-drop)
│   ├── charts/             # Auto-generated ranking charts
│   └── uploads/            # Temporary uploaded files
│
├── sample_data/
│   ├── job_description.txt         # Sample ML Engineer JD
│   ├── resume_alex_chen.txt        # Strong match (Senior ML Eng)
│   ├── resume_priya_sharma.txt     # Good match (ML Eng)
│   ├── resume_james_okafor.txt     # Moderate match (Data Eng)
│   ├── resume_sarah_kim.txt        # Weak match (Frontend Dev)
│   └── resume_michael_torres.txt   # Strong match (AI Researcher)
│
└── tests/
    └── test_core.py        # Unit & integration tests
```

---

## Tech Stack

| Layer | Technology |
|---|---|
| Web framework | Flask 3.x |
| NLP preprocessing | NLTK (tokenisation, stopwords, WordNet lemmatiser) |
| ML / scoring | scikit-learn (TF-IDF, cosine similarity) |
| PDF extraction | pdfminer.six, PyPDF2 (fallback) |
| DOCX extraction | python-docx |
| Visualisation | matplotlib |
| Database | SQLite (stdlib `sqlite3`) |
| Data manipulation | pandas, numpy |

---

## Quick Start

### 1 — Clone / download the project

```bash
git clone https://github.com/yourname/resume-screener.git
cd resume-screener
```

### 2 — Create a virtual environment

```bash
python -m venv .venv

# Activate:
source .venv/bin/activate        # macOS / Linux
.venv\Scripts\activate           # Windows
```

### 3 — Install dependencies

```bash
pip install -r requirements.txt
```

### 4 — Download NLTK data (one-time)

```bash
python - <<'EOF'
import nltk
for pkg in ["stopwords", "wordnet", "punkt", "punkt_tab", "averaged_perceptron_tagger"]:
    nltk.download(pkg)
EOF
```

### 5 — (Optional) Download spaCy model

```bash
python -m spacy download en_core_web_sm
```

---

## Running the Web App

```bash
python app.py
```

Open your browser at **http://127.0.0.1:5000**

### Workflow

1. Enter the **job title** and paste (or upload) the **job description**.
2. Upload one or more **resume files** (PDF or DOCX).
3. Click **Analyse & Rank Candidates**.
4. View the ranked table, match percentages, matched keywords, and chart.
5. All sessions are stored — browse **History** to revisit past screenings.

---

## Using the CLI

```bash
# Screen all resumes in the sample_data folder:
python cli.py --jd sample_data/job_description.txt \
              --resumes sample_data/ \
              --title "Senior ML Engineer"

# Screen specific files and save CSV:
python cli.py --jd sample_data/job_description.txt \
              --resumes sample_data/resume_alex_chen.txt \
                        sample_data/resume_priya_sharma.txt \
              --output results.csv

# Show only top 3 candidates, skip DB:
python cli.py --jd sample_data/job_description.txt \
              --resumes sample_data/ \
              --top 3 --no-db
```

### CLI Arguments

| Argument | Description |
|---|---|
| `--jd PATH` | Job description file (`.txt`, `.pdf`, `.docx`) |
| `--resumes PATH [PATH ...]` | Resume file(s) or folder |
| `--title TEXT` | Label for this screening session |
| `--output PATH` | Save ranked results to CSV |
| `--top N` | Limit output to top N candidates |
| `--no-db` | Skip saving to SQLite database |

---

## Running Tests

```bash
# All tests with verbose output:
pytest tests/ -v

# With coverage report:
pytest tests/ -v --cov=utils --cov-report=term-missing

# Run a specific test class:
pytest tests/test_core.py::TestScoreResume -v
```

---

## How It Works

### 1. Text Extraction (`utils/extractor.py`)

```
File (PDF/DOCX)  →  extract_text()  →  raw text string
```

- PDF: `pdfminer.six` (primary) → `PyPDF2` (fallback)
- DOCX: `python-docx` (paragraphs + table cells)
- Error handling for corrupted or password-protected files

### 2. Preprocessing (`utils/preprocessor.py`)

```
raw text  →  lowercase  →  remove special chars  →  tokenise
          →  remove stopwords  →  lemmatise  →  clean string
```

### 3. Scoring (`utils/scorer.py`)

```
score = 0.70 × cosine_similarity(TF-IDF(resume), TF-IDF(JD))
      + 0.30 × (|JD keywords ∩ resume tokens| / |JD keywords|)
```

TF-IDF uses unigrams + bigrams, sublinear term-frequency scaling.

### 4. Ranking

Candidates are sorted by descending score and assigned tiers:

| Match % | Tier |
|---|---|
| ≥ 80% | Excellent |
| 60–79% | Strong |
| 40–59% | Good |
| 20–39% | Fair |
| < 20% | Low |

### 5. Persistence

Every screening session is stored in `screening_results.db` (SQLite):

- **`sessions`** table: job title, job description, timestamp
- **`candidates`** table: rank, name, score, match%, tier, keywords

---

## API Reference

| Endpoint | Method | Description |
|---|---|---|
| `/` | GET | Main screening page |
| `/screen` | POST | Run screening (multipart form) |
| `/history` | GET | Session history page |
| `/session/<id>` | GET | Session detail page |
| `/api/sessions` | GET | JSON list of all sessions |
| `/api/session/<id>` | GET | JSON detail for one session |

### POST `/screen` — Form Fields

| Field | Type | Required | Description |
|---|---|---|---|
| `job_title` | text | No | Position label |
| `job_description` | text | Yes* | Pasted JD text |
| `job_desc_file` | file | Yes* | JD as PDF/DOCX |
| `resumes` | file(s) | Yes | Resume files |

*At least one of `job_description` or `job_desc_file` is required.

---

## Configuration

| Variable | Default | Description |
|---|---|---|
| `SECRET_KEY` | `resume-screener-secret-2024` | Flask session secret |
| `UPLOAD_FOLDER` | `static/uploads/` | Temporary file storage |
| `MAX_CONTENT_LENGTH` | 16 MB | Maximum upload size |
| `DB_PATH` (in `database.py`) | `screening_results.db` | SQLite file path |

Set environment variables before running:

```bash
export SECRET_KEY="your-secure-secret"
python app.py
```

---

## Sample Data

Five sample resumes are provided in `sample_data/`:

| File | Candidate | Expected Match |
|---|---|---|
| `resume_alex_chen.txt` | Alex Chen | 🟢 Excellent (Senior ML Eng, 7 yrs) |
| `resume_michael_torres.txt` | Dr. Michael Torres | 🟢 Excellent (AI Researcher, PhD) |
| `resume_priya_sharma.txt` | Priya Sharma | 🔵 Strong (ML Eng, 5 yrs) |
| `resume_james_okafor.txt` | James Okafor | 🟡 Good (Data Eng, transitioning) |
| `resume_sarah_kim.txt` | Sarah Kim | 🔴 Low (Frontend Dev) |

---

## Troubleshooting

**`ModuleNotFoundError: No module named 'pdfminer'`**  
→ Run `pip install pdfminer.six`

**`LookupError: Resource punkt not found`**  
→ Run `python -m nltk.downloader punkt punkt_tab stopwords wordnet`

**`Port 5000 already in use`**  
→ Change the port: `python app.py` then edit `app.run(port=5001)` in `app.py`

**Empty results after upload**  
→ Ensure your PDF is not scanned/image-only. Use a text-based PDF or convert with OCR first.

**Database locked error**  
→ Only one process should write to `screening_results.db` at a time.

---

## License

MIT License — free to use and modify for personal or commercial projects.
