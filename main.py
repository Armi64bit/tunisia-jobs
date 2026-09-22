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
from database.db_manager import DBManager

load_dotenv()
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(name)s] %(levelname)s: %(message)s',
    handlers=[logging.StreamHandler(), logging.FileHandler('scrape.log')]
)

def full_pipeline(cv_path=None, skip_scraping=False, run_cv_matching=False,
                  scrape_run_id=None):
    logging.info('=== Pipeline started ===')

    cv_keywords = None
    if cv_path:
        cv_text = extract_cv_text(cv_path)
        cv_keywords = keywords_from_cv(cv_text)
        logging.info('CV search terms: %s', ', '.join(cv_keywords))

    pipeline_run_id = None
    if skip_scraping:
        logging.info('Scraping skipped; using jobs already stored in the database.')
    else:
        run_db = DBManager()
        pipeline_run_id = run_db.start_scrape_run('pipeline')
        total_found = 0
        total_new = 0
        run_status = 'success'
        run_error = None
        try:
            for scraper in [KeeJobScraper(), EmploiTunisieScraper(),
                            ReKruteScraper(), LinkedInScraper()]:
                scraper.scrape_run_id = pipeline_run_id
                try:
                    if isinstance(scraper, LinkedInScraper):
                        n = scraper.run(keywords=cv_keywords)
                    else:
                        n = scraper.run()
                    total_found += scraper.last_jobs_found
                    total_new += n
                    logging.info(f'{scraper.source}: {n} new jobs inserted')
                except Exception as e:
                    run_status = 'partial'
                    run_error = str(e)
                    logging.error(f'{scraper.source} failed: {e}')
        finally:
            run_db.finish_scrape_run(
                pipeline_run_id, total_found, total_new, run_status, run_error
            )

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
            matched = run_cv_job_matching(
                cv_path, max_jobs=50,
                scrape_run_id=scrape_run_id or pipeline_run_id
            )
            logging.info(f'CV matching complete: {len(matched)} jobs analyzed')
        except Exception as e:
            logging.exception(f'CV job matching failed: {e}')

    logging.info('Exporting pipeline outputs...')
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
        try:
            scrape_run_id = None
            if '--scrape-run-id' in sys.argv:
                run_index = sys.argv.index('--scrape-run-id') + 1
                if run_index >= len(sys.argv):
                    raise SystemExit('--scrape-run-id requires a numeric run ID')
                scrape_run_id = int(sys.argv[run_index])
            full_pipeline(
                cv_path,
                skip_scraping='--skip-scraping' in sys.argv,
                run_cv_matching='--match-cv' in sys.argv,
                scrape_run_id=scrape_run_id,
            )
        except Exception:
            logging.exception('Pipeline failed')
            raise
    else:
        schedule.every().day.at('07:00').do(full_pipeline)
        logging.info('Scheduler started — daily run at 07:00')
        while True:
            schedule.run_pending()
            time.sleep(60)