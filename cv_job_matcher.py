# cv_job_matcher.py
# Matches CV profile to scraped jobs using AI with optimized search
import os
import json
import logging
import re
import requests
import pandas as pd
from datetime import date, datetime
from collections import Counter
from dotenv import load_dotenv
from database.db_manager import DBManager
from cv_matching import extract_cv_text, keywords_from_cv, CV_KEYWORDS

load_dotenv()

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "openrouter/free")

logger = logging.getLogger("cv_job_matcher")

JUNIOR_ROLE_TERMS = (
    "software engineer", "software developer", "software development",
    "full stack", "fullstack", "front end", "frontend", "back end", "backend",
    "react developer", "java developer", "python developer", "developer",
    "développeur", "developpeur", "engineer", "ingénieur logiciel",
    "graduate", "junior", "entry level", "new grad", "associate",
)
SENIORITY_EXCLUSIONS = (
    "senior", "sr.", "staff", "principal", "lead", "architect",
    "manager", "director", "head of", "chief", "responsable",
)
EXCLUDED_LOCATIONS = (
    "morocco", "maroc", "algeria", "algérie", "egypt", "égypte",
    "uae", "united arab emirates", "saudi", "qatar",
)


def job_fit_guard(job: dict) -> tuple[bool, float]:
    """Apply entry-level, location, and recency rules before AI analysis."""
    title = (job.get("title") or "").casefold()
    location = (job.get("location") or "").casefold()
    experience = (job.get("experience") or "").casefold()

    if any(term in title for term in SENIORITY_EXCLUSIONS):
        return False, 0.0
    if any(country in location for country in EXCLUDED_LOCATIONS):
        return False, 0.0
    if re.search(r"(?:[3-9]|\d{2,})\+?\s*(?:years?|ans)", experience):
        if not any(term in title for term in ("junior", "graduate", "entry", "new grad")):
            return False, 0.0

    role_bonus = 4.0 if any(term in title for term in JUNIOR_ROLE_TERMS) else 0.0
    recency_bonus = 0.0
    raw_date = job.get("posted_at")
    if raw_date:
        try:
            if isinstance(raw_date, datetime):
                posted = raw_date.date()
            elif isinstance(raw_date, date):
                posted = raw_date
            else:
                posted = datetime.fromisoformat(str(raw_date).replace("Z", "+00:00")).date()
            age_days = max(0, (date.today() - posted).days)
            recency_bonus = max(0.0, 6.0 - min(age_days, 30) * 0.2)
        except (TypeError, ValueError):
            pass
    return True, role_bonus + recency_bonus


def term_in_text(term: str, text: str) -> bool:
    """Match a skill as a term, not as an accidental substring."""
    normalized = re.sub(r"[^a-z0-9+#.]+", " ", term.lower()).strip()
    if not normalized:
        return False
    pattern = r"(?<![a-z0-9+#])" + re.escape(normalized) + r"(?![a-z0-9+#])"
    return re.search(pattern, text.lower()) is not None


