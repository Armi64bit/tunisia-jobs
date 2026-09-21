# scrapers/base_scraper.py
import time, random, logging
from fake_useragent import UserAgent
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from database.db_manager import DBManager

ua = UserAgent()

def make_driver():
    opts = Options()
    opts.add_argument('--headless=new')
    opts.add_argument('--no-sandbox')
    opts.add_argument('--disable-dev-shm-usage')
    opts.add_argument('--disable-blink-features=AutomationControlled')
    opts.add_argument('--disable-extensions')
    opts.add_argument('--disable-gpu')
    opts.add_argument('--window-size=1920,1080')
    opts.add_argument('--memory-pressure-off')
    opts.add_argument('--max_old_space_size=512')
    opts.add_experimental_option('excludeSwitches', ['enable-automation'])
    opts.add_experimental_option('useAutomationExtension', False)
    opts.add_argument(f'--user-agent={ua.random}')
    opts.add_argument('--lang=fr-FR')
    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()), options=opts)
    driver.set_page_load_timeout(30)
    driver.execute_cdp_cmd('Network.setUserAgentOverride', {"userAgent": ua.random})
    return driver

class BaseScraper:
    def __init__(self, source_name: str):
        self.source = source_name
        self.db     = DBManager()
        self.ua     = ua
        self.logger = logging.getLogger(source_name)

    def random_delay(self, min_s=1.5, max_s=4.0):
        time.sleep(random.uniform(min_s, max_s))

    def get_headers(self) -> dict:
        return {
            'User-Agent': self.ua.random,
            'Accept-Language': 'fr-TN,fr;q=0.9,en;q=0.8',
            'Accept': 'text/html,application/xhtml+xml',
        }

    def clean_text(self, text: str) -> str:
        if not text:
            return ''
        return text.replace('\x00', '').strip()

    def is_driver_alive(self, driver) -> bool:
        try:
            _ = driver.current_url
            return True
        except Exception:
            return False

    def save_jobs(self, jobs: list) -> int:
        inserted = 0
        for job in jobs:
            for field in ('title', 'company', 'location', 'description',
                          'contract', 'experience', 'salary_raw'):
                if field in job and job[field]:
                    job[field] = self.clean_text(job[field])
            try:
                if self.db.insert_job(job):
                    inserted += 1
            except UnicodeDecodeError as e:
                self.logger.warning(f'Encoding error on "{job.get("title","?")}": {e}')
            except Exception as e:
                self.logger.warning(f'Skip "{job.get("title","?")}": {e}')
        self.db.log_run(self.source, len(jobs), inserted)
        return inserted

    def run(self):
        raise NotImplementedError