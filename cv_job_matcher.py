# cv_job_matcher.py
# Matches CV profile to scraped jobs using AI
import os
import json
import logging
import requests
import pandas as pd
from datetime import date
from dotenv import load_dotenv
from database.db_manager import DBManager
from cv_matching import extract_cv_text, keywords_from_cv

load_dotenv()

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "openrouter/free")

logger = logging.getLogger("cv_job_matcher")


def analyze_job_match(cv_text: str, cv_keywords: list, job: dict) -> dict | None:
    """Use AI to analyze how well a job matches the CV."""
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        logger.warning("OPENROUTER_API_KEY not configured, skipping AI match analysis")
        return None

    job_desc = (job.get('description', '') or '').strip()
    if not job_desc:
        logger.warning(f"Job {job.get('id', 'unknown')} has no description, skipping")
        return None

    job_title = job.get('title', '') or ''
    job_company = job.get('company_name', '') or job.get('company', '') or ''

    prompt = f"""
Tu es un expert en recrutement. Analyse la correspondance entre ce CV et cette offre d'emploi.

CV (texte extrait):
{cv_text[:3000]}

Mots-clés du CV: {', '.join(cv_keywords)}

OFFRE D'EMPLOI:
Titre: {job_title}
Entreprise: {job_company}
Description: {job_desc[:2000]}

Réponds UNIQUEMENT en JSON valide avec ces champs:
{{
  "match_score": 0-100,
  "summary": "Résumé de l'offre en 2-3 phrases (français)",
  "why_good_match": "Pourquoi cette offre correspond au profil (français, max 3 phrases)",
  "missing_skills": ["compétence1", "compétence2"],
  "recommendation": "postuler|peut-etre|ignorer"
}}
"""

    try:
        response = requests.post(
            OPENROUTER_URL,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": OPENROUTER_MODEL,
                "messages": [
                    {"role": "system", "content": "Tu es un expert en recrutement. Réponds uniquement en JSON valide."},
                    {"role": "user", "content": prompt},
                ],
                "temperature": 0.2,
                "max_tokens": 500,
            },
            timeout=60,
        )
        if not response.ok:
            logger.warning(f"OpenRouter match analysis failed: {response.status_code} - {response.text[:200]}")
            return None

        data = response.json()
        
        # Check if response has expected structure
        if "choices" not in data or not data["choices"]:
            logger.warning(f"OpenRouter response missing choices: {data}")
            return None
            
        content = data["choices"][0].get("message", {}).get("content", "")
        if not content:
            logger.warning(f"OpenRouter returned empty content: {data}")
            return None
            
        content = content.strip()

        # Extract JSON from response
        import re
        json_match = re.search(r'\{.*\}', content, re.DOTALL)
        if json_match:
            result = json.loads(json_match.group())
            result['tokens_used'] = data.get("usage", {}).get("total_tokens", 0)
            return result

    except Exception as e:
        logger.error(f"Error analyzing job match: {e}")

    return None


