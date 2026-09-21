# scrapers/keejob.py 
import requests, re
from bs4 import BeautifulSoup
from tqdm import tqdm
from scrapers.base_scraper import BaseScraper

BASE = 'https://www.keejob.com'

class KeeJobScraper(BaseScraper):
    def __init__(self):
        super().__init__('keejob')

    def fetch_description(self, url: str) -> str:
        try:
            resp = requests.get(url, headers=self.get_headers(),
                                timeout=12, verify=False)
            resp.encoding = resp.apparent_encoding
            soup = BeautifulSoup(resp.text, 'lxml')
            # Confirmed selector from debug: div with Tailwind text-gray-700 class
            for sel in [
                'div.mt-4.text-gray-700',
                'div[class*="text-gray-700"]',
                'div[class*="prose"]',
                'div[class*="description"]',
                'article div[class*="mt-4"]',
            ]:
                el = soup.select_one(sel)
                if el:
                    text = el.get_text(separator=' ', strip=True)
                    if len(text) > 80:
                        return text[:3000]
        except Exception:
            pass
        return ''

    def run(self, max_pages: int = 20):
        all_jobs = []
        for page in tqdm(range(1, max_pages + 1), desc='KeeJob pages', unit='page'):
            url = f'{BASE}/offres-emploi/?page={page}'
            try:
                resp = requests.get(url, headers=self.get_headers(),
                                    timeout=15, verify=False)
                resp.encoding = resp.apparent_encoding
                if resp.status_code in (404, 410):
                    break
                resp.raise_for_status()
            except Exception as e:
                self.logger.warning(f'keejob page {page}: {e}')
                break

            soup  = BeautifulSoup(resp.text, 'lxml')
            cards = soup.select('article')
            if not cards:
                self.logger.info(f'keejob: no cards on page {page}, stopping.')
                break

            for card in cards:
                try:
                    title_el = card.select_one('h2 a, h3 a')
                    if not title_el or not title_el.get_text(strip=True):
                        continue
                    title = title_el.get_text(strip=True)
                    href  = title_el.get('href', '')
                    link  = href if href.startswith('http') else BASE + href

                    company = ''
                    comp_el = card.select_one('p a[href*="companies"]')
                    if comp_el:
                        company = comp_el.get_text(strip=True)

                    location = ''
                    for span in card.select('span, p'):
                        txt = span.get_text(strip=True)
                        if any(city in txt for city in [
                            'Tunis','Sfax','Sousse','Monastir','Ariana',
                            'Bizerte','Nabeul','Gabès','Gafsa','Kairouan',
                            'Médenine','Sidi Bouzid','Jendouba','Siliana',
                            'Zaghouan','Ben Arous','Manouba','Mahdia']):
                            location = txt[:80]
                            break

                    salary_raw = ''
                    m = re.search(r'\d[\d\s]*(?:[-–]\s*\d[\d\s]*)?\s*TND',
                                  card.get_text(' ', strip=True))
                    if m:
                        salary_raw = m.group(0).strip()

                    contract = ''
                    for badge in card.select('span, p'):
                        txt = badge.get_text(strip=True)
                        if txt in ('CDI','CDD','SIVP','Stage','Freelance','Intérim'):
                            contract = txt
                            break

                    self.random_delay(0.3, 0.8)
                    description = self.fetch_description(link)

                    all_jobs.append({
                        'title': title, 'company': company,
                        'location': location, 'salary_raw': salary_raw,
                        'contract': contract, 'description': description,
                        'source_url': link, 'source': 'keejob',
                    })
                except Exception:
                    continue
            self.random_delay(2, 3)

        self.logger.info(f'keejob: {len(all_jobs)} jobs collected.')
        return self.save_jobs(all_jobs)