def extract_cv_skills_detailed(cv_text: str) -> dict:
    """Extract detailed skill categories from CV text."""
    text_lower = cv_text.lower()
    
    # Categorize skills found in CV
    skill_categories = {
        'languages': [],
        'frameworks': [],
        'databases': [],
        'tools': [],
        'cloud': [],
        'soft_skills': [],
        'roles': [],
        'domains': []
    }
    
    # Language keywords
    lang_keywords = ['python', 'java', 'javascript', 'typescript', 'c#', 'c++', 'php', 'go', 'rust', 'ruby', 'scala', 'kotlin', 'swift', 'r', 'matlab', 'sql']
    for kw in lang_keywords:
        if kw in text_lower:
            skill_categories['languages'].append(kw)
    
    # Framework keywords
    fw_keywords = ['react', 'angular', 'vue', 'django', 'flask', 'fastapi', 'spring', 'spring boot', 'node.js', 'express', 'nestjs', 'next.js', 'nuxt', 'laravel', 'symfony', '.net', 'asp.net', 'rails', 'gin', 'echo']
    for kw in fw_keywords:
        if kw in text_lower:
            skill_categories['frameworks'].append(kw)
    
    # Database keywords
    db_keywords = ['postgresql', 'mysql', 'mongodb', 'redis', 'elasticsearch', 'sql server', 'oracle', 'sqlite', 'dynamodb', 'cassandra', 'neo4j']
    for kw in db_keywords:
        if kw in text_lower:
            skill_categories['databases'].append(kw)
    
    # Tools/DevOps keywords
    tool_keywords = ['docker', 'kubernetes', 'git', 'jenkins', 'github actions', 'gitlab ci', 'terraform', 'ansible', 'aws', 'azure', 'gcp', 'linux', 'nginx', 'apache', 'webpack', 'vite', 'jest', 'junit', 'pytest', 'selenium', 'cypress']
    for kw in tool_keywords:
        if kw in text_lower:
            skill_categories['tools'].append(kw)
    
    # Cloud keywords
    cloud_keywords = ['aws', 'azure', 'gcp', 'google cloud', 'ec2', 's3', 'lambda', 'rds', 'cloudformation', 'cloudrun', 'functions']
    for kw in cloud_keywords:
        if kw in text_lower:
            skill_categories['cloud'].append(kw)
    
    # Role keywords
    role_keywords = ['developer', 'engineer', 'architect', 'lead', 'manager', 'devops', 'data scientist', 'data analyst', 'ml engineer', 'ai engineer', 'fullstack', 'frontend', 'backend', 'mobile', 'qa', 'test', 'security', 'sysadmin', 'sre']
    for kw in role_keywords:
        if kw in text_lower:
            skill_categories['roles'].append(kw)
    
    # Domain keywords
    domain_keywords = ['fintech', 'banking', 'insurance', 'ecommerce', 'healthcare', 'edtech', 'saas', 'crm', 'erp', 'logistics', 'retail', 'telecom', 'automotive', 'gaming', 'blockchain', 'crypto', 'legaltech', 'hrtech']
    for kw in domain_keywords:
        if kw in text_lower:
            skill_categories['domains'].append(kw)
    
    return skill_categories


def calculate_job_match_score(job: dict, cv_skills: dict, cv_keywords: list) -> float:
    """Calculate a relevance score for a job based on CV skills."""
    score = 0.0
    job_text = f"{job.get('title', '')} {job.get('description', '')} {job.get('location', '')} {job.get('contract', '')}".lower()
    
    # Weight configuration
    weights = {
        'languages': 3.0,
        'frameworks': 2.5,
        'databases': 2.0,
        'tools': 1.5,
        'cloud': 2.0,
        'roles': 3.0,
        'domains': 1.5,
        'keywords': 1.0
    }
    
    # Match categorized skills
    for category, skills in cv_skills.items():
        weight = weights.get(category, 1.0)
        for skill in skills:
            if term_in_text(skill, job_text):
                score += weight
    
    # Match original keywords
    for kw in cv_keywords:
        if term_in_text(kw, job_text):
            score += weights['keywords']
    
    # Bonus for title matches (more important)
    title_lower = job.get('title', '').lower()
    for category, skills in cv_skills.items():
        for skill in skills:
            if term_in_text(skill, title_lower):
                score += weights.get(category, 1.0) * 1.5
    
    for kw in cv_keywords:
        if term_in_text(kw, title_lower):
            score += weights['keywords'] * 1.5
    
    return score


