# main.py
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

import schedule, time, logging, urllib3
from cv_matching import extract_cv_text, keywords_from_cv
from cv_job_matcher import run_cv_job_matching, export_cv_matches
from scrapers.keejob import KeeJobScraper
from scrapers.linkedin        import LinkedInScraper
from scrapers.emploitunisie      import EmploiTunisieScraper
from scrapers.rekrute         import ReKruteScraper
from analysis.skills_analysis import run_skills_analysis
from analysis.salary_analysis import run_salary_analysis
from analysis.trends          import run_trends_analysis
from ai.summarizer            import summarize_market
from data.export_data         import export_all
from dotenv import load_dotenv

load_dotenv()
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(name)s] %(levelname)s: %(message)s',
    handlers=[logging.StreamHandler(), logging.FileHandler('scrape.log')]
)

def full_pipeline(cv_path=None, skip_scraping=False, run_cv_matching=False):
    logging.info('=== Pipeline started ===')

    cv_keywords = None
    if cv_path:
        cv_text = extract_cv_text(cv_path)
        cv_keywords = keywords_from_cv(cv_text)
        logging.info('CV search terms: %s', ', '.join(cv_keywords))

    if skip_scraping:
        logging.info('Scraping skipped; using jobs already stored in the database.')
    else:
        for scraper in [KeeJobScraper(), EmploiTunisieScraper(),
                        ReKruteScraper(), LinkedInScraper()]:
            try:
                if isinstance(scraper, LinkedInScraper):
                    n = scraper.run(keywords=cv_keywords)
                else:
                    n = scraper.run()
                logging.info(f'{scraper.source}: {n} new jobs inserted')
            except Exception as e:
                logging.error(f'{scraper.source} failed: {e}')

    skills_df = run_skills_analysis()
    run_salary_analysis()
    run_trends_analysis()
    logging.info(f'Analysis complete: {len(skills_df)} skills tracked')

    summary = summarize_market()
    logging.info(f'AI summary generated ({summary["tokens_used"]} tokens)')

    # Run CV-based job matching if CV provided
    if cv_path and run_cv_matching:
        logging.info('Running CV-based job matching...')
        try:
            matched = run_cv_job_matching(cv_path, max_jobs=50)
            logging.info(f'CV matching complete: {len(matched)} jobs analyzed')
        except Exception as e:
            logging.error(f'CV job matching failed: {e}')

    export_all()
    export_cv_matches()
    logging.info('=== Pipeline complete ===')

if __name__ == '__main__':
    if '--once' in sys.argv:
        cv_path = None
        if '--cv' in sys.argv:
            cv_index = sys.argv.index('--cv') + 1
            if cv_index >= len(sys.argv):
                raise SystemExit('Usage: python main.py --once --cv path\\to\\cv.pdf [--skip-scraping] [--match-cv]')
            cv_path = sys.argv[cv_index]
        full_pipeline(
            cv_path,
            skip_scraping='--skip-scraping' in sys.argv,
            run_cv_matching='--match-cv' in sys.argv
        )
    else:
        schedule.every().day.at('07:00').do(full_pipeline)
        logging.info('Scheduler started — daily run at 07:00')
        while True:
            schedule.run_pending()
            time.sleep(60)