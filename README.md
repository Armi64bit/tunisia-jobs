<div align="center">

# 🇹🇳 Tunisia Job Market Intelligence

**Collect. Understand. Match. Apply.**

An end-to-end platform for collecting and analysing Tunisian job listings, with a live dashboard, CV matching, AI assistance, and Power BI-ready exports.

[![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/API-FastAPI-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Next.js](https://img.shields.io/badge/Frontend-Next.js-000000?logo=next.js&logoColor=white)](https://nextjs.org/)
[![PostgreSQL](https://img.shields.io/badge/Database-PostgreSQL-4169E1?logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![OpenRouter](https://img.shields.io/badge/AI-OpenRouter-6E56CF)](https://openrouter.ai/)

</div>

## Contents

| | | |
|---|---|---|
| [Highlights](#highlights) | [Architecture](#architecture) | [Installation](#installation) |
| [Run the app](#run-the-application) | [Pipeline commands](#run-the-pipeline-from-the-command-line) | [API](#api-endpoints) |
| [Exports](#generated-exports) | [Testing](#testing-and-frontend-checks) | [Database](#database-model) |

## Highlights

| Capability | What it provides |
|---|---|
| **Job collection** | Scraping from Apify, KeeJob, EmploiTunisie, ReKrute, and LinkedIn |
| **Market intelligence** | Skill, salary, and monthly trend analysis with Power BI-ready CSVs |
| **CV matching** | Skill extraction, ranked matches, covered and missing skills, and recommendations |
| **AI assistance** | Market summaries, match analysis, and generated cover letters through OpenRouter |
| **Pipeline control** | Background runs, live progress, logs, stop requests, and scrape-run history |
| **Candidate workflow** | Applications, reply tracking, scrape snapshot selection, and export downloads |

<details>
<summary><strong>Project background</strong></summary>

This project began as a fork of [Chiraz Kitar's Tunisia Jobs project](https://github.com/chirazkitar/tunisia-jobs). The original repository provided the initial scraping pipeline, database model, analysis scripts, AI summaries, and Power BI exports.

The current extensions are maintained by **Bahaa Eddine Bouzid** ([Armi64bit](https://github.com/Armi64bit)). They include the FastAPI backend, Next.js dashboard, CV workflow, scrape-run snapshots, application tracking, cover-letter generation, and compatibility handling for legacy data.

</details>

## Architecture

```text
Job portals / Apify
        |
        v
Python scrapers -> PostgreSQL
                         |
                         v
             NLP + salary + trend analysis
                         |
                         +--> OpenRouter market summary
                         +--> CV matching and cover letters
                         v
                  CSV exports / Power BI

Next.js dashboard <-> FastAPI backend <-> PostgreSQL and pipeline
```

The Python pipeline owns collection and analysis. The FastAPI layer exposes that workflow to the dashboard, while PostgreSQL remains the source of truth for jobs, matches, scrape snapshots, and applications.

## Project structure

<details>
<summary><strong>Expand project tree</strong></summary>

```text
tunisia-jobs/
├── main.py                         # Pipeline entry point and daily scheduler
├── cv_matching.py                  # CV text and keyword extraction
├── cv_job_matcher.py               # CV-to-job scoring and AI match analysis
├── scrapers/
│   ├── base_scraper.py             # Shared Selenium and scraper helpers
│   ├── apify_jobs.py               # Apify jobs source
│   ├── keejob.py                   # KeeJob scraper
│   ├── emploitunisie.py            # EmploiTunisie scraper
│   ├── rekrute.py                  # ReKrute scraper
│   └── linkedin.py                 # LinkedIn scraper
├── analysis/
│   ├── skills_analysis.py          # Skill extraction and counts
│   ├── salary_analysis.py          # Salary range parsing
│   └── trends.py                   # Monthly demand trends
├── ai/
│   ├── summarizer.py               # AI market summaries
│   └── cover_letter.py             # AI cover-letter generation
├── data/
│   ├── clean_data.py               # Data normalization
│   └── export_data.py              # Power BI-ready CSV exports
├── database/
│   ├── schema.sql                  # PostgreSQL schema
│   └── db_manager.py               # Database queries and persistence
├── backend/
│   └── main.py                     # FastAPI API on port 8001
├── frontend/
│   ├── app/                        # Next.js app entry points and styles
│   ├── components/                 # Dashboard views and UI components
│   └── lib/                        # API client, types, matching, and demo data
├── exports/                        # Generated CSV files
├── uploads/                        # Uploaded CV files used by the backend
├── requirements.txt                # Pipeline dependencies
└── frontend/package.json            # Frontend dependencies and scripts
```

</details>

## Requirements

| Requirement | Purpose |
|---|---|
| Python 3.11+ | Scrapers, analysis, matching, and backend support |
| PostgreSQL | Persistent job and workflow data |
| Node.js and npm | Next.js dashboard |
| Selenium-compatible browser | Browser-based source scrapers |
| OpenRouter API key | AI summaries, match analysis, and cover letters |

## Configuration

Create a `.env` file in the repository root. Database settings can be supplied as a complete `DATABASE_URL`, or with the individual variables below:

```dotenv
DATABASE_URL=postgresql://postgres:password@localhost:5432/tunisia_jobs

# Used when DATABASE_URL is not set
DB_USER=postgres
DB_PASSWORD=password
DB_HOST=localhost
DB_PORT=5432
DB_NAME=tunisia_jobs

OPENROUTER_API_KEY=your_key_here
OPENROUTER_MODEL=openrouter/free
EXPORT_DIR=exports

# Optional backend configuration
BACKEND_CORS_ORIGINS=http://localhost:3000
BACKEND_CORS_ORIGIN_REGEX=http://(?:localhost|127\.0\.0\.1|192\.168\.\d+\.\d+):\d+
```

The frontend reads `frontend/.env.local`:

```dotenv
NEXT_PUBLIC_API_BASE_URL=http://localhost:8001
```

When the frontend is opened from another machine, set this value to the backend's reachable URL and configure matching backend CORS origins.

## Installation

> [!NOTE]
> The commands below use PowerShell on Windows. Activate the virtual environment before running Python commands.

```powershell
git clone https://github.com/armi64bit/tunisia-jobs.git
cd tunisia-jobs

python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt

psql -U postgres -c "CREATE DATABASE tunisia_jobs;"
psql -U postgres -d tunisia_jobs -f database/schema.sql

cd frontend
npm install
cd ..
```

## Run the application

### 1. Start the API

Start the API from the repository root:

```powershell
python backend/main.py
```

The API is available at `http://localhost:8001`. A health check is available at `http://localhost:8001/health`.

### 2. Start the dashboard

In a second terminal, start the dashboard:

```powershell
cd frontend
npm run dev
```

Open **[http://localhost:3000](http://localhost:3000)**. The dashboard provides:

- **Overview:** job totals, source breakdowns, employers, and a filterable listing view.
- **Scraper run:** PDF CV upload, drag and drop, pipeline controls, live progress, logs, scrape-run selection, and job export.
- **CV matches:** ranked jobs, match scores, covered and missing skills, match explanations, generated cover letters, applications, and match CSV export. Expanded cards stack their actions on mobile and keep long details and letters readable within the viewport.
- **Applications:** saved applications, reply tracking, and application status management.

## Run the pipeline from the command line

Run one complete scrape, analysis, AI summary, and export cycle:

```powershell
python main.py --once
```

Run without scraping and use jobs already in PostgreSQL:

```powershell
python main.py --once --skip-scraping
```

Use a CV to provide search terms to LinkedIn:

```powershell
python main.py --once --cv path\to\cv.pdf
```

Run CV matching after the pipeline. The optional scrape-run ID limits matching to a selected completed run:

```powershell
python main.py --once --cv path\to\cv.pdf --match-cv
python main.py --once --cv path\to\cv.pdf --skip-scraping --match-cv --scrape-run-id 12
```

Supported CV formats for the command-line pipeline are `.pdf`, `.txt`, and `.md`. The backend upload workflow accepts PDF files up to 10 MB.

To start the daily scheduler instead of a one-time run:

```powershell
python main.py
```

The scheduler runs the pipeline daily at 07:00.

## API endpoints

The FastAPI backend exposes:

| Endpoint | Purpose |
|---|---|
| `GET /health` | Health check |
| `GET /jobs` | Browse stored jobs with pagination |
| `GET /sources` | List supported sources |
| `GET /scrape-runs` | List successful and partial scrape snapshots |
| `GET /cv-matches` | List ranked CV matches, optionally by `scrape_run_id` |
| `GET /applications` | List saved applications |
| `POST /applications` | Create an application |
| `PATCH /applications/{job_id}` | Update application reply status |
| `DELETE /applications/{job_id}` | Remove an application |
| `DELETE /scrape-runs/{run_id}` | Remove a scrape snapshot and its links |
| `GET /pipeline/status` | Read progress, steps, logs, and errors |
| `POST /pipeline/run` | Start a background pipeline with optional CV and matching flags |
| `POST /pipeline/stop` | Request that the active pipeline stop |
| `POST /cover-letters` | Generate and save a cover letter for a job |
| `GET /export/jobs` | Download `jobs_clean.csv` |
| `GET /export/cv-matches` | Download `cv_matches.csv` |

Interactive API documentation is available at `http://localhost:8001/docs` while the backend is running.

## Generated exports

The pipeline writes CSV files to `exports/`:

| File | Contents |
|---|---|
| `jobs_clean.csv` | Normalized job listings |
| `skills.csv` | Skill frequencies and categories |
| `by_location.csv` | Jobs by governorate or location |
| `by_contract.csv` | Contract-type breakdown |
| `monthly_by_source.csv` | Monthly jobs by source |
| `monthly_sector.csv` | Monthly jobs by sector |
| `monthly_total.csv` | Monthly total job volume |
| `skill_trend.csv` | Skill demand over time |
| `top_companies.csv` | Most active hiring companies |
| `ai_summary.csv` | Latest AI-generated market summary |
| `cv_matches.csv` | CV-to-job matching results |

These files can be imported into Power BI or downloaded through the backend export endpoints where supported.

## Utility scripts

```powershell
# Backfill descriptions for jobs without detail-page descriptions
python update_descriptions.py

# Recalculate skills after a database reset or skill-dictionary change
python recount_skills.py
```

## Testing and frontend checks

```powershell
# Backend tests
pytest backend

# Existing pipeline tests
pytest test_cv.py test_cv2.py

# Frontend checks
cd frontend
npm run typecheck
npm run build
```

## Database model

The schema includes the core job entities and the newer workflow tables:

```text
sectors, companies, jobs, skills, job_skills, salaries
scrape_logs, scrape_runs, scrape_run_jobs
job_applications
```

`cv_job_matches` is used by the CV matching workflow and is managed by the matching/database code alongside the base schema.

## Sources

| Source | Implementation |
|---|---|
| Apify | `scrapers/apify_jobs.py` |
| KeeJob | `scrapers/keejob.py` |
| EmploiTunisie | `scrapers/emploitunisie.py` |
| ReKrute | `scrapers/rekrute.py` |
| LinkedIn | `scrapers/linkedin.py` |

Scraper availability and result counts depend on the source site, network access, credentials, and the current run.
