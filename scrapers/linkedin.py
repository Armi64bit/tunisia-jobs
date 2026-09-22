# scrapers/linkedin.py
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from tqdm import tqdm
from scrapers.base_scraper import BaseScraper, make_driver
import time

BASE = 'https://www.linkedin.com/jobs/search'

KEYWORDS = [
    # Tech
    'developpeur', 'developer', 'software engineer', 'ingenieur logiciel',
    'data analyst', 'data scientist', 'data engineer', 'business intelligence',
    'devops', 'cloud engineer', 'fullstack', 'frontend', 'backend',
    'python', 'java', 'javascript', 'react', 'angular', 'php',
    'mobile developer', 'flutter', 'android', 'ios',
    'cybersecurity', 'network engineer', 'system administrator',
    'machine learning', 'artificial intelligence',
    # Business
    'chef de projet', 'project manager', 'product manager',
    'comptable', 'auditeur', 'finance', 'contrôleur de gestion',
    'commercial', 'responsable commercial', 'business developer',
    'marketing', 'community manager', 'digital marketing',
    'rh', 'ressources humaines', 'recrutement',
    'ingenieur', 'technicien', 'responsable qualite',
    # Sectors
    'banque', 'assurance', 'telecom', 'industrie', 'logistique',
]

class LinkedInScraper(BaseScraper):
    def __init__(self):
        super().__init__('linkedin')

    def scrape_keyword(self, driver, keyword: str) -> list:
        # f_TPR=r2592000 = last 30 days, f_JT=F = full time
        url = (f'{BASE}/?keywords={keyword.replace(" ", "%20")}'
               f'&location=Tunisia&f_TPR=r2592000&start=0')
        try:
            driver.get(url)
            time.sleep(3)
        except Exception:
            return []

        jobs     = []
        last_len = 0

        # Scroll up to 5 times to load more cards (25 per scroll)
        for scroll in range(5):
            driver.execute_script('window.scrollTo(0, document.body.scrollHeight)')
            time.sleep(2)

            # Click "Show more" button if present
            try:
                btn = driver.find_element(By.CSS_SELECTOR,
                    'button.infinite-scroller__show-more-button, '
                    'button[aria-label*="more"], button[data-tracking-control-name*="load"]')
                driver.execute_script('arguments[0].click()', btn)
                time.sleep(2)
            except Exception:
                pass

            cards = driver.find_elements(By.CSS_SELECTOR, '.job-search-card, .base-card')
            if len(cards) == last_len:
                break  # no new cards loaded
            last_len = len(cards)

        # Parse all loaded cards
        cards = driver.find_elements(By.CSS_SELECTOR, '.job-search-card, .base-card')
        for card in cards:
            try:
                title = card.find_element(By.CSS_SELECTOR,
                    '.base-search-card__title, h3').text.strip()
                company = card.find_element(By.CSS_SELECTOR,
                    '.base-search-card__subtitle, h4').text.strip()
                location = card.find_element(By.CSS_SELECTOR,
                    '.job-search-card__location, .base-search-card__metadata').text.strip()
                link = card.find_element(By.CSS_SELECTOR, 'a').get_attribute('href')

                # Get posted date if available
                try:
                    date_el = card.find_element(By.CSS_SELECTOR, 'time')
                    posted  = date_el.get_attribute('datetime')
                except Exception:
                    posted = None

                if title:
                    jobs.append({
                        'title':     title,
                        'company':   company,
                        'location':  location,
                        'source_url': link,
                        'posted_at': posted,
                        'source':    'linkedin',
                    })
            except Exception:
                continue
        return jobs

    def run(self, keywords=None):
        driver   = make_driver()
        all_jobs = []
        seen_urls = set()
        # Only use the broad catalogue when no CV profile was supplied.
        search_keywords = KEYWORDS if keywords is None else keywords
        if not search_keywords:
            raise ValueError('No LinkedIn search terms were extracted from the CV.')

        try:
            for kw in tqdm(search_keywords, desc='LinkedIn searches', unit='keyword'):
                if not self.is_driver_alive(driver):
                    self.logger.warning('LinkedIn: Chrome crashed, restarting...')
                    try: driver.quit()
                    except Exception: pass
                    time.sleep(3)
                    driver = make_driver()

                jobs = self.scrape_keyword(driver, kw)

                # Deduplicate by URL within this run
                for job in jobs:
                    url = job.get('source_url', '')
                    if url and url not in seen_urls:
                        seen_urls.add(url)
                        all_jobs.append(job)

                self.logger.info(f'linkedin [{kw}]: {len(jobs)} jobs')
                self.random_delay(3, 6)
        finally:
            try: driver.quit()
            except Exception: pass

        self.logger.info(f'linkedin total: {len(all_jobs)} unique jobs collected.')
        return self.save_jobs(all_jobs)