# 🇹🇳 Tunisia Job Market Intelligence Platform

An end-to-end data pipeline that scrapes job postings from major Tunisian portals, stores them in PostgreSQL, extracts skills via NLP, generates AI-powered market summaries using a local LLaMA3 model, and exports clean datasets for Power BI dashboards.


## Results

| Metric | Value |
|---|---|
| Total jobs collected | 1,200+ |
| Sources scraped | 4 portals |
| Skills tracked | 75+ |
| CSVs exported | 10 files |
| AI summaries | Daily (LLaMA3) |


## Architecture

```
Scraping (Python + Selenium)
        ↓
PostgreSQL Database (7 tables)
        ↓
Analysis (NLP + pandas)     →    AI Summary (OpenRouter / LLaMA3)
        ↓
Data Cleaning (data/clean_data.py)
        ↓
CSV Export (data/export_data.py)
        ↓
Power BI Dashboard
```


## Project Structure

```
tunisia-jobs/
├── scrapers/
│   ├── base_scraper.py        # Shared base class + Selenium factory
│   ├── keejob.py      # Keejob.com scraper
│   ├── emploitunisie.py           # EmploiTunisie.com scraper (Selenium)
│   ├── rekrute.py             # ReKrute.com scraper
│   └── linkedin.py            # LinkedIn scraper (40 keywords)
├── database/
│   ├── schema.sql             # Full PostgreSQL schema (7 tables)
│   └── db_manager.py          # DB connection + all query helpers
├── analysis/
│   ├── skills_analysis.py     # NLP skill extraction (90+ skills dict)
│   ├── salary_analysis.py     # Salary range parsing from raw text
│   └── trends.py              # Monthly demand evolution
├── data/
│   ├── clean_data.py          # Title/location/contract normalization
│   └── export_data.py         # Export 10 Power BI-ready CSVs
├── ai/
│   └── summarizer.py          # OpenRouter LLaMA3 market trend summaries
├── exports/                   # Auto-generated CSVs for Power BI
├── main.py                    # Pipeline orchestrator + daily scheduler
├── update_descriptions.py     # Backfill job descriptions from detail pages
├── recount_skills.py          # Force fresh skills recount
├── requirements.txt
└── .env.example
```


## Tech Stack

| Layer | Technology |
|---|---|
| Scraping | Python, Selenium, BeautifulSoup, Requests |
| Storage | PostgreSQL, SQLAlchemy |
| Analysis | pandas, NLTK, scikit-learn |
| AI | OpenRouter (LLaMA 3 API) |
| Orchestration | schedule |
| Export | pandas CSV |
| Visualization | Power BI |


## Quick Start

### 1. Clone & install

```bash
git clone https://github.com/armi64bit/tunisia-jobs.git
cd tunisia-jobs
python -m venv .venv
.venv\Scripts\activate        # Windows
pip install -r requirements.txt
```

### 2. Configure environment

```bash
cp .env.example .env
# Fill in DB credentials and OpenRouter settings
```

### 3. Set up PostgreSQL

```bash
psql -U postgres -c "CREATE DATABASE tunisia_jobs;"
psql -U postgres -d tunisia_jobs -f database/schema.sql
```

### 4. Configure OpenRouter

Add your OpenRouter API key to `.env` as `OPENROUTER_API_KEY`. The default
model is `openrouter/free`, which automatically selects an available free
model. Set `OPENROUTER_MODEL` to another OpenRouter model when needed.

### 5. Run the pipeline

```bash
python main.py --once
```

This single command runs: **scrape → analyze → AI summary → clean → export**

To search LinkedIn using skills and roles found in a CV, provide a PDF or text
CV. The scraper searches Tunisia jobs using up to ten recognized terms:

```bash
python main.py --once --cv path\to\cv.pdf
```

To regenerate the analysis and AI summary from jobs already in PostgreSQL,
skip scraping:

```bash
python main.py --once --skip-scraping
```

Supported CV formats are `.pdf`, `.txt`, and `.md`. Without `--cv`, the
default broad LinkedIn keyword list is used.


## Exported CSVs

| File | Description | Power BI Use |
|---|---|---|
| `jobs_clean.csv` | All jobs — cleaned titles, locations, contracts | Main table |
| `skills.csv` | 75+ skills with frequency + category | Bar chart, heatmap |
| `by_location.csv` | Jobs per Tunisian governorate | Map visual |
| `by_contract.csv` | CDI / CDD / SIVP / Stage breakdown | Donut chart |
| `monthly_by_source.csv` | Jobs per source per month | Trend line |
| `top_companies.csv` | Top 50 hiring companies | Bar chart |
| `ai_summary.csv` | Latest LLaMA3 market summary | Text card |


## Daily Automation

```bash
# Run once manually
python main.py --once

# Start daily scheduler (runs every day at 07:00)
python main.py
```


## Utility Scripts

```bash
# Backfill descriptions for jobs scraped without detail pages
python update_descriptions.py

# Force fresh skills recount (e.g. after DB reset)
python recount_skills.py
```


## Sources

| Portal | Method | Jobs/run |
|---|---|---|
| [Keejob.com](https://www.keejob.com) | requests + BeautifulSoup | ~300 |
| [EmploiTunisie.com](https://www.emploitunisie.com) | Selenium | ~375 |
| [ReKrute.com](https://www.rekrute.com) | requests | ~5 |
| [LinkedIn](https://www.linkedin.com/jobs) | Selenium (40 keywords) | ~260 |


## Database Schema

```sql
jobs          -- Core job postings
companies     -- Employer profiles
sectors       -- Hierarchical sectors
skills        -- Skill reference table
job_skills    -- Jobs ↔ Skills (M:M)
salaries      -- Extracted salary ranges (TND)
scrape_logs   -- Scraping audit log
```


## Key Findings (June 2026)



## Notes



## Author

**Chiraz Kitar** — Data Analysis Project, June 2026