def get_jobs_for_cv_matching(db: DBManager, cv_keywords: list, cv_skills: dict,
                             limit: int = 100, scrape_run_id: int | None = None) -> list:
    """Get jobs ranked by keyword match score."""
    # Build keyword conditions for initial filter (broad)
    all_keywords = cv_keywords[:15]
    for skills in cv_skills.values():
        all_keywords.extend(skills)
    
    # Deduplicate
    unique_keywords = [
        keyword for keyword in dict.fromkeys(all_keywords)
        if len(re.sub(r"[^a-z0-9]+", "", keyword.lower())) > 1
    ][:20]
    
    keyword_conditions = " OR ".join([
        f"(j.title ILIKE '%{kw}%' OR j.description ILIKE '%{kw}%')" for kw in unique_keywords
    ])
    
    run_join = ""
    run_filter = ""
    params = {"limit": limit}
    if scrape_run_id is not None:
        run_join = "JOIN scrape_run_jobs srj ON srj.job_id = j.id"
        run_filter = "AND srj.run_id = :scrape_run_id"
        params["scrape_run_id"] = scrape_run_id

    sql = f"""
         SELECT j.id, j.title, COALESCE(j.description, '') AS description,
             j.location, j.contract,
               j.experience, j.source, j.source_url, j.posted_at, j.scraped_at,
               c.name AS company_name, s.name AS sector_name
        FROM jobs j
        {run_join}
        LEFT JOIN companies c ON c.id = j.company_id
        LEFT JOIN sectors s ON s.id = j.sector_id
        WHERE j.is_active = TRUE
          {run_filter}
                    AND ({keyword_conditions.replace('j.description', "COALESCE(j.description, '')")})
        ORDER BY j.scraped_at DESC
        LIMIT :limit
    """
    df = db.fetch(sql, params)
    logger.info(f"Found {len(df)} candidate jobs from keyword filter")
    
    # Score and rank jobs
    jobs = df.to_dict(orient="records")
    scored_jobs = []
    technical_terms = [
        term for category in ('languages', 'frameworks', 'databases', 'tools', 'cloud')
        for term in cv_skills.get(category, [])
        if len(term) > 1
    ]
    role_terms = cv_skills.get('roles', []) + [
        'informaticien', 'informatique', 'software', 'developpeur',
        'programmeur', 'web', 'data', 'system', 'système',
    ]
    seen_jobs = set()
    for job in jobs:
        allowed, fit_bonus = job_fit_guard(job)
        if not allowed:
            continue
        score = calculate_job_match_score(job, cv_skills, cv_keywords)
        title = job.get('title', '') or ''
        text = f"{title} {job.get('description', '') or ''}"
        title_is_relevant = any(term_in_text(term, title) for term in technical_terms + role_terms)
        technical_hits = sum(term_in_text(term, text) for term in technical_terms)
        if not title_is_relevant and technical_hits < 2:
            continue
        if score < 8:
            continue
        identity = (
            job.get("source_url")
            or f"{job.get('title', '').casefold()}|{job.get('company_name', '').casefold()}"
        )
        if identity in seen_jobs:
            continue
        seen_jobs.add(identity)
        job['pre_match_score'] = score + fit_bonus
        scored_jobs.append(job)
    
    # Sort by score descending
    scored_jobs.sort(key=lambda x: x['pre_match_score'], reverse=True)
    
    # Return top jobs (more candidates for AI to analyze)
    return scored_jobs[:min(limit, 80)]


