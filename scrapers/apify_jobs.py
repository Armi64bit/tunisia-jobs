import json
import os
from urllib.parse import quote

import requests

from scrapers.base_scraper import BaseScraper


class ApifyJobScraper(BaseScraper):
    """Optional Apify actor adapter; disabled unless explicitly configured."""

    def __init__(self):
        super().__init__("apify")
        self.token = os.getenv("APIFY_TOKEN", "").strip()
        self.actor_id = os.getenv("APIFY_ACTOR_ID", "").strip()
        self.input_json = os.getenv("APIFY_INPUT_JSON", "{}").strip()

    @property
    def configured(self) -> bool:
        return bool(self.token and self.actor_id)

    def _actor_input(self) -> dict:
        if not self.input_json:
            return {}
        value = json.loads(self.input_json)
        if not isinstance(value, dict):
            raise ValueError("APIFY_INPUT_JSON must contain a JSON object")
        return value

    @staticmethod
    def _first(item: dict, *keys, default=""):
        for key in keys:
            value = item.get(key)
            if value not in (None, ""):
                return value
        return default

    def _normalize_job(self, item: dict) -> dict | None:
        title = str(self._first(item, "title", "position", "jobTitle", "name")).strip()
        if not title:
            return None

        return {
            "title": title,
            "company": str(self._first(item, "company", "companyName", "employer", default="")).strip(),
            "location": str(self._first(item, "location", "jobLocation", default="")).strip(),
            "description": str(self._first(item, "description", "summary", "jobDescription", default="")).strip(),
            "contract": str(self._first(item, "contract", "employmentType", "type", default="")).strip(),
            "experience": str(self._first(item, "experience", "experienceLevel", default="")).strip(),
            "source_url": str(self._first(item, "url", "jobUrl", "applyUrl", "link", default="")).strip(),
            "posted_at": self._first(item, "postedAt", "publishedAt", "datePosted", "date"),
            "salary_raw": str(self._first(item, "salary", "salaryRaw", default="")).strip(),
            "source": "apify",
        }

    def run(self) -> int:
        if not self.configured:
            self.logger.info("apify: not configured; skipping optional actor.")
            return 0

        try:
            actor = quote(self.actor_id, safe="~")
            endpoint = f"https://api.apify.com/v2/actors/{actor}/run-sync-get-dataset-items"
            response = requests.post(
                endpoint,
                params={"format": "json", "clean": "true"},
                headers={"Authorization": f"Bearer {self.token}"},
                json=self._actor_input(),
                timeout=180,
            )
            if not response.ok:
                try:
                    error = response.json().get("error", {})
                    detail = error.get("message") or error.get("type") or response.text[:300]
                except ValueError:
                    detail = response.text[:300]
                raise RuntimeError(f"HTTP {response.status_code}: {detail}")
            payload = response.json()
            if not isinstance(payload, list):
                raise ValueError("Apify returned a non-list dataset payload")

            jobs = [
                job for item in payload
                if isinstance(item, dict)
                for job in [self._normalize_job(item)]
                if job is not None
            ]
            self.logger.info("apify: %s jobs normalized.", len(jobs))
            return self.save_jobs(jobs)
        except Exception as exc:
            self.logger.warning("apify: optional scraper unavailable: %s", exc)
            return 0