def save_cv_match(db: DBManager, job_id: int, match_result: dict, cv_keywords: list):
    """Save CV-job match analysis to database."""
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS cv_job_matches (
            id              SERIAL PRIMARY KEY,
            job_id          INT REFERENCES jobs(id) ON DELETE CASCADE,
            cv_keywords     TEXT[],
            match_score     INT,
            summary         TEXT,
            why_good_match  TEXT,
            missing_skills  TEXT[],
            recommendation  VARCHAR(20),
            tokens_used     INT,
            created_at      TIMESTAMP DEFAULT NOW(),
            UNIQUE(job_id)
        )
        """
    )
    db.execute(
        """
        INSERT INTO cv_job_matches (job_id, cv_keywords, match_score, summary, why_good_match, missing_skills, recommendation, tokens_used)
        VALUES (:job_id, :cv_keywords, :match_score, :summary, :why_good_match, :missing_skills, :recommendation, :tokens_used)
        ON CONFLICT (job_id) DO UPDATE SET
            cv_keywords = EXCLUDED.cv_keywords,
            match_score = EXCLUDED.match_score,
            summary = EXCLUDED.summary,
            why_good_match = EXCLUDED.why_good_match,
            missing_skills = EXCLUDED.missing_skills,
            recommendation = EXCLUDED.recommendation,
            tokens_used = EXCLUDED.tokens_used,
            created_at = NOW()
        """,
        {
            "job_id": job_id,
            "cv_keywords": cv_keywords,
            "match_score": match_result.get("match_score", 0),
            "summary": match_result.get("summary", ""),
            "why_good_match": match_result.get("why_good_match", ""),
            "missing_skills": match_result.get("missing_skills", []),
            "recommendation": match_result.get("recommendation", "peut-etre"),
            "tokens_used": match_result.get("tokens_used", 0),
        }
    )


def get_jobs_for_cv_matching(db: DBManager, cv_keywords: list, limit: int = 50) -> list:
    """Get recent jobs that might match CV keywords."""
    # Build keyword filter
    keyword_conditions = " OR ".join([
        f"(j.title ILIKE '%{kw}%' OR j.description ILIKE '%{kw}%')" for kw in cv_keywords[:10]
    ])

    sql = f"""
        SELECT j.id, j.title, j.description, j.location, j.contract,
               j.experience, j.source, j.source_url, j.posted_at,
               c.name AS company_name
        FROM jobs j
        LEFT JOIN companies c ON c.id = j.company_id
        WHERE j.is_active = TRUE
          AND j.description IS NOT NULL
          AND j.description != ''
          AND ({keyword_conditions})
        ORDER BY j.scraped_at DESC
        LIMIT :limit
    """
    df = db.fetch(sql, {"limit": limit})
    logger.info(f"Found {len(df)} jobs with descriptions matching keywords")
    return df.to_dict(orient="records")


def run_cv_job_matching(cv_path: str, max_jobs: int = 50) -> list:
    """
    Main pipeline: extract CV keywords, find matching jobs, analyze with AI.
    Returns list of matched jobs with AI analysis.
    """
    logger.info(f"=== CV Job Matching started for {cv_path} ===")

    # 1. Extract CV text and keywords
    cv_text = extract_cv_text(cv_path)
    cv_keywords = keywords_from_cv(cv_text)
    logger.info(f"CV keywords: {cv_keywords}")

    # 2. Get matching jobs from DB
    db = DBManager()
    jobs = get_jobs_for_cv_matching(db, cv_keywords, limit=max_jobs)
    logger.info(f"Found {len(jobs)} potential matching jobs")

    # 3. Analyze each job with AI
    matched_jobs = []
    for i, job in enumerate(jobs):
        logger.info(f"Analyzing match {i+1}/{len(jobs)}: {job.get('title', '')[:50]}")
        match_result = analyze_job_match(cv_text, cv_keywords, job)
        if match_result:
            job['match_analysis'] = match_result
            job['cv_keywords'] = cv_keywords
            # Save to DB
            save_cv_match(db, job['id'], match_result, cv_keywords)
            matched_jobs.append(job)

    logger.info(f"=== CV Job Matching complete: {len(matched_jobs)} jobs analyzed ===")
    return matched_jobs


def export_cv_matches():
    """Export CV-matched jobs to CSV for dashboard."""
    db = DBManager()
    # Check if table exists first
    table_exists = db.fetch("""
        SELECT EXISTS (
            SELECT FROM information_schema.tables
            WHERE table_name = 'cv_job_matches'
        )
    """)
    if table_exists.empty or not table_exists.iloc[0, 0]:
        logger.info("cv_job_matches table doesn't exist yet, creating empty CSV")
        export_dir = os.getenv("EXPORT_DIR", "exports")
        os.makedirs(export_dir, exist_ok=True)
        pd.DataFrame(columns=[
            'id', 'title', 'company_name', 'location', 'contract', 'experience',
            'source', 'source_url', 'posted_at', 'scraped_at',
            'match_score', 'summary', 'why_good_match', 'missing_skills',
            'recommendation', 'cv_keywords', 'match_date'
        ]).to_csv(f"{export_dir}/cv_matches.csv", index=False, encoding='utf-8-sig')
        return pd.DataFrame()

    df = db.fetch("""
        SELECT j.id, j.title, j.location, j.contract, j.experience,
               j.source, j.source_url, j.posted_at, j.scraped_at,
               c.name AS company_name,
               m.match_score, m.summary, m.why_good_match, m.missing_skills,
               m.recommendation, m.cv_keywords, m.created_at AS match_date
        FROM cv_job_matches m
        JOIN jobs j ON j.id = m.job_id
        LEFT JOIN companies c ON c.id = j.company_id
        ORDER BY m.match_score DESC, m.created_at DESC
    """)

    export_dir = os.getenv("EXPORT_DIR", "exports")
    os.makedirs(export_dir, exist_ok=True)
    df.to_csv(f"{export_dir}/cv_matches.csv", index=False, encoding='utf-8-sig')
    logger.info(f"cv_matches.csv exported: {len(df)} rows")
    return df


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 3 or sys.argv[1] != "--cv":
        print("Usage: python cv_job_matcher.py --cv path/to/cv.pdf")
        sys.exit(1)

    cv_path = sys.argv[2]
    results = run_cv_job_matching(cv_path)
    export_cv_matches()
    print(f"\nMatched {len(results)} jobs. Results exported to exports/cv_matches.csv")