def analyze_job_match(cv_text: str, cv_keywords: list, cv_skills: dict, job: dict) -> dict | None:
    """Use AI to analyze how well a job matches the CV."""
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        logger.warning("OPENROUTER_API_KEY not configured, skipping AI match analysis")
        return None

    job_desc = (job.get('description', '') or '').strip()
    if not job_desc:
        job_desc = "No job description was provided; evaluate the role from its title and metadata."

    job_title = job.get('title', '') or ''
    job_company = job.get('company_name', '') or job.get('company', '') or ''
    job_location = job.get('location', '') or ''
    job_contract = job.get('contract', '') or ''
    job_experience = job.get('experience', '') or ''
    job_sector = job.get('sector_name', '') or ''

    # Format CV skills for prompt
    skills_summary = []
    for cat, skills in cv_skills.items():
        if skills:
            skills_summary.append(f"{cat}: {', '.join(skills[:10])}")
    skills_text = "; ".join(skills_summary)

    prompt = f"""
Tu es un expert en recrutement. Analyse la correspondance entre ce CV et cette offre d'emploi.

PROFIL DU CANDIDAT:
Compétences techniques: {skills_text}
Mots-clés principaux: {', '.join(cv_keywords)}
Extrait du CV:
{cv_text[:2500]}

OFFRE D'EMPLOI:
Titre: {job_title}
Entreprise: {job_company}
Localisation: {job_location}
Type de contrat: {job_contract}
Expérience requise: {job_experience}
Secteur: {job_sector}
Description: {job_desc[:2000]}

Réponds UNIQUEMENT en JSON valide avec ces champs:
{{
  "match_score": 0-100,
  "summary": "Résumé de l'offre en 2-3 phrases (français)",
  "why_good_match": "Pourquoi cette offre correspond au profil (français, max 3 phrases)",
  "missing_skills": ["compétence1", "compétence2"],
  "recommendation": "postuler|peut-etre|ignorer"
}}

Critères de notation:
- 80-100: Excellent match, compétences clés alignées, expérience pertinente
- 60-79: Bon match, la plupart des compétences requises présentes
- 40-59: Match partiel, quelques compétences manquantes importantes
- 20-39: Faible match, compétences principales non alignées
- 0-19: Non pertinent
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
        
        if "choices" not in data or not data["choices"]:
            logger.warning(f"OpenRouter response missing choices: {data}")
            return None
            
        content = data["choices"][0].get("message", {}).get("content", "")
        if not content:
            logger.warning(f"OpenRouter returned empty content: {data}")
            return None
            
        content = content.strip()

        # Extract JSON from response
        json_match = re.search(r'\{.*\}', content, re.DOTALL)
        if json_match:
            result = json.loads(json_match.group())
            result['tokens_used'] = data.get("usage", {}).get("total_tokens", 0)
            return result

    except Exception as e:
        logger.error(f"Error analyzing job match: {e}")

    return None


def save_cv_match(db: DBManager, job_id: int, match_result: dict,
                  cv_keywords: list, cv_skills: dict,
                  scrape_run_id: int | None = None):
    """Save CV-job match analysis to database."""
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS cv_job_matches (
            id              SERIAL PRIMARY KEY,
            job_id          INT REFERENCES jobs(id) ON DELETE CASCADE,
            cv_keywords     TEXT[],
            cv_skills       JSONB,
            match_score     INT,
            summary         TEXT,
            why_good_match  TEXT,
            missing_skills  TEXT[],
            recommendation  VARCHAR(20),
            tokens_used     INT,
            scrape_run_id   INT REFERENCES scrape_runs(id),
            created_at      TIMESTAMP DEFAULT NOW(),
            UNIQUE(job_id)
        )
        """
    )
    # Add cv_skills column if it doesn't exist (migration)
    db.execute("""
        ALTER TABLE cv_job_matches 
        ADD COLUMN IF NOT EXISTS cv_skills JSONB
    """)
    db.execute("""
        ALTER TABLE cv_job_matches
        ADD COLUMN IF NOT EXISTS scrape_run_id INT REFERENCES scrape_runs(id)
    """)
    db.execute(
        """
        INSERT INTO cv_job_matches (job_id, cv_keywords, cv_skills, match_score, summary, why_good_match, missing_skills, recommendation, tokens_used, scrape_run_id)
        VALUES (:job_id, :cv_keywords, :cv_skills, :match_score, :summary, :why_good_match, :missing_skills, :recommendation, :tokens_used, :scrape_run_id)
        ON CONFLICT (job_id) DO UPDATE SET
            cv_keywords = EXCLUDED.cv_keywords,
            cv_skills = EXCLUDED.cv_skills,
            match_score = EXCLUDED.match_score,
            summary = EXCLUDED.summary,
            why_good_match = EXCLUDED.why_good_match,
            missing_skills = EXCLUDED.missing_skills,
            recommendation = EXCLUDED.recommendation,
            tokens_used = EXCLUDED.tokens_used,
            scrape_run_id = EXCLUDED.scrape_run_id,
            created_at = NOW()
        """,
        {
            "job_id": job_id,
            "cv_keywords": cv_keywords,
            "cv_skills": json.dumps(cv_skills),
            "match_score": match_result.get("match_score", 0),
            "summary": match_result.get("summary", ""),
            "why_good_match": match_result.get("why_good_match", ""),
            "missing_skills": match_result.get("missing_skills", []),
            "recommendation": match_result.get("recommendation", "peut-etre"),
            "tokens_used": match_result.get("tokens_used", 0),
            "scrape_run_id": scrape_run_id,
        }
    )


def run_cv_job_matching(cv_path: str, max_jobs: int = 50, ai_analysis_limit: int = 30,
                        scrape_run_id: int | None = None) -> list:
    """
    Main pipeline: extract CV skills, find matching jobs, analyze with AI.
    Returns list of matched jobs with AI analysis, sorted by match score.
    """
    logger.info(f"=== CV Job Matching started for {cv_path} ===")

    # 1. Extract CV text, keywords, and detailed skills
    cv_text = extract_cv_text(cv_path)
    cv_keywords = keywords_from_cv(cv_text)
    cv_skills = extract_cv_skills_detailed(cv_text)
    logger.info(f"CV keywords: {cv_keywords}")
    logger.info(f"CV skills categories: {{k: len(v) for k, v in cv_skills.items()}}")

    # 2. Get and pre-rank matching jobs from DB
    db = DBManager()
    selected_run_id = scrape_run_id or db.get_latest_scrape_run_id()
    if selected_run_id:
        logger.info(f"Using scrape run {selected_run_id} for CV matching")
    else:
        logger.info("No scrape run history found; using all active jobs")
    jobs = get_jobs_for_cv_matching(
        db, cv_keywords, cv_skills, limit=100, scrape_run_id=selected_run_id
    )
    logger.info(f"Pre-ranked {len(jobs)} candidate jobs")

    # 3. Analyze top jobs with AI (limit AI calls to save costs)
    jobs_to_analyze = jobs[:ai_analysis_limit]
    matched_jobs = []
    
    for i, job in enumerate(jobs_to_analyze):
        logger.info(f"Analyzing match {i+1}/{len(jobs_to_analyze)}: {job.get('title', '')[:50]} (pre-score: {job.get('pre_match_score', 0):.1f})")
        match_result = analyze_job_match(cv_text, cv_keywords, cv_skills, job)
        if match_result:
            job['match_analysis'] = match_result
            job['cv_keywords'] = cv_keywords
            job['cv_skills'] = cv_skills
            # Save to DB
            save_cv_match(
                db, job['id'], match_result, cv_keywords, cv_skills, selected_run_id
            )
            matched_jobs.append(job)

    # 4. Sort final results by AI match score
    matched_jobs.sort(key=lambda x: x.get('match_analysis', {}).get('match_score', 0), reverse=True)

    logger.info(f"=== CV Job Matching complete: {len(matched_jobs)} jobs analyzed ===")
    return matched_jobs


def export_cv_matches():
    """Export CV-matched jobs to CSV for dashboard."""
    db = DBManager()
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
            'id', 'title', 'company_name', 'location', 'contract', 'experience', 'sector_name',
            'source', 'source_url', 'posted_at', 'scraped_at',
            'match_score', 'summary', 'why_good_match', 'missing_skills',
            'recommendation', 'cv_keywords', 'cv_skills', 'match_date'
        ]).to_csv(f"{export_dir}/cv_matches.csv", index=False, encoding='utf-8-sig')
        return pd.DataFrame()

    df = db.fetch("""
        SELECT j.id, j.title, j.location, j.contract, j.experience,
               s.name AS sector_name,
               j.source, j.source_url, j.posted_at, j.scraped_at,
               c.name AS company_name,
               m.match_score, m.summary, m.why_good_match, m.missing_skills,
               m.recommendation, m.cv_keywords, m.cv_skills, m.created_at AS match_date
        FROM cv_job_matches m
        JOIN jobs j ON j.id = m.job_id
        LEFT JOIN companies c ON c.id = j.company_id
        LEFT JOIN sectors s ON s.id = j.sector_id
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