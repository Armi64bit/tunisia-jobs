# data/export_data.py
# Exports cleaned data as Power BI-ready CSVs
# Run: python data/export_data.py

import sys, os, logging
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from data.clean_data import get_clean_jobs
from database.db_manager import DBManager
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s: %(message)s')

EXPORT_DIR = os.getenv('EXPORT_DIR', 'exports')
os.makedirs(EXPORT_DIR, exist_ok=True)

def export_all():
    db   = DBManager()
    jobs = get_clean_jobs()

    # 1. jobs_clean.csv — main table for Power BI
    cols = ['id', 'title_clean', 'company', 'sector', 'location_clean',
            'contract_clean', 'source_label', 'scrape_date',
            'scrape_month', 'has_description', 'posted_at']
    jobs[cols].to_csv(f'{EXPORT_DIR}/jobs_clean.csv',
                      index=False, encoding='utf-8-sig')
    logging.info(f'jobs_clean.csv — {len(jobs)} rows')

    # 2. skills.csv
    skills = db.fetch("""
        SELECT skill, category, job_count, pct_jobs
        FROM analysis_skills ORDER BY job_count DESC
    """)
    skills.to_csv(f'{EXPORT_DIR}/skills.csv', index=False, encoding='utf-8-sig')
    logging.info(f'skills.csv — {len(skills)} skills')

    # 3. monthly_by_source.csv
    monthly = (jobs.groupby(['scrape_month', 'source_label'])
                   .size().reset_index(name='job_count'))
    monthly.to_csv(f'{EXPORT_DIR}/monthly_by_source.csv',
                   index=False, encoding='utf-8-sig')
    logging.info('monthly_by_source.csv')

    # 4. by_location.csv
    by_loc = (jobs.groupby('location_clean')
                  .size().reset_index(name='job_count')
                  .sort_values('job_count', ascending=False))
    by_loc.to_csv(f'{EXPORT_DIR}/by_location.csv',
                  index=False, encoding='utf-8-sig')
    logging.info('by_location.csv')

    # 5. by_contract.csv
    by_contract = (jobs.groupby('contract_clean')
                       .size().reset_index(name='job_count')
                       .sort_values('job_count', ascending=False))
    by_contract.to_csv(f'{EXPORT_DIR}/by_contract.csv',
                       index=False, encoding='utf-8-sig')
    logging.info('by_contract.csv')

    # 6. top_companies.csv
    top_co = (jobs[jobs['company'] != '']
                  .groupby('company').size()
                  .reset_index(name='job_count')
                  .sort_values('job_count', ascending=False)
                  .head(50))
    top_co.to_csv(f'{EXPORT_DIR}/top_companies.csv',
                  index=False, encoding='utf-8-sig')
    logging.info('top_companies.csv')

    # 7. ai_summary.csv
    try:
        ai = db.fetch("""
            SELECT generated_at, model, summary
            FROM ai_summaries ORDER BY generated_at DESC LIMIT 1
        """)
        ai.to_csv(f'{EXPORT_DIR}/ai_summary.csv',
                  index=False, encoding='utf-8-sig')
        logging.info('ai_summary.csv')
    except Exception as e:
        logging.warning(f'ai_summary skipped: {e}')

    # 8. cv_matches.csv
    try:
        cv_matches = db.fetch("""
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
        cv_matches.to_csv(f'{EXPORT_DIR}/cv_matches.csv',
                          index=False, encoding='utf-8-sig')
        logging.info(f'cv_matches.csv — {len(cv_matches)} rows')
    except Exception as e:
        logging.warning(f'cv_matches skipped: {e}')

    # Summary
    logging.info(f'\n=== {EXPORT_DIR}/ ===')
    for f in sorted(os.listdir(EXPORT_DIR)):
        if f.endswith('.csv'):
            kb = os.path.getsize(f'{EXPORT_DIR}/{f}') / 1024
            logging.info(f'  {f:<30} {kb:.1f} KB')

if __name__ == '__main__':
    export_all()