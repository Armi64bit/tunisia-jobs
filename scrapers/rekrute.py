# scrapers/rekrute.py
import requests, re
from bs4 import BeautifulSoup
from tqdm import tqdm
from scrapers.base_scraper import BaseScraper

BASE = 'https://www.rekrute.com'

# Tunisia location keywords to filter jobs
TUNISIA_KEYWORDS = [
    'tunisie','tunis','sfax','sousse','monastir','ariana','bizerte',
    'nabeul','gabès','gafsa','kairouan','médenine','sidi bouzid',
    'jendouba','siliana','zaghouan','ben arous','manouba','mahdia',
    'tozeur','kebili','tataouine','beja'
]

class ReKruteScraper(BaseScraper):
    def __init__(self):
        super().__init__('rekrute')

    def run(self, max_pages: int = 10):
        all_jobs = []
        for page in tqdm(range(1, max_pages + 1), desc='ReKrute pages', unit='page'):
            # Correct working URL (gNetwork=2 = Tunisia)
            url = f'{BASE}/offres.html?gNetwork=2&p={page}'
            try:
                resp = requests.get(url, headers=self.get_headers(),
                                    timeout=15, verify=False)
                resp.encoding = resp.apparent_encoding
                if resp.status_code in (404, 403):
                    break
                resp.raise_for_status()
            except Exception as e:
                self.logger.warning(f'rekrute page {page}: {e}')
                break

            soup  = BeautifulSoup(resp.text, 'lxml')
            # Confirmed selector: li.post-id
            cards = soup.select('li.post-id')
            if not cards:
                self.logger.info(f'rekrute: no cards on page {page}, stopping.')
                break

            for card in cards:
                try:
                    # Title inside div.col-sm-10 > h2/h3 > a
                    title_el = card.select_one(
                        'div.col-sm-10 h2 a, div.col-sm-10 h3 a, h2 a, h3 a')
                    if not title_el or not title_el.get_text(strip=True):
                        continue

                    raw_title = title_el.get_text(strip=True)
                    href      = title_el.get('href', '')
                    link      = href if href.startswith('http') else BASE + '/' + href.lstrip('/')

                    # Title format: "Job Title | City (Country)"
                    # Extract clean title and location
                    if ' | ' in raw_title:
                        parts    = raw_title.split(' | ')
                        title    = parts[0].strip()
                        location = parts[1].strip() if len(parts) > 1 else ''
                    else:
                        title    = raw_title
                        location = ''

                    # Filter: only keep Tunisia jobs
                    loc_lower = location.lower()
                    if location and not any(k in loc_lower for k in TUNISIA_KEYWORDS):
                        continue  # skip non-Tunisia jobs

                    # Company: inside .section or em tag
                    company = ''
                    for sel in ['div.col-sm-10 .section em a',
                                'div.col-sm-10 em a',
                                '.recruiter a', 'em a']:
                        el = card.select_one(sel)
                        if el:
                            company = el.get_text(strip=True)
                            break

                    # Salary
                    salary_raw = ''
                    full_text  = card.get_text(' ', strip=True)
                    sal_match  = re.search(
                        r'\d[\d\s]*(?:[-–]\s*\d[\d\s]*)?\s*(?:TND|MAD|DH|€)', full_text)
                    if sal_match:
                        salary_raw = sal_match.group(0).strip()

                    all_jobs.append({
                        'title': title, 'company': company,
                        'location': location, 'salary_raw': salary_raw,
                        'source_url': link, 'source': 'rekrute',
                    })
                except Exception:
                    continue
            self.random_delay(2, 4)

        self.logger.info(f'rekrute: {len(all_jobs)} jobs collected.')
        return self.save_jobs(all_jobs)