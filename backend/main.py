import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import asyncio
import json
import logging
import signal
import subprocess
import threading
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import BackgroundTasks, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("backend")

app = FastAPI(title="Tunisia Jobs API", version="1.0.0")

configured_origins = [
    origin.strip()
    for origin in os.getenv("BACKEND_CORS_ORIGINS", "").split(",")
    if origin.strip()
]
cors_origins = configured_origins or [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:3001",
    "http://127.0.0.1:3001",
    "http://localhost:3002",
    "http://127.0.0.1:3002",
]
cors_origin_regex = os.getenv(
    "BACKEND_CORS_ORIGIN_REGEX",
    r"http://(?:localhost|127\.0\.0\.1|192\.168\.\d+\.\d+):\d+",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_origin_regex=cors_origin_regex,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global state for pipeline progress
pipeline_state = {
    "running": False,
    "progress": 0,
    "label": "idle",
    "steps": [],
    "logs": [],
    "started_at": None,
    "completed_at": None,
    "error": None,
    "cv_path": None,
    "stopped": False,
}
pipeline_process = None
pipeline_stop_requested = False


class JobResponse(BaseModel):
    id: int
    title: str
    company: str
    location: str
    contract: str
    source: str
    source_url: str
    posted_at: str
    description: str
    match_score: Optional[int] = None
    summary: Optional[str] = None
    why_good_match: Optional[str] = None
    missing_skills: Optional[List[str]] = None
    recommendation: Optional[str] = None


class SourceResponse(BaseModel):
    id: str
    name: str


class PipelineStatus(BaseModel):
    running: bool
    progress: int
    label: str
    steps: List[Dict[str, Any]]
    logs: List[Dict[str, Any]]
    started_at: Optional[str]
    completed_at: Optional[str]
    error: Optional[str]
    stopped: bool


class CVUploadResponse(BaseModel):
    success: bool
    message: str
    cv_path: Optional[str] = None


class ApplicationCreate(BaseModel):
    job_id: int
    match_id: Optional[int] = None
    applied_at: Optional[datetime] = None


class ApplicationUpdate(BaseModel):
    replied: bool


def run_pipeline_background(cv_path: Optional[str] = None, skip_scraping: bool = False,
                            match_cv: bool = False, scrape_run_id: Optional[int] = None):
    """Run the main pipeline in a background thread."""
    global pipeline_state, pipeline_process, pipeline_stop_requested
    
    pipeline_state.update({
        "running": True,
        "progress": 0,
        "label": "Starting...",
        "steps": [],
        "logs": [],
        "started_at": datetime.now().isoformat(),
        "completed_at": None,
        "error": None,
        "cv_path": cv_path,
        "stopped": False,
    })
    pipeline_stop_requested = False
    
    def log(msg: str, kind: str = "act"):
        pipeline_state["logs"].append({
            "id": len(pipeline_state["logs"]) + 1,
            "t": datetime.now().strftime("%H:%M:%S"),
            "text": msg,
            "kind": kind
        })
    
    def update_progress(pct: int, label: str):
        pipeline_state["progress"] = pct
        pipeline_state["label"] = label
    
    try:
        # Build command
        cmd = [sys.executable, "main.py", "--once"]
        
        if cv_path:
            cmd.extend(["--cv", cv_path])
        if skip_scraping:
            cmd.append("--skip-scraping")
        if match_cv and cv_path:
            cmd.append("--match-cv")
        if match_cv and scrape_run_id is not None:
            cmd.extend(["--scrape-run-id", str(scrape_run_id)])
        
        log(f"Running: {' '.join(cmd)}")
        if cv_path:
            log(f"CV-driven search enabled: {cv_path}")
        else:
            log("No CV supplied; using the general search catalogue")
        
        # Initialize steps
        scrapers = ["apify", "keejob", "emploitunisie", "rekrute", "linkedin"]
        if skip_scraping:
            scrapers = []
        
        for i, src in enumerate(scrapers):
            pipeline_state["steps"].append({
                "id": src,
                "name": src.capitalize(),
                "status": "ready",
                "found": 0
            })
        
        # Add analysis steps
        pipeline_state["steps"].extend([
            {"id": "skills", "name": "Skills Analysis", "status": "ready", "found": 0},
            {"id": "salary", "name": "Salary Analysis", "status": "ready", "found": 0},
            {"id": "trends", "name": "Trends Analysis", "status": "ready", "found": 0},
            {"id": "ai", "name": "AI Summary", "status": "ready", "found": 0},
            {"id": "export", "name": "Export Data", "status": "ready", "found": 0},
        ])
        
        if match_cv and cv_path:
            pipeline_state["steps"].append({
                "id": "cv_match", "name": "CV Matching", "status": "ready", "found": 0
            })
        
        # Run the pipeline
        creation_flags = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
        process = subprocess.Popen(
            cmd,
            cwd=os.path.join(os.path.dirname(__file__), '..'),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            universal_newlines=True,
            creationflags=creation_flags,
        )
        pipeline_process = process
        
        current_step_idx = 0
        step_map = {
            step["id"]: index for index, step in enumerate(pipeline_state["steps"])
        }
        
        for line in iter(process.stdout.readline, ''):
            if not line:
                break
            line = line.strip()
            if not line:
                continue
            
            log(line)
            
            # Parse log for progress updates
            if "Pipeline started" in line:
                update_progress(5, "Initializing pipeline")
            elif "CV search terms" in line:
                update_progress(10, "Extracted CV keywords")
            elif "Scraping skipped" in line:
                update_progress(15, "Using existing database")
            elif "DBManager connected" in line and current_step_idx < len(scrapers):
                pass
            elif "new jobs inserted" in line:
                # Extract count and update step
                for src in scrapers:
                    if src in line.lower():
                        idx = step_map.get(src, 0)
                        if idx < len(pipeline_state["steps"]):
                            pipeline_state["steps"][idx]["status"] = "running"
                        try:
                            count = int(line.split(": ")[-1].split(" ")[0])
                            pipeline_state["steps"][idx]["found"] = count
                        except:
                            pass
            elif "Analysis complete" in line:
                pipeline_state["steps"][step_map["skills"]]["status"] = "done"
                update_progress(60, "Running analyses...")
            elif "AI summary generated" in line:
                pipeline_state["steps"][step_map["ai"]]["status"] = "done"
                update_progress(80, "Generating AI summary")
            elif "CV Job Matching started" in line:
                pipeline_state["steps"][step_map["cv_match"]]["status"] = "running"
                update_progress(85, "Matching CV to jobs...")
            elif "CV Job Matching complete" in line:
                pipeline_state["steps"][step_map["cv_match"]]["status"] = "done"
                try:
                    count = int(line.split(": ")[-1].split(" ")[0])
                    pipeline_state["steps"][step_map["cv_match"]]["found"] = count
                except:
                    pass
            elif "Export" in line and "complete" in line.lower():
                pipeline_state["steps"][step_map["export"]]["status"] = "done"
                update_progress(95, "Exporting data")
            elif "Pipeline complete" in line:
                update_progress(100, "Complete")
        
        process.wait()
        
        if process.returncode != 0:
            if pipeline_stop_requested:
                pipeline_state["stopped"] = True
                pipeline_state["label"] = "Stopped"
                log("Pipeline stopped by user", "ok")
                return
            raise Exception(f"Pipeline exited with code {process.returncode}")
        
        # Mark all steps as done
        for step in pipeline_state["steps"]:
            if step["status"] != "error":
                step["status"] = "done"
        
        pipeline_state["completed_at"] = datetime.now().isoformat()
        log("Pipeline completed successfully", "ok")
        
    except Exception as e:
        logger.exception("Pipeline failed")
        pipeline_state["error"] = str(e)
        pipeline_state["completed_at"] = datetime.now().isoformat()
        log(f"Pipeline failed: {e}", "err")
    finally:
        pipeline_process = None
        pipeline_state["running"] = False


def get_jobs_from_db(limit: int = 100, offset: int = 0) -> List[Dict]:
    """Fetch jobs from database."""
    try:
        from database.db_manager import DBManager
        from data.clean_data import get_clean_jobs
        
        jobs_df = get_clean_jobs()
        
        # Apply limit/offset
        jobs_df = jobs_df.iloc[offset:offset+limit]
        
        jobs = []
        for _, row in jobs_df.iterrows():
            jobs.append({
                "id": int(row.get("id", 0)),
                "title": str(row.get("title_clean", "")),
                "company": str(row.get("company", "")),
                "location": str(row.get("location_clean", "")),
                "contract": str(row.get("contract_clean", "")),
                "source": str(row.get("source_label", "")),
                "source_url": "",  # Not in clean export
                "posted_at": str(row.get("posted_at", "")),
                "description": "",
                "match_score": None,
            })
        return jobs
    except Exception as e:
        logger.error(f"Error fetching jobs: {e}")
        return []


def get_cv_matches_from_db(limit: int = 50, scrape_run_id: Optional[int] = None) -> List[Dict]:
    """Fetch CV matches from database."""
    try:
        from database.db_manager import DBManager
        import pandas as pd
        
        db = DBManager()
        scrape_run_id = scrape_run_id or db.get_latest_scrape_run_id()
        run_filter = ""
        params = {"limit": limit}
        if scrape_run_id is not None:
            run_filter = """
                AND EXISTS (
                    SELECT 1 FROM scrape_run_jobs srj
                    WHERE srj.run_id = :scrape_run_id AND srj.job_id = j.id
                )
            """
            params["scrape_run_id"] = scrape_run_id

        df = db.fetch(f"""
            SELECT j.id, m.id AS match_id, j.title, j.location, j.contract, j.experience,
                   s.name AS sector_name,
                   j.source, j.source_url, j.posted_at, j.scraped_at,
                   c.name AS company_name,
                   m.match_score, m.summary, m.why_good_match, m.missing_skills,
                   m.recommendation, m.cover_letter, m.cv_keywords, m.cv_skills, m.created_at AS match_date
            FROM cv_job_matches m
            JOIN jobs j ON j.id = m.job_id
            LEFT JOIN companies c ON c.id = j.company_id
            LEFT JOIN sectors s ON s.id = j.sector_id
            WHERE 1 = 1
            {run_filter}
            ORDER BY m.match_score DESC, m.created_at DESC
            LIMIT :limit
        """, params)
        
        matches = []
        for _, row in df.iterrows():
            # PostgreSQL arrays are already returned as Python lists by psycopg2
            missing_skills = row.get("missing_skills") or []
            cv_keywords = row.get("cv_keywords") or []
            cv_skills = row.get("cv_skills")
            if isinstance(cv_skills, str):
                try:
                    import json
                    cv_skills = json.loads(cv_skills)
                except:
                    cv_skills = {}
            elif cv_skills is None:
                cv_skills = {}
            
            matches.append({
                "id": int(row.get("id", 0)),
                "match_id": int(row.get("match_id", 0)),
                "title": str(row.get("title", "")),
                "company": str(row.get("company_name", "")),
                "location": str(row.get("location", "")),
                "contract": str(row.get("contract", "")),
                "experience": str(row.get("experience", "")),
                "sector": str(row.get("sector_name", "")),
                "source": str(row.get("source", "")),
                "source_url": str(row.get("source_url", "")),
                "posted_at": str(row.get("posted_at", "")),
                "scraped_at": str(row.get("scraped_at", "")),
                "scrape_run_id": scrape_run_id,
                "match_score": int(row.get("match_score", 0)) if pd.notna(row.get("match_score")) else None,
                "summary": str(row.get("summary", "")),
                "why_good_match": str(row.get("why_good_match", "")),
                "missing_skills": missing_skills,
                "recommendation": str(row.get("recommendation", "")),
                "cover_letter": str(row.get("cover_letter", "") or ""),
                "cv_keywords": cv_keywords,
                "cv_skills": cv_skills,
                "match_date": str(row.get("match_date", "")),
            })
        return matches
    except Exception as e:
        logger.error(f"Error fetching CV matches: {e}")
        return []


@app.get("/health")
async def health():
    return {"status": "ok", "timestamp": datetime.now().isoformat()}


@app.get("/jobs", response_model=List[JobResponse])
async def get_jobs(limit: int = 100, offset: int = 0):
    jobs = get_jobs_from_db(limit, offset)
    return jobs


@app.get("/sources", response_model=List[SourceResponse])
async def get_sources():
    return [
        {"id": "keejob", "name": "KeeJob"},
        {"id": "emploitunisie", "name": "EmploiTunisie"},
        {"id": "rekrute", "name": "ReKrute"},
        {"id": "linkedin", "name": "LinkedIn"},
    ]


@app.get("/scrape-runs")
async def get_scrape_runs(limit: int = 30):
    from database.db_manager import DBManager

    db = DBManager()
    df = db.get_scrape_runs(limit)
    return [
        {
            "id": int(row["id"]),
            "source": str(row["source"]),
            "started_at": row["started_at"].isoformat() if row["started_at"] else None,
            "completed_at": row["completed_at"].isoformat() if row["completed_at"] else None,
            "jobs_found": int(row["jobs_found"] or 0),
            "jobs_new": int(row["jobs_new"] or 0),
            "status": str(row["status"]),
        }
        for _, row in df.iterrows()
        if str(row["status"]) in {"success", "partial"}
    ]


@app.get("/cv-matches")
async def get_cv_matches(limit: int = 50, scrape_run_id: Optional[int] = None):
    matches = get_cv_matches_from_db(limit, scrape_run_id)
    return matches


def application_response(row) -> Dict[str, Any]:
    return {
        "job_id": int(row["job_id"]),
        "match_id": int(row["match_id"]) if row["match_id"] == row["match_id"] else None,
        "applied_at": row["applied_at"].isoformat() if row["applied_at"] else None,
        "replied": bool(row["replied"]),
        "id": int(row["id"]),
        "title": str(row["title"] or ""),
        "company": str(row["company_name"] or ""),
        "location": str(row["location"] or ""),
        "contract": str(row["contract"] or ""),
        "source": str(row["source"] or ""),
        "source_url": str(row["source_url"] or ""),
        "posted_at": str(row["posted_at"] or ""),
        "scraped_at": str(row["scraped_at"] or ""),
        "description": str(row["description"] or row["summary"] or ""),
        "match_score": int(row["match_score"] or 0),
        "cover_letter": str(row["cover_letter"] or ""),
        "missing_skills": row["missing_skills"] or [],
        "cv_keywords": row["cv_keywords"] or [],
    }


@app.get("/applications")
async def get_applications():
    from database.db_manager import DBManager

    db = DBManager()
    return [application_response(row) for _, row in db.get_applications().iterrows()]


@app.post("/applications")
async def create_application(application: ApplicationCreate):
    from database.db_manager import DBManager

    db = DBManager()
    try:
        saved = db.add_application(application.job_id, application.match_id, application.applied_at)
    except Exception as exc:
        logger.exception("Failed to save application")
        raise HTTPException(status_code=400, detail=str(exc))
    if saved.empty:
        raise HTTPException(status_code=404, detail="Job not found")
    rows = db.get_applications()
    row = rows[rows["job_id"] == application.job_id]
    if row.empty:
        raise HTTPException(status_code=404, detail="Job not found")
    return application_response(row.iloc[0])


@app.patch("/applications/{job_id}")
async def update_application(job_id: int, application: ApplicationUpdate):
    from database.db_manager import DBManager

    db = DBManager()
    saved = db.set_application_replied(job_id, application.replied)
    if saved.empty:
        raise HTTPException(status_code=404, detail="Application not found")
    rows = db.get_applications()
    row = rows[rows["job_id"] == job_id]
    return application_response(row.iloc[0])


@app.delete("/applications/{job_id}")
async def delete_application(job_id: int):
    from database.db_manager import DBManager

    db = DBManager()
    db.remove_application(job_id)
    return {"success": True}


@app.delete("/scrape-runs/{run_id}")
async def delete_scrape_run(run_id: int):
    from database.db_manager import DBManager

    db = DBManager()
    if not db.delete_scrape_run(run_id):
        raise HTTPException(status_code=404, detail="Scrape run not found")
    return {"success": True, "run_id": run_id}


@app.get("/pipeline/status", response_model=PipelineStatus)
async def get_pipeline_status():
    return PipelineStatus(**pipeline_state)


@app.post("/pipeline/run")
async def run_pipeline(
    background_tasks: BackgroundTasks,
    cv_file: Optional[UploadFile] = File(None),
    skip_scraping: bool = Form(False),
    match_cv: bool = Form(False),
    scrape_run_id: Optional[int] = Form(None),
):
    global pipeline_state
    
    if pipeline_state["running"]:
        raise HTTPException(status_code=400, detail="Pipeline already running")
    
    cv_path = None
    if cv_file and cv_file.filename:
        if not cv_file.filename.lower().endswith('.pdf'):
            raise HTTPException(status_code=400, detail="Only PDF files allowed")
        
        # Save uploaded CV
        upload_dir = Path(os.path.join(os.path.dirname(__file__), '..', 'uploads'))
        upload_dir.mkdir(exist_ok=True)
        
        cv_path = str(upload_dir / cv_file.filename)
        with open(cv_path, "wb") as f:
            content = await cv_file.read()
            f.write(content)
        
        logger.info(f"Saved CV to {cv_path}")
    
    # Run pipeline in background
    background_tasks.add_task(
        run_pipeline_background, cv_path, skip_scraping, match_cv, scrape_run_id
    )
    
    return {"success": True, "message": "Pipeline started", "cv_path": cv_path}


@app.post("/pipeline/stop")
async def stop_pipeline():
    global pipeline_stop_requested

    if not pipeline_state["running"] or pipeline_process is None:
        return {"success": False, "message": "No pipeline is running"}

    pipeline_stop_requested = True
    pipeline_state["label"] = "Stopping..."
    process = pipeline_process
    try:
        if os.name == "nt":
            process.send_signal(signal.CTRL_BREAK_EVENT)
        else:
            process.send_signal(signal.SIGINT)
    except (OSError, ValueError):
        process.terminate()

    return {"success": True, "message": "Pipeline stop requested"}


@app.post("/cover-letters")
async def create_cover_letter(
    job_id: int = Form(...),
    match_id: Optional[int] = Form(None),
    cv_file: Optional[UploadFile] = File(None),
):
    from ai.cover_letter import generate_cover_letter
    from cv_matching import extract_cv_text
    from database.db_manager import DBManager

    cv_path = pipeline_state.get("cv_path")
    temporary_cv = False
    if cv_file and cv_file.filename:
        if not cv_file.filename.lower().endswith(".pdf"):
            raise HTTPException(status_code=400, detail="Only PDF files allowed")
        upload_dir = Path(os.path.join(os.path.dirname(__file__), "..", "uploads"))
        upload_dir.mkdir(exist_ok=True)
        cv_path = str(upload_dir / f"cover-{uuid.uuid4().hex}.pdf")
        with open(cv_path, "wb") as output:
            output.write(await cv_file.read())
        temporary_cv = True

    if not cv_path:
        raise HTTPException(status_code=400, detail="Upload the CV used for matching first")

    db = DBManager()
    job_rows = db.fetch("""
        SELECT j.id, j.title, j.location, j.contract, j.description,
               COALESCE(c.name, '') AS company_name,
               COALESCE(m.cv_keywords, ARRAY[]::TEXT[]) AS cv_keywords,
               COALESCE(m.missing_skills, ARRAY[]::TEXT[]) AS missing_skills
        FROM jobs j
        LEFT JOIN companies c ON c.id = j.company_id
        LEFT JOIN cv_job_matches m ON m.job_id = j.id
        WHERE j.id = :job_id
    """, {"job_id": job_id})
    if job_rows.empty:
        raise HTTPException(status_code=404, detail="Job not found")

    row = job_rows.iloc[0]
    try:
        letter = generate_cover_letter(
            extract_cv_text(cv_path),
            {
                "title": str(row["title"] or ""),
                "company": str(row["company_name"] or ""),
                "location": str(row["location"] or ""),
                "contract": str(row["contract"] or ""),
                "description": str(row["description"] or ""),
            },
            {
                "cv_keywords": row["cv_keywords"] or [],
                "missing_skills": row["missing_skills"] or [],
            },
        )
        db.save_cover_letter(job_id, letter)
        return {"success": True, "cover_letter": letter, "job_id": job_id, "match_id": match_id}
    except Exception as exc:
        logger.exception("Failed to generate cover letter")
        raise HTTPException(status_code=502, detail=str(exc))
    finally:
        if temporary_cv:
            try:
                Path(cv_path).unlink(missing_ok=True)
            except OSError:
                logger.warning("Could not remove temporary CV file %s", cv_path)


@app.get("/export/cv-matches")
async def export_cv_matches():
    """Download cv_matches.csv"""
    file_path = Path(os.path.join(os.path.dirname(__file__), '..', 'exports', 'cv_matches.csv'))
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Export file not found")
    return FileResponse(file_path, filename="cv_matches.csv", media_type="text/csv")


@app.get("/export/jobs")
async def export_jobs():
    """Download jobs_clean.csv"""
    file_path = Path(os.path.join(os.path.dirname(__file__), '..', 'exports', 'jobs_clean.csv'))
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Export file not found")
    return FileResponse(file_path, filename="jobs_clean.csv", media_type="text/csv")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)