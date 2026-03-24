# 🤖 AI Jobs Aggregator

> A Compound AI System for automated job matching and daily digest delivery — fully autonomous, zero cost, runs every morning at 06:00 CET.

**Built by [Shahbaz Khalilli](https://www.linkedin.com/in/shahbaz-khalilli0/) | MSc Data Science, KU Eichstätt-Ingolstadt | 2026**

---

## 📋 Table of Contents

- [What It Does](#what-it-does)
- [Architecture](#architecture)
- [Technology Stack](#technology-stack)
- [Project Structure](#project-structure)
- [Setup and Deployment](#setup-and-deployment)
- [Version History](#version-history)
- [Key Engineering Challenges](#key-engineering-challenges)
- [About This Project](#about-this-project)

---

## What It Does

This system automatically scrapes job postings from company career pages every morning, evaluates each posting against a pre-loaded candidate profile using a three-phase AI pipeline, scores each role on a **0–100 scale using deterministic Python logic**, and delivers a personalized HTML email digest containing only the most relevant matches — completely autonomously, every day at 06:00 CET.

| Metric | Value |
|--------|-------|
| Daily runtime | ~3–5 minutes (fully automated) |
| Cost | **100% free** (GitHub Actions + Groq + Supabase free tiers) |
| LLM Model | `llama-3.3-70b-versatile` via Groq API |
| Scoring | Deterministic Python — zero LLM arithmetic |
| Job deduplication | URL primary key in PostgreSQL — never evaluates the same job twice |
| Email deduplication | `email_sent` flag — never sends the same job twice |

---

## Architecture

The system follows a strict **Extract → Compute → Evaluate** pattern, separating NLP responsibilities from mathematical logic entirely. This design emerged from two failed iterations where asking an LLM to perform arithmetic or cross-reference two documents simultaneously produced unreliable results.

```
┌─────────────────────────────────────────────────────────┐
│                    DAILY PIPELINE                        │
│                                                         │
│  Phase 0         Phase 1          Phase 2               │
│  ────────        ────────         ────────              │
│  Load            LLM extracts     Python computes       │
│  cv_profile      JD facts only    set intersection      │
│  .json once      (no comparison)  + scoring rubric      │
│                                                         │
│  Phase 3         Phase 4          Phase 5               │
│  ────────        ────────         ────────              │
│  LLM writes      Store in         Email unsent          │
│  2-sentence      Supabase         jobs → mark           │
│  rationale       PostgreSQL       as sent               │
└─────────────────────────────────────────────────────────┘
```

### Phase 0 — Static CV Loading *(once per run)*

The candidate's CV is pre-parsed into `cv_profile.json` containing a normalized skills set, years of experience, education level, seniority, and language capabilities. Loaded once at startup and reused for every job — eliminates cognitive overload from asking the LLM to hold two documents simultaneously.

### Phase 1 — JD Fact Extraction *(LLM, temperature=0.0)*

The LLM receives **only the job description**. It is explicitly forbidden from referencing the candidate or performing any comparison. Its sole task is structured extraction into a JSON schema:

```json
{
  "required_skills": ["python", "sql", "machine learning"],
  "preferred_skills": ["spark", "airflow"],
  "min_years_experience": 2,
  "education_required": "master",
  "is_student_or_intern": false,
  "seniority": "mid",
  "explicit_german_required": false
}
```

### Phase 2 — Deterministic Python Scoring *(no LLM)*

Python performs set intersection between `cv_profile.skills` and `jd_profile.required_skills` using a `SKILL_ALIASES` normalization layer. **All scoring arithmetic is pure Python — zero LLM involvement.**

| Component | Max Points | Logic |
|-----------|-----------|-------|
| Required Skills Match | 50 | `required_overlap_pct * 50` |
| Preferred Skills Match | 15 | `preferred_overlap_pct * 15` |
| Experience Match | 20 | +20 if delta ≥ 0, +10 if delta = -1, 0 if gap > 1yr |
| Student / Intern Boost | +20 | Applied if `is_student_or_intern = TRUE` |
| German Language Penalty | −40 | Applied if `explicit_german_required = TRUE` |

### Phase 3 — Contextual Reasoning *(LLM, temperature=0.2)*

The LLM receives **only the pre-computed numerical metrics** from Phase 2 — never raw text. It generates exactly two sentences summarizing why the candidate is or is not a fit. This prevents the model from inventing reasons not grounded in the actual computation.

---

## Technology Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| Web Scraping | Playwright + httpx + BeautifulSoup | Render JS pages, parse HTML, extract jobs |
| ATS Parsing | Custom `__NEXT_DATA__` JSON crawler | Extract jobs from JOIN.com ATS platform |
| LLM Inference | Groq API — `llama-3.3-70b-versatile` | JD extraction + reasoning generation |
| Scoring Engine | Pure Python — set operations | Deterministic overlap calculation |
| Database | Supabase PostgreSQL (eu-west-2) | Persistent job storage with deduplication |
| Email Delivery | Gmail SMTP (`smtplib`) | HTML digest + crash alerts |
| Scheduling | GitHub Actions cron | Daily automated execution at 05:00 UTC |
| Package Management | `uv` + `pyproject.toml` | Dependency management |

---

## Project Structure

```
ai-jobs-aggregator/
│
├── .github/
│   └── workflows/
│       └── daily_pipeline.yml      # GitHub Actions cron — runs daily 05:00 UTC
│
├── config/
│   ├── cv_profile.json             # Candidate CV — normalized skills and profile
│   ├── companies.json              # Target companies with career page URLs
│   └── prompt_template.txt         # Phase 1 LLM extraction prompt
│
├── core/
│   ├── agent.py                    # Main evaluation pipeline — Phases 0–4
│   ├── scraper.py                  # Multi-company job scraper with Playwright
│   ├── database.py                 # Supabase PostgreSQL connection and queries
│   └── main.py                     # Pipeline orchestrator
│
├── utils/
│   ├── emailer.py                  # HTML email digest + crash alert sender
│   ├── db_viewer.py                # Export evaluated jobs to Markdown report
│   ├── inspect_db.py               # Terminal preview + Excel export
│   └── clear_db.py                 # Truncate database (dev utility)
│
├── data/                           # Ephemeral — regenerated each run (gitignored)
│   └── multi_company_raw_jobs.json
│
├── .env                            # Secrets — never committed (gitignored)
├── pyproject.toml
├── requirements.txt
└── README.md
```

---

## Setup and Deployment

### Prerequisites

- Python 3.11+
- `uv` package manager: `pip install uv`
- [Groq API key](https://console.groq.com) — free
- [Supabase account](https://supabase.com) — free
- Gmail account with [App Password](https://myaccount.google.com/apppasswords) enabled

### Local Installation

```bash
# 1. Clone the repository
git clone https://github.com/sahbaz00/ai-jobs-aggregator
cd ai-jobs-aggregator

# 2. Install dependencies
uv sync
playwright install chromium

# 3. Configure environment
cp .env.example .env
# Fill in your credentials in .env

# 4. Run the pipeline
python core/main.py
```

### Environment Variables

```bash
GROQ_API_KEY=gsk_...              # Groq API key
SENDER_EMAIL=your@gmail.com       # Gmail sender address
EMAIL_PASSWORD=xxxx xxxx xxxx     # Gmail App Password
RECEIVER_EMAIL=your@gmail.com     # Digest destination
SUPABASE_DB_URL=postgresql://...  # Supabase connection string
```

### Supabase Table Setup

Run this once in your Supabase SQL Editor:

```sql
CREATE TABLE IF NOT EXISTS evaluated_jobs (
    url TEXT PRIMARY KEY,
    title TEXT,
    company TEXT,
    ai_score INTEGER,
    ai_reasoning TEXT,
    date_discovered TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    email_sent BOOLEAN DEFAULT FALSE
);
```

### GitHub Actions Deployment

1. Push to `main` branch
2. Go to **Settings → Secrets and variables → Actions**
3. Add all five environment variables as repository secrets
4. Trigger manually: **Actions → Daily AI Jobs Pipeline → Run workflow**
5. After successful manual test, the cron fires automatically every day at **05:00 UTC (06:00 CET)**

### Groq API Token Budget

| Metric | Per Job | 30 Jobs/Day | Free Tier Limit | Usage |
|--------|---------|-------------|-----------------|-------|
| API Calls | 2 | 60 | 1,000 RPD | 6% |
| Phase 1 Tokens | ~1,250 | 37,500 | 100,000 TPD | 38% |
| Phase 3 Tokens | ~480 | 14,400 | 100,000 TPD | 14% |
| **Total Tokens** | **~1,730** | **~51,900** | **100,000 TPD** | **52%** |

---

## Version History

| Version | Design Pattern | Key Innovation | Critical Failure Fixed |
|---------|---------------|----------------|----------------------|
| **V1.0** | Zero-Shot Text-to-Score | End-to-end pipeline proof of concept | — |
| **V2.0** | JSON Extraction + Deterministic Math | LLM as extractor, Python as calculator | LLM arithmetic hallucinations |
| **V3.0** | Compound AI — Extract → Compute → Evaluate | Pre-loaded CV, LLM forbidden from comparing | Lazy evaluation — `missing_skills: []` |
| **V3.1** | Cloud-Native Production | Groq API + Supabase + GitHub Actions | Local infrastructure dependency |

### V1.0 — The Monolithic LLM Evaluator *(Deprecated)*

Asked a single LLM to understand requirements AND calculate a score in one prompt. Produced 100/100 for Java roles when the candidate had zero Java experience — the model was generating plausible-sounding assessments rather than accurate ones.

### V2.0 — The Deterministic JSON Engine *(Superseded)*

Separated LLM extraction from Python scoring. Eliminated arithmetic hallucinations entirely. However, asking the LLM to extract CV skills, JD skills, AND compute the difference was cognitive overload — the model consistently returned `missing_core_tech_skills: []` for every job, causing score inflation.

### V3.0 — The Compound AI Evaluator *(Validated)*

Pre-loaded the CV as a static dictionary. LLM extracts JD facts only — one task, not three. Python performs set intersection. Validated on 9 jobs: 90+ scores for relevant Working Student roles, 0.0 for Java/SAP roles requiring absent skills, correct penalties for seniority mismatches.

### V3.1 — Production Cloud Migration *(Current)*

Migrated from local Ollama (gemma3:12b, 3–5 min/job on CPU) to Groq API (llama-3.3-70b, 2–4 sec/job on H100). SQLite replaced with Supabase PostgreSQL. Windows Task Scheduler replaced with GitHub Actions cron. Eight bug fixes applied — see below.

---

## Key Engineering Challenges

### 1. LLM Arithmetic Hallucinations *(V1 → V2)*
Asking the LLM to both understand job requirements and calculate a score produced confident but wrong numbers. **Fix:** Complete separation — LLM never touches a number, Python handles all arithmetic.

### 2. Cognitive Overload in Extraction *(V2 → V3)*
Asking the LLM to extract CV skills, JD skills, and compute the difference in one prompt caused the model to return empty arrays — satisfying the JSON structure consumed its full attention. **Fix:** Pre-load CV as a static dictionary, ask LLM only to extract JD skills.

### 3. Local Infrastructure Dependency *(V3 → V3.1)*
V3.0 required the developer's personal machine to be powered on with Ollama running. **Fix:** Groq API for inference, GitHub Actions for scheduling — zero local dependencies.

### 4. Ephemeral Filesystem on GitHub Actions
GitHub Actions resets the entire filesystem between runs. The scraper relied on a local JSON file for deduplication. **Fix:** In-memory `seen_urls = set()` within each run, persistent storage via Supabase PostgreSQL across runs.

### 5. Email Deduplication
Manual testing triggered multiple daily runs, sending the same jobs repeatedly. **Fix:** Added `email_sent BOOLEAN` column — only unsent jobs are queried, marked `TRUE` only after confirmed SMTP delivery.

### 6. Non-Deterministic ATS Responses
JOIN.com's API returned different job slugs for the same posting depending on geographic request origin — the developer's German IP vs. GitHub's London server. **Fix:** Track `jobs_before_page` and `jobs_after_page` counts, stop pagination when no net-new unique jobs are added regardless of what slugs appear.

### 7. Soft Skill Contamination
The LLM occasionally extracted German soft skills (`Teamfähigkeit`, `Kommunikationsfähigkeit`) as required technical skills, incorrectly penalizing the candidate. **Fix:** Explicit `DO NOT EXTRACT` list in Phase 1 prompt with German examples.

### 8. String Matching Brittleness
British/American spelling variations (`modelling` vs `modeling`) and abbreviations (`ml` vs `machine learning`) caused false skill mismatches. **Fix:** `SKILL_ALIASES` normalization dictionary applied to both CV and JD skills before set intersection.

---

## About This Project

This project was built as both a **practical daily job search tool** and a **portfolio demonstration** of production-grade MLOps thinking.

**Competencies demonstrated:**

- **Compound AI System Design** — Strict phase separation with defined interfaces between NLP extraction, deterministic scoring, and contextual reasoning
- **MLOps and Automation** — Fully automated pipeline with monitoring, error alerting, and structured logging
- **Cloud-Native Architecture** — Zero-cost infrastructure using GitHub Actions + Groq API + Supabase
- **Iterative Engineering** — Four documented architectural versions with explicit failure analysis and principled migration decisions
- **Data Engineering** — Custom scrapers handling JavaScript SPAs, ATS API crawling, and multi-source aggregation with multi-layer deduplication

---

*Automated by Shahbaz's MLOps Pipeline — running daily since March 2026*