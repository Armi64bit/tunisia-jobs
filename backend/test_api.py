import sys
sys.path.insert(0, '..')

from database.db_manager import DBManager
import pandas as pd
from dotenv import load_dotenv
load_dotenv()

def get_cv_matches_from_db(limit: int = 50):
    try:
        db = DBManager()
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
            LIMIT :limit
        """, {"limit": limit})
        
        matches = []
        for _, row in df.iterrows():
            missing_skills = row.get("missing_skills") or []
            cv_keywords = row.get("cv_keywords") or []
            cv_skills = row.get("cv_skills")
            if isinstance(cv_skills, str):
                try:
                    import json
                    cv_skills = json.loads(cv_skills)
                except:
                    cv_skills = {}
            elif cv_skills is None:
                cv_skills = {}
            
            matches.append({
                "id": int(row.get("id", 0)),
                "title": str(row.get("title", "")),
                "company": str(row.get("company_name", "")),
                "location": str(row.get("location", "")),
                "contract": str(row.get("contract", "")),
                "experience": str(row.get("experience", "")),
                "sector": str(row.get("sector_name", "")),
                "source": str(row.get("source", "")),
                "source_url": str(row.get("source_url", "")),
                "posted_at": str(row.get("posted_at", "")),
                "scraped_at": str(row.get("scraped_at", "")),
                "match_score": int(row.get("match_score", 0)) if pd.notna(row.get("match_score")) else None,
                "summary": str(row.get("summary", "")),
                "why_good_match": str(row.get("why_good_match", "")),
                "missing_skills": missing_skills,
                "recommendation": str(row.get("recommendation", "")),
                "cv_keywords": cv_keywords,
                "cv_skills": cv_skills,
                "match_date": str(row.get("match_date", "")),
            })
        return matches
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return []

result = get_cv_matches_from_db(5)
print(f"Success! Got {len(result)} matches")
for m in result:
    print(f"  {m['id']}: {m['title']} - missing_skills type: {type(m['missing_skills'])}, cv_keywords type: {type(m['cv_keywords'])}")