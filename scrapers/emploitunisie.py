# scrapers/emploitunisie.py 
import time, requests
from bs4 import BeautifulSoup
from tqdm import tqdm
from scrapers.base_scraper import BaseScraper, make_driver

BASE = 'https://www.emploitunisie.com'

class EmploiTunisieScraper(BaseScraper):
    def __init__(self):
        super().__init__('emploitunisie')

    def fetch_description(self, url: str) -> str:
        try:
            resp = requests.get(url, headers=self.get_headers(),
                                timeout=12, verify=False)
            resp.encoding = resp.apparent_encoding
            soup = BeautifulSoup(resp.text, 'lxml')
            for sel in ['.field-name-body', '.card-job-description',
                        '.job-description', '.description',
                        '.field-items', '.node-body', '.content']:
                el = soup.select_one(sel)
                if el and len(el.get_text(strip=True)) > 80:
                    return el.get_text(separator=' ', strip=True)[:3000]
        except Exception:
            pass
        return ''

    def _parse_card(self, card) -> dict:
        try:
            title_el = card.select_one('h3, h2')
            if not title_el or not title_el.get_text(strip=True):
                return None
            raw_title = title_el.get_text(strip=True)
            link_el   = card.select_one('a[href]')
            href      = link_el.get('href', '') if link_el else ''
            link      = href if href.startswith('http') else BASE + href

            if ' - ' in raw_title:
                parts    = raw_title.rsplit(' - ', 1)
                title    = parts[0].strip()
                location = parts[1].strip()
            else:
                title    = raw_title
                location = ''

            company = ''
            comp_el = card.select_one('a.card-job-company, .company-name')
            if comp_el:
                company = comp_el.get_text(strip=True)

            # Always fetch full description from detail page
            description = ''
            if link:
                self.random_delay(0.5, 1.2)
                description = self.fetch_description(link)
            # Fallback to card snippet
            if not description:
                desc_el     = card.select_one('.card-job-description')
                description = desc_el.get_text(separator=' ', strip=True) if desc_el else ''

            return {'title': title, 'company': company, 'location': location,
                    'source_url': link, 'description': description, 'source': 'emploitunisie'}
        except Exception:
            return None

    def run(self, max_pages: int = 15):
        all_jobs = []
        driver   = None
        try:
            driver = make_driver()
            for page in tqdm(range(0, max_pages), desc='EmploiTunisie pages', unit='page'):
                if driver is None or not self.is_driver_alive(driver):
                    self.logger.warning('Chrome session lost, restarting...')
                    try: driver.quit()
                    except Exception: pass
                    time.sleep(3)
                    driver = make_driver()

                url = f'{BASE}/recherche-jobs-tunisie/' + (f'?page={page}' if page > 0 else '')
                try:
                    driver.get(url)
                except Exception:
                    try: driver.quit()
                    except Exception: pass
                    driver = make_driver()
                    driver.get(url)

                time.sleep(8)
                driver.execute_script('window.scrollTo(0, document.body.scrollHeight)')
                time.sleep(2)

                soup  = BeautifulSoup(driver.page_source, 'lxml')
                cards = soup.select('div.card.card-job')
                if not cards:
                    self.logger.info(f'emploitunisie: no cards on page {page}, stopping.')
                    break

                self.logger.info(f'emploitunisie: {len(cards)} cards on page {page}')
                for card in cards:
                    job = self._parse_card(card)
                    if job:
                        all_jobs.append(job)
                self.random_delay(2, 4)
        finally:
            try:
                if driver: driver.quit()
            except Exception:
                pass

        self.logger.info(f'emploitunisie: {len(all_jobs)} jobs collected.')
        return self.save_jobs(all_jobs)