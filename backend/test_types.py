import sys
sys.path.insert(0, '..')
from database.db_manager import DBManager
import pandas as pd
from dotenv import load_dotenv
load_dotenv()
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
    LIMIT 5
""")
for _, row in df.iterrows():
    print("missing_skills:", type(row.get('missing_skills')), row.get('missing_skills'))
    print("cv_keywords:", type(row.get('cv_keywords')), row.get('cv_keywords'))
    print("cv_skills:", type(row.get('cv_skills')), row.get('cv_skills'))
    break