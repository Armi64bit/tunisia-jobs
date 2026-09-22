"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import OverviewView from "./OverviewView";
import ScraperView from "./ScraperView";
import MatchesView from "./MatchesView";
import Sidebar from "./Sidebar";
import Toast from "./Toast";
import { JOBS, NEW_JOBS, SAMPLE_CV_NAME, SAMPLE_CV_SKILLS, SOURCES } from "../lib/demo-data";
import { skillScore } from "../lib/api";
import { nextLogId, timeNow } from "../lib/format";
import type {
  BackendState,
  CvInfo,
  Job,
  LogLine,
  MatchedJob,
  PipelineLog,
  PipelineStep,
  PipelineStatus,
  RunState,
  RunStep,
  Source,
  SourceId,
  ViewId,
} from "../lib/types";

const PER_SOURCE = [18, 10, 8, 14];

function sourceName(id: SourceId): string {
  return SOURCES.find((s) => s.id === id)?.name ?? id;
}

function normalizeJob(job: any): Job {
  return {
    id: job.id,
    title: job.title ?? "",
    company: job.company ?? "",
    source: job.source,
    city: job.city ?? job.location ?? "",
    contract: job.contract ?? "",
    date: job.date ?? job.posted_at ?? "",
    salary: job.salary ?? "",
    skills: Array.isArray(job.skills)
      ? job.skills
      : Array.isArray(job.cv_keywords)
        ? job.cv_keywords
        : [],
    desc: job.desc ?? job.description ?? job.summary ?? "",
    applyUrl: job.applyUrl ?? job.source_url,
    source_url: job.source_url,
  };
}

function computeMatches(jobs: Job[]): MatchedJob[] {
  return jobs
    .map((job) => {
      const score = skillScore(job, SAMPLE_CV_SKILLS);
      return {
        job,
        score,
        matched: job.skills.filter((s) => SAMPLE_CV_SKILLS.includes(s)),
        missing: job.skills.filter((s) => !SAMPLE_CV_SKILLS.includes(s)),
      };
    })
    .sort((a, b) => b.score - a.score)
    .slice(0, 6);
}

function convertPipelineLogs(logs: PipelineLog[]): LogLine[] {
  return logs.map((l) => ({
    id: l.id,
    t: l.t,
    text: l.text,
    kind: l.kind as LogLine["kind"],
  }));
}

function convertPipelineSteps(steps: PipelineStep[]): RunStep[] {
  return steps.map((s) => ({
    id: s.id as SourceId,
    name: s.name,
    status: s.status as RunStep["status"],
    found: s.found,
  }));
}

export default function TunisJobsApp() {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [loadingJobs, setLoadingJobs] = useState(true);
  const [backend, setBackend] = useState<BackendState>({
    online: false,
    label: "Backend: connecting...",
  });

  const [view, setView] = useState<ViewId>("overview");

  const [cv, setCv] = useState<CvInfo | null>(null);
  const [cvFile, setCvFile] = useState<File | null>(null);
  const [cvError, setCvError] = useState<string | null>(null);

  const [runState, setRunState] = useState<RunState>("idle");
  const [steps, setSteps] = useState<RunStep[]>([]);
  const [progress, setProgress] = useState({ pct: 0, label: "idle" });
  const [pipelineSub, setPipelineSub] = useState("Ready");
  const [logLines, setLogLines] = useState<LogLine[]>([]);
  const [matches, setMatches] = useState<MatchedJob[]>([]);

  const [toast, setToast] = useState<{ message: string; kind: "ok" | "err" } | null>(null);
  const toastRef = useRef<number | null>(null);
  const statusPollRef = useRef<number | null>(null);

  useEffect(() => () => {
    if (toastRef.current) window.clearTimeout(toastRef.current);
    if (statusPollRef.current) window.clearInterval(statusPollRef.current);
  }, []);

  const showToast = useCallback((message: string, kind: "ok" | "err" = "ok") => {
    setToast({ message, kind });
    if (toastRef.current) window.clearTimeout(toastRef.current);
    toastRef.current = window.setTimeout(() => setToast(null), 3400);
  }, []);

  const switchView = useCallback((v: ViewId) => setView(v), []);

  const applyCv = useCallback(
    (file: File) => {
      if (file.type !== "application/pdf" && !/\.pdf$/i.test(file.name)) {
        setCvError("That file is not a PDF — upload a .pdf CV.");
        return;
      }
      if (file.size > 10 * 1024 * 1024) {
        setCvError("This CV is over 10 MB — try a smaller file.");
        return;
      }
      setCvError(null);
      setCv({ name: file.name, size: file.size, sample: false });
      setCvFile(file);
      showToast(`CV loaded: ${file.name}`);
    },
    [showToast],
  );

  const removeCv = useCallback(() => {
    setCv(null);
    setCvFile(null);
    setCvError(null);
  }, []);

  const loadJobs = useCallback(async () => {
    setLoadingJobs(true);
    try {
      const { jobs: fetchedJobs } = await fetch("/api/jobs").then(r => r.json()).catch(() => ({ jobs: JOBS }));
      // Use local API if available, otherwise demo data
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8001"}/jobs?limit=200`);
      if (response.ok) {
        const data = await response.json();
        setJobs(Array.isArray(data) ? data.map(normalizeJob) : JOBS);
      } else {
        setJobs(JOBS);
      }
    } catch {
      setJobs(JOBS);
    } finally {
      setLoadingJobs(false);
    }
  }, []);

  const loadCVMatches = useCallback(async () => {
    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8001"}/cv-matches?limit=100`);
      if (response.ok) {
        const data = await response.json();
        // Convert to MatchedJob format
        const matchedJobs: MatchedJob[] = data.map((job: any) => ({
          job: {
            id: job.id,
            title: job.title,
            company: job.company,
            source: job.source,
            city: job.location,
            contract: job.contract,
            date: job.posted_at,
            salary: "",
            skills: job.cv_keywords || [],
            desc: job.summary || "",
            applyUrl: job.source_url,
          },
          score: job.match_score || 0,
          matched: job.cv_keywords || [],
          missing: job.missing_skills || [],
        }));
        setMatches(matchedJobs);
      }
    } catch (e) {
      console.error("Failed to load CV matches:", e);
    }
  }, []);

  const loadBackendState = useCallback(async () => {
    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8001"}/health`);
      if (response.ok) {
        setBackend({ online: true, label: "Backend: live" });
      } else {
        setBackend({ online: false, label: "Backend: offline" });
      }
    } catch {
      setBackend({ online: false, label: "Backend: offline" });
    }
  }, []);

  useEffect(() => {
    loadJobs();
    loadCVMatches();
    loadBackendState();
  }, [loadJobs, loadCVMatches, loadBackendState]);

  const pollPipelineStatus = useCallback(async () => {
    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8001"}/pipeline/status`);
      if (response.ok) {
        const status: PipelineStatus = await response.json();
        
        setRunState(status.running ? "running" : (status.error ? "error" : status.completed_at ? "done" : "idle"));
        setSteps(convertPipelineSteps(status.steps));
        setProgress({ pct: status.progress, label: status.label });
        setPipelineSub(status.label);
        setLogLines(convertPipelineLogs(status.logs));
        
        if (status.running) {
          statusPollRef.current = window.setTimeout(pollPipelineStatus, 1000);
        } else if (status.completed_at && !status.error) {
          showToast("Pipeline completed successfully!", "ok");
          loadJobs();
          loadCVMatches();
        } else if (status.error) {
          showToast(`Pipeline failed: ${status.error}`, "err");
        }
      }
    } catch (e) {
      console.error("Failed to poll pipeline status:", e);
    }
  }, [showToast, loadJobs, loadCVMatches]);

  const runPipeline = useCallback(
    async (cvFile: File | null, skipScraping: boolean, matchCv: boolean) => {
      if (runState === "running") return;
      
      setRunState("running");
      setPipelineSub("Starting...");
      setLogLines([]);
      setProgress({ pct: 0, label: "Initializing" });
      setSteps([]);

      const formData = new FormData();
      if (cvFile) formData.append("cv_file", cvFile);
      formData.append("skip_scraping", String(skipScraping));
      formData.append("match_cv", String(matchCv));

      try {
        const response = await fetch(`${process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8001"}/pipeline/run`, {
          method: "POST",
          body: formData,
        });
        const result = await response.json();
        
        if (result.success) {
          showToast("Pipeline started", "ok");
          // Start polling
          statusPollRef.current = window.setTimeout(pollPipelineStatus, 1000);
        } else {
          setRunState("error");
          showToast(result.message || "Failed to start pipeline", "err");
        }
      } catch (e) {
        setRunState("error");
        showToast("Failed to start pipeline", "err");
      }
    },
    [runState, showToast, pollPipelineStatus]
  );

  const matchCv = useCallback(() => {
    if (!cv) return;
    loadCVMatches();
    setView("matches");
    showToast("Matches loaded", "ok");
  }, [cv, loadCVMatches, showToast]);

  const matchDisabled = !cv || runState === "running";

  const handleApply = useCallback(
    (job: Job) => {
      if (job.applyUrl) {
        window.open(job.applyUrl, "_blank", "noopener,noreferrer");
      } else if (job.source_url) {
        window.open(job.source_url, "_blank", "noopener,noreferrer");
      } else {
        showToast(
          `Apply via ${sourceName(job.source)} — link not available in sample data.`,
        );
      }
    },
    [showToast],
  );

  const downloadExport = useCallback(async (type: "cv-matches" | "jobs") => {
    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8001"}/export/${type}`);
      if (response.ok) {
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = type === "cv-matches" ? "cv_matches.csv" : "jobs_clean.csv";
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
        showToast(`Downloaded ${type}.csv`, "ok");
      } else {
        showToast("Export not available", "err");
      }
    } catch {
      showToast("Download failed", "err");
    }
  }, [showToast]);

  return (
    <div className="shell">
      <header className="appbar">
        <div className="brand">
          <span className="brand-mark" aria-hidden="true">TJ</span>
          <span className="brand-name">
            TunisJobs
            <span className="brand-tag">scrape · match</span>
          </span>
        </div>
        <div className="appbar-meta">
          <span className="badge-sample">Live data</span>
          <span className={`backend-state ${backend.online ? "online" : "offline"}`}>
            {backend.label}
          </span>
        </div>
      </header>

      <div className="layout">
        <Sidebar active={view} onSwitch={switchView} />
        <main className="content" id="content">
          {view === "overview" && (
            <OverviewView
              jobs={jobs}
              sources={SOURCES as Source[]}
              cvLoaded={!!cv}
              onGoScraper={() => switchView("scraper")}
              loading={loadingJobs}
            />
          )}
          {view === "scraper" && (
            <ScraperView
              runState={runState}
              steps={steps}
              progressPct={progress.pct}
              progressLabel={progress.label}
              pipelineSub={pipelineSub}
              logLines={logLines}
              cv={cv}
              cvFile={cvFile}
              cvError={cvError}
              onApplyCv={applyCv}
              onRemoveCv={removeCv}
              onRun={runPipeline}
              onMatch={matchCv}
              matchDisabled={matchDisabled}
              onDownloadJobs={() => downloadExport("jobs")}
            />
          )}
          {view === "matches" && (
            <MatchesView
              matches={matches}
              cvName={cv ? (cv.sample ? SAMPLE_CV_NAME : cv.name) : null}
              jobs={jobs}
              sources={SOURCES as Source[]}
              onGoScraper={() => switchView("scraper")}
              onApply={handleApply}
              onDownloadMatches={() => downloadExport("cv-matches")}
            />
          )}
        </main>
      </div>

      {toast && <Toast message={toast.message} kind={toast.kind} />}
    </div>
  );
}

// Need to import fetch from lib/api
import { fetchJobs, fetchCVMatches, fetchBackendState } from "../lib/api";