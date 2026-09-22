# database/db_manager.py
import os
import logging
import pandas as pd
from datetime import date, datetime
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError

load_dotenv()

logger = logging.getLogger("db_manager")


class DBManager:
    """
    Handles all database operations for the Tunisia Job Market platform.
    Connects to PostgreSQL via SQLAlchemy.
    """

    def __init__(self):
        db_url = os.getenv("DATABASE_URL") or (
            f"postgresql://{os.getenv('DB_USER', 'postgres')}"
            f":{os.getenv('DB_PASSWORD', '')}"
            f"@{os.getenv('DB_HOST', 'localhost')}"
            f":{os.getenv('DB_PORT', '5432')}"
            f"/{os.getenv('DB_NAME', 'tunisia_jobs')}"
        )
        self.engine = create_engine(
            db_url,
            pool_pre_ping=True,
            connect_args={"options": "-c lc_messages=C"},
        )
        self.Session = sessionmaker(bind=self.engine)
        self._ensure_scrape_run_tables()
        self._backfill_scrape_runs()
        self._repair_empty_scrape_runs()
        logger.info("DBManager connected to database.")

    # ── Generic helper ─────────────────────────────────────────────────────────

    def execute(self, sql: str, params: dict = None):
        """Execute a write query (INSERT / UPDATE / DELETE)."""
        with self.engine.begin() as conn:
            conn.execute(text(sql), params or {})

    def fetch(self, sql: str, params: dict = None) -> pd.DataFrame:
        """Execute a SELECT query and return a DataFrame."""
        with self.engine.connect() as conn:
            return pd.read_sql(text(sql), conn, params=params or {})

    def execute_returning(self, sql: str, params: dict = None) -> pd.DataFrame:
        """Execute a write query that returns rows, committing the transaction."""
        with self.engine.begin() as conn:
            result = conn.execute(text(sql), params or {})
            return pd.DataFrame(result.mappings().all())

    def _ensure_scrape_run_tables(self):
        self.execute("""
            CREATE TABLE IF NOT EXISTS scrape_runs (
                id SERIAL PRIMARY KEY,
                source VARCHAR(40) NOT NULL,
                started_at TIMESTAMP DEFAULT NOW(),
                completed_at TIMESTAMP,
                jobs_found INT DEFAULT 0,
                jobs_new INT DEFAULT 0,
                status VARCHAR(20) DEFAULT 'running',
                error_msg TEXT
            )
        """)

    def _backfill_scrape_runs(self):
        """Convert legacy per-source logs into selectable pipeline snapshots once."""
        if not self.fetch("SELECT id FROM scrape_runs LIMIT 1").empty:
            return

        logs = self.fetch("""
            SELECT run_at, jobs_found, jobs_new, status, error_msg
            FROM scrape_logs
            WHERE status = 'success'
            ORDER BY run_at
        """)
        if logs.empty:
            return

        groups = []
        for _, row in logs.iterrows():
            if not groups or (row["run_at"] - groups[-1][-1]["run_at"]).total_seconds() > 900:
                groups.append([])
            groups[-1].append(row)

        for group in groups:
            started_at = group[0]["run_at"]
            completed_at = group[-1]["run_at"]
            jobs_found = sum(int(row["jobs_found"] or 0) for row in group)
            jobs_new = sum(int(row["jobs_new"] or 0) for row in group)
            run = self.execute_returning("""
                INSERT INTO scrape_runs
                    (source, started_at, completed_at, jobs_found, jobs_new, status)
                VALUES
                    ('pipeline', :started_at, :completed_at, :jobs_found, :jobs_new, 'success')
                RETURNING id
            """, {
                "started_at": started_at,
                "completed_at": completed_at,
                "jobs_found": jobs_found,
                "jobs_new": jobs_new,
            })
            run_id = int(run.iloc[0]["id"])
            self.execute("""
                INSERT INTO scrape_run_jobs (run_id, job_id)
                SELECT :run_id, id
                FROM jobs
                WHERE scraped_at BETWEEN :started_at AND :completed_at
                ON CONFLICT DO NOTHING
            """, {
                "run_id": run_id,
                "started_at": started_at,
                "completed_at": completed_at,
            })

    def _repair_empty_scrape_runs(self):
        """Link legacy snapshots whose duplicate jobs predate their log entries."""
        empty_runs = self.fetch("""
            SELECT r.id, r.completed_at
            FROM scrape_runs r
            LEFT JOIN scrape_run_jobs rj ON rj.run_id = r.id
            WHERE r.status IN ('success', 'partial')
            GROUP BY r.id, r.completed_at
            HAVING COUNT(rj.job_id) = 0
        """)
        for _, row in empty_runs.iterrows():
            self.execute("""
                INSERT INTO scrape_run_jobs (run_id, job_id)
                SELECT :run_id, id
                FROM jobs
                WHERE scraped_at <= :completed_at
                ON CONFLICT DO NOTHING
            """, {
                "run_id": int(row["id"]),
                "completed_at": row["completed_at"],
            })
        self.execute("""
            CREATE TABLE IF NOT EXISTS scrape_run_jobs (
                run_id INT REFERENCES scrape_runs(id) ON DELETE CASCADE,
                job_id INT REFERENCES jobs(id) ON DELETE CASCADE,
                PRIMARY KEY (run_id, job_id)
            )
        """)

    # ── Company helpers ────────────────────────────────────────────────────────

    def get_or_create_company(self, name: str) -> int | None:
        """Return company id, creating it if it doesn't exist."""
        if not name or not name.strip():
            return None
        name = name.strip()
        row = self.fetch(
            "SELECT id FROM companies WHERE name = :name", {"name": name}
        )
        if not row.empty:
            return int(row.iloc[0]["id"])
        self.execute(
            "INSERT INTO companies (name) VALUES (:name) ON CONFLICT (name) DO NOTHING",
            {"name": name},
        )
        row = self.fetch(
            "SELECT id FROM companies WHERE name = :name", {"name": name}
        )
        return int(row.iloc[0]["id"]) if not row.empty else None

    # ── Sector helpers ─────────────────────────────────────────────────────────

    def get_or_create_sector(self, name: str) -> int | None:
        """Return sector id, creating it if it doesn't exist."""
        if not name or not name.strip():
            return None
        name = name.strip()
        row = self.fetch(
            "SELECT id FROM sectors WHERE name = :name", {"name": name}
        )
        if not row.empty:
            return int(row.iloc[0]["id"])
        self.execute(
            "INSERT INTO sectors (name) VALUES (:name) ON CONFLICT (name) DO NOTHING",
            {"name": name},
        )
        row = self.fetch(
            "SELECT id FROM sectors WHERE name = :name", {"name": name}
        )
        return int(row.iloc[0]["id"]) if not row.empty else None

    # ── Job insertion ──────────────────────────────────────────────────────────

    def insert_job(self, job: dict) -> int | None:
        """
        Insert a single job posting.
        Returns True if inserted, False if duplicate (same title + company + source).
        """
        company_id = self.get_or_create_company(job.get("company", ""))
        sector_id  = self.get_or_create_sector(job.get("sector", ""))

        # Duplicate check
        dup = self.fetch(
            """
            SELECT id FROM jobs
            WHERE title = :title
              AND source = :source
              AND COALESCE(company_id, -1) = COALESCE(:company_id, -1)
            LIMIT 1
            """,
            {
                "title":      job.get("title", "").strip(),
                "source":     job.get("source", ""),
                "company_id": company_id,
            },
        )
        if not dup.empty:
            return int(dup.iloc[0]["id"])

        self.execute(
            """
            INSERT INTO jobs
                (title, company_id, sector_id, location, contract,
                 experience, description, source, source_url, posted_at)
            VALUES
                (:title, :company_id, :sector_id, :location, :contract,
                 :experience, :description, :source, :source_url, :posted_at)
            """,
            {
                "title":       job.get("title", "").strip(),
                "company_id":  company_id,
                "sector_id":   sector_id,
                "location":    job.get("location", ""),
                "contract":    job.get("contract", ""),
                "experience":  job.get("experience", ""),
                "description": job.get("description", ""),
                "source":      job.get("source", ""),
                "source_url":  job.get("source_url", ""),
                "posted_at":   job.get("posted_at") or date.today(),
            },
        )

        # Save raw salary if present
        job_id = self.fetch(
            """
            SELECT id FROM jobs
            WHERE title = :title
              AND source = :source
              AND COALESCE(company_id, -1) = COALESCE(:company_id, -1)
            LIMIT 1
            """,
            {
                "title": job.get("title", "").strip(),
                "source": job.get("source", ""),
                "company_id": company_id,
            },
        )
        if not job_id.empty and job.get("salary_raw"):
            self._save_raw_salary(int(job_id.iloc[0]["id"]), job["salary_raw"])

        return int(job_id.iloc[0]["id"]) if not job_id.empty else None

    def _save_raw_salary(self, job_id: int, salary_raw: str):
        """Parse and store salary from raw string (called internally)."""
        import re

        text_clean = salary_raw.replace("\xa0", " ").replace(",", "")
        patterns = [
            r"(\d[\d\s]*)\s*[-–—]\s*(\d[\d\s]*)\s*TND",
            r"De\s+(\d[\d\s]*)\s+[àa]\s+(\d[\d\s]*)\s*TND",
            r"Salaire\s*:\s*(\d[\d\s]*)\s*TND",
        ]
        for pattern in patterns:
            m = re.search(pattern, text_clean, re.IGNORECASE)
            if m:
                nums = [float(n.replace(" ", "")) for n in m.groups()]
                min_s = min(nums)
                max_s = max(nums) if len(nums) > 1 else min_s
                self.execute(
                    """
                    INSERT INTO salaries (job_id, min_tnd, max_tnd)
                    VALUES (:job_id, :min_tnd, :max_tnd)
                    ON CONFLICT DO NOTHING
                    """,
                    {"job_id": job_id, "min_tnd": min_s, "max_tnd": max_s},
                )
                return

    # ── Skills ─────────────────────────────────────────────────────────────────

    def get_or_create_skill(self, name: str, category: str = "") -> int:
        """Return skill id, creating it if needed."""
        normalized = name.lower().strip()
        row = self.fetch(
            "SELECT id FROM skills WHERE normalized_name = :n", {"n": normalized}
        )
        if not row.empty:
            return int(row.iloc[0]["id"])
        self.execute(
            """
            INSERT INTO skills (name, normalized_name, category)
            VALUES (:name, :normalized, :category)
            ON CONFLICT (normalized_name) DO NOTHING
            """,
            {"name": name.strip(), "normalized": normalized, "category": category},
        )
        row = self.fetch(
            "SELECT id FROM skills WHERE normalized_name = :n", {"n": normalized}
        )
        return int(row.iloc[0]["id"])

    def link_job_skill(self, job_id: int, skill_id: int, is_required: bool = True):
        self.execute(
            """
            INSERT INTO job_skills (job_id, skill_id, is_required)
            VALUES (:job_id, :skill_id, :required)
            ON CONFLICT DO NOTHING
            """,
            {"job_id": job_id, "skill_id": skill_id, "required": is_required},
        )

    # ── Scrape logs ────────────────────────────────────────────────────────────

    def log_run(self, source: str, jobs_found: int, jobs_new: int,
                status: str = "success", error_msg: str = None):
        self.execute(
            """
            INSERT INTO scrape_logs (source, jobs_found, jobs_new, status, error_msg)
            VALUES (:source, :found, :new, :status, :error)
            """,
            {
                "source": source,
                "found":  jobs_found,
                "new":    jobs_new,
                "status": status,
                "error":  error_msg,
            },
        )

    def start_scrape_run(self, source: str) -> int:
        row = self.execute_returning(
            """
            INSERT INTO scrape_runs (source)
            VALUES (:source)
            RETURNING id
            """,
            {"source": source},
        )
        return int(row.iloc[0]["id"])

    def link_job_to_scrape_run(self, run_id: int, job_id: int):
        self.execute(
            """
            INSERT INTO scrape_run_jobs (run_id, job_id)
            VALUES (:run_id, :job_id)
            ON CONFLICT DO NOTHING
            """,
            {"run_id": run_id, "job_id": job_id},
        )

    def finish_scrape_run(self, run_id: int, jobs_found: int, jobs_new: int,
                          status: str = "success", error_msg: str = None):
        self.execute(
            """
            UPDATE scrape_runs
            SET completed_at = NOW(), jobs_found = :found, jobs_new = :new,
                status = :status, error_msg = :error
            WHERE id = :run_id
            """,
            {
                "run_id": run_id,
                "found": jobs_found,
                "new": jobs_new,
                "status": status,
                "error": error_msg,
            },
        )

    def get_latest_scrape_run_id(self) -> int | None:
        row = self.fetch(
            """
            SELECT id FROM scrape_runs
            WHERE status IN ('success', 'partial')
            ORDER BY completed_at DESC NULLS LAST, id DESC
            LIMIT 1
            """
        )
        return int(row.iloc[0]["id"]) if not row.empty else None

    def get_scrape_runs(self, limit: int = 30) -> pd.DataFrame:
        return self.fetch(
            """
            SELECT id, source, started_at, completed_at, jobs_found, jobs_new, status
            FROM scrape_runs
            ORDER BY completed_at DESC NULLS LAST, id DESC
            LIMIT :limit
            """,
            {"limit": limit},
        )

    # ── Analysis reads (used by analysis/ modules) ─────────────────────────────

    def get_all_jobs_with_description(self) -> pd.DataFrame:
        return self.fetch(
            """
            SELECT j.id, j.title, j.description, j.source,
                   j.location, j.contract, j.posted_at,
                   c.name AS company_name,
                   s.name AS sector_name
            FROM jobs j
            LEFT JOIN companies c ON c.id = j.company_id
            LEFT JOIN sectors   s ON s.id = j.sector_id
            WHERE j.is_active = TRUE
            """
        )

    def get_all_jobs_with_date(self) -> pd.DataFrame:
        return self.fetch(
            """
            SELECT j.id AS job_id, j.title, j.posted_at, j.source,
                   s.name AS sector_name
            FROM jobs j
            LEFT JOIN sectors s ON s.id = j.sector_id
            WHERE j.posted_at IS NOT NULL
              AND j.is_active = TRUE
            ORDER BY j.posted_at
            """
        )

    def get_jobs_with_salary_raw(self) -> pd.DataFrame:
        """Return jobs that have a salary entry, with normalized title."""
        return self.fetch(
            """
            SELECT j.id AS job_id,
                   j.title,
                   LOWER(TRIM(j.title)) AS title_normalized,
                   sal.min_tnd,
                   sal.max_tnd,
                   s.name AS sector_name
            FROM jobs j
            JOIN salaries sal ON sal.job_id = j.id
            LEFT JOIN sectors s ON s.id = j.sector_id
            WHERE j.is_active = TRUE
            """
        )

    # ── Analysis writes ────────────────────────────────────────────────────────

    def save_skills_analysis(self, df: pd.DataFrame):
        """
        Persist skill frequency results.
        Expects columns: skill, count, category, pct_jobs
        Uses a simple analysis_results table (create if needed).
        """
        self.execute(
            """
            CREATE TABLE IF NOT EXISTS analysis_skills (
                id          SERIAL PRIMARY KEY,
                run_date    DATE DEFAULT CURRENT_DATE,
                skill       VARCHAR(120),
                category    VARCHAR(60),
                job_count   INT,
                pct_jobs    NUMERIC(5,1)
            )
            """
        )
        self.execute(
            "DELETE FROM analysis_skills WHERE run_date = CURRENT_DATE"
        )
        for _, row in df.iterrows():
            self.execute(
                """
                INSERT INTO analysis_skills (skill, category, job_count, pct_jobs)
                VALUES (:skill, :category, :count, :pct)
                """,
                {
                    "skill":    row["skill"],
                    "category": row.get("category", ""),
                    "count":    int(row["count"]),
                    "pct":      float(row.get("pct_jobs", 0)),
                },
            )

    def save_salary_analysis(self, df: pd.DataFrame):
        """Persist per-job salary data (min/max already parsed)."""
        self.execute(
            """
            CREATE TABLE IF NOT EXISTS analysis_salaries (
                id          SERIAL PRIMARY KEY,
                run_date    DATE DEFAULT CURRENT_DATE,
                job_id      INT,
                min_tnd     NUMERIC(10,2),
                max_tnd     NUMERIC(10,2),
                mid_tnd     NUMERIC(10,2)
            )
            """
        )
        self.execute(
            "DELETE FROM analysis_salaries WHERE run_date = CURRENT_DATE"
        )
        for _, row in df.iterrows():
            self.execute(
                """
                INSERT INTO analysis_salaries (job_id, min_tnd, max_tnd, mid_tnd)
                VALUES (:job_id, :min_tnd, :max_tnd, :mid_tnd)
                """,
                {
                    "job_id":  int(row["job_id"]),
                    "min_tnd": float(row.get("min_tnd") or 0),
                    "max_tnd": float(row.get("max_tnd") or 0),
                    "mid_tnd": float(row.get("mid_tnd") or 0),
                },
            )

    def save_trends(self, monthly_total: pd.DataFrame,
                    monthly_sector: pd.DataFrame,
                    skill_trend: pd.DataFrame):
        """Persist trend DataFrames for Power BI export."""
        export_dir = os.getenv("EXPORT_DIR", "exports")
        os.makedirs(export_dir, exist_ok=True)
        monthly_total.to_csv(f"{export_dir}/monthly_total.csv",  index=False)
        monthly_sector.to_csv(f"{export_dir}/monthly_sector.csv", index=False)
        skill_trend.to_csv(f"{export_dir}/skill_trend.csv",       index=False)
        logger.info("Trend CSVs exported to %s/", export_dir)

    def save_ai_summary(self, result: dict):
        """Persist the AI-generated summary text."""
        self.execute(
            """
            CREATE TABLE IF NOT EXISTS ai_summaries (
                id           SERIAL PRIMARY KEY,
                generated_at DATE DEFAULT CURRENT_DATE,
                model        VARCHAR(80),
                summary      TEXT,
                tokens_used  INT
            )
            """
        )
        self.execute(
            """
            INSERT INTO ai_summaries (generated_at, model, summary, tokens_used)
            VALUES (:generated_at, :model, :summary, :tokens_used)
            """,
            {
                "generated_at": result.get("generated_at", str(date.today())),
                "model":        result.get("model", "openrouter"),
                "summary":      result.get("summary", ""),
                "tokens_used":  result.get("tokens_used", 0),
            },
        )

    # ── AI context reads (used by ai/summarizer.py) ────────────────────────────

    def get_top_skills(self, n: int = 20) -> list[dict]:
        df = self.fetch(
            """
            SELECT s.name AS skill,
                   COUNT(js.job_id) AS demand,
                   s.category
            FROM skills s
            JOIN job_skills js ON s.id = js.skill_id
            GROUP BY s.name, s.category
            ORDER BY demand DESC
            LIMIT :n
            """,
            {"n": n},
        )
        return df.to_dict(orient="records")

    def get_top_sectors(self, n: int = 10) -> list[dict]:
        df = self.fetch(
            """
            SELECT sec.name AS sector,
                   COUNT(j.id) AS job_count
            FROM jobs j
            JOIN sectors sec ON sec.id = j.sector_id
            WHERE j.is_active = TRUE
            GROUP BY sec.name
            ORDER BY job_count DESC
            LIMIT :n
            """,
            {"n": n},
        )
        return df.to_dict(orient="records")

    def get_salary_summary(self) -> list[dict]:
        df = self.fetch(
            """
            SELECT
                LOWER(TRIM(j.title)) AS role,
                ROUND(AVG(sal.min_tnd), 0) AS avg_min_tnd,
                ROUND(AVG(sal.max_tnd), 0) AS avg_max_tnd,
                COUNT(*) AS sample_size
            FROM salaries sal
            JOIN jobs j ON j.id = sal.job_id
            GROUP BY LOWER(TRIM(j.title))
            HAVING COUNT(*) >= 2
            ORDER BY avg_min_tnd DESC
            LIMIT 15
            """
        )
        return df.to_dict(orient="records")

    def get_monthly_growth(self, months: int = 3) -> list[dict]:
        df = self.fetch(
            """
            SELECT
                TO_CHAR(DATE_TRUNC('month', posted_at), 'YYYY-MM') AS month,
                COUNT(*) AS total_jobs
            FROM jobs
            WHERE posted_at >= CURRENT_DATE - INTERVAL ':m months'
              AND is_active = TRUE
            GROUP BY DATE_TRUNC('month', posted_at)
            ORDER BY month
            """,
            {"m": months},
        )
        return df.to_dict(orient="records")