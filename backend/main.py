import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import asyncio
import json
import logging
import subprocess
import threading
import time
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

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
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
}


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


class CVUploadResponse(BaseModel):
    success: bool
    message: str
    cv_path: Optional[str] = None


def run_pipeline_background(cv_path: Optional[str] = None, skip_scraping: bool = False, match_cv: bool = False):
    """Run the main pipeline in a background thread."""
    global pipeline_state
    
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
    })
    
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
        
        log(f"Running: {' '.join(cmd)}")
        if cv_path:
            log(f"CV-driven search enabled: {cv_path}")
        else:
            log("No CV supplied; using the general search catalogue")
        
        # Initialize steps
        scrapers = ["keejob", "emploitunisie", "rekrute", "linkedin"]
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
        process = subprocess.Popen(
            cmd,
            cwd=os.path.join(os.path.dirname(__file__), '..'),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            universal_newlines=True
        )
        
        current_step_idx = 0
        step_map = {
            "keejob": 0, "emploitunisie": 1, "rekrute": 2, "linkedin": 3,
            "skills": 4, "salary": 5, "trends": 6, "ai": 7, "export": 8, "cv_match": 9
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


def get_cv_matches_from_db(limit: int = 50) -> List[Dict]:
    """Fetch CV matches from database."""
    try:
        from database.db_manager import DBManager
        import pandas as pd
        
        db = DBManager()
        df = db.fetch("""
            SELECT j.id, j.title, j.location, j.contract, j.experience,
                   s.name AS sector_name,
                   j.source, j.source_url, j.posted_at, j.scraped_at,
                   c.name AS company_name,
                   m.match_score, m.summary, m.why_good_match, m.missing_skills,
                   m.recommendation, m.cv_keywords, m.cv_skills, m.created_at AS match_date
            FROM cv_job_matches m
            JOIN jobs j ON j.id = m.job_id
            LEFT JOIN companies c ON c.id = j.company_id
            LEFT JOIN sectors s ON s.id = j.sector_id
            ORDER BY m.match_score DESC, m.created_at DESC
            LIMIT :limit
        """, {"limit": limit})
        
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
                "match_score": int(row.get("match_score", 0)) if pd.notna(row.get("match_score")) else None,
                "summary": str(row.get("summary", "")),
                "why_good_match": str(row.get("why_good_match", "")),
                "missing_skills": missing_skills,
                "recommendation": str(row.get("recommendation", "")),
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


@app.get("/cv-matches")
async def get_cv_matches(limit: int = 50):
    matches = get_cv_matches_from_db(limit)
    return matches


@app.get("/pipeline/status", response_model=PipelineStatus)
async def get_pipeline_status():
    return PipelineStatus(**pipeline_state)


@app.post("/pipeline/run")
async def run_pipeline(
    background_tasks: BackgroundTasks,
    cv_file: Optional[UploadFile] = File(None),
    skip_scraping: bool = Form(False),
    match_cv: bool = Form(False),
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
    background_tasks.add_task(run_pipeline_background, cv_path, skip_scraping, match_cv)
    
    return {"success": True, "message": "Pipeline started", "cv_path": cv_path}


@app.post("/pipeline/stop")
async def stop_pipeline():
    # Note: This would require process management to actually stop
    return {"success": False, "message": "Stop not implemented yet"}


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