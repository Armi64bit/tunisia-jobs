"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import OverviewView from "./OverviewView";
import ScraperView from "./ScraperView";
import MatchesView from "./MatchesView";
import ApplicationsView from "./ApplicationsView";
import Sidebar from "./Sidebar";
import Toast from "./Toast";
import { SAMPLE_CV_NAME, SAMPLE_CV_SKILLS, SOURCES } from "../lib/demo-data";
import { skillScore } from "../lib/api";
import { nextLogId, timeNow } from "../lib/format";
import type {
  AppliedJob,
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
  ScrapeRun,
} from "../lib/types";

const PER_SOURCE = [18, 10, 8, 14];

const configuredApiBase = process.env.NEXT_PUBLIC_API_BASE_URL;
const API_BASE = typeof window !== "undefined" &&
  window.location.hostname !== "localhost" &&
  window.location.hostname !== "127.0.0.1" &&
  (!configuredApiBase || configuredApiBase.includes("localhost"))
  ? `${window.location.protocol}//${window.location.hostname}:8001`
  : configuredApiBase ?? "http://localhost:8001";
const LEGACY_APPLICATIONS_STORAGE_KEY = "tunisjobs-applied-jobs";

function sourceName(id: SourceId): string {
  return SOURCES.find((s) => s.id === id)?.name ?? id;
}

function normalizeSource(source: unknown): SourceId {
  const value = String(source ?? "").trim().toLowerCase().replace(/[\s_-]+/g, "");
  if (value.includes("emploi") || value.includes("emploitunisie")) return "emploitunisie";
  if (value.includes("rekrute")) return "rekrute";
  if (value.includes("linkedin")) return "linkedin";
  if (value.includes("apify")) return "apify";
  return "keejob";
}

function normalizeJob(job: any): Job {
  return {
    id: job.id,
    title: job.title ?? "",
    company: job.company ?? "",
    source: normalizeSource(job.source),
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
  const [jobsError, setJobsError] = useState<string | null>(null);
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
  const [pipelineStartedAt, setPipelineStartedAt] = useState<number | null>(null);
  const [pipelineSub, setPipelineSub] = useState("Ready");
  const [logLines, setLogLines] = useState<LogLine[]>([]);
  const [matches, setMatches] = useState<MatchedJob[]>([]);
  const [applications, setApplications] = useState<AppliedJob[]>([]);
  const [loadingMatches, setLoadingMatches] = useState(false);
  const [scrapeRuns, setScrapeRuns] = useState<ScrapeRun[]>([]);
  const [selectedScrapeRunId, setSelectedScrapeRunId] = useState<number | null>(null);

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
    setJobsError(null);
    try {
      const response = await fetch(`${API_BASE}/jobs?limit=200`);
      if (!response.ok) {
        throw new Error(`Backend returned ${response.status}`);
      }
      const data = await response.json();
      if (!Array.isArray(data)) {
        throw new Error("Backend returned an invalid jobs payload");
      }
      setJobs(data.map(normalizeJob));
    } catch (error) {
      setJobs([]);
      setJobsError(error instanceof Error ? error.message : "Could not load jobs");
    } finally {
      setLoadingJobs(false);
    }
  }, []);

  const loadCVMatches = useCallback(async (scrapeRunId?: number) => {
    setLoadingMatches(true);
    try {
      const selected = scrapeRunId ? `&scrape_run_id=${scrapeRunId}` : "";
      const response = await fetch(`${API_BASE}/cv-matches?limit=100${selected}`);
      if (response.ok) {
        const data = await response.json();
        // Convert to MatchedJob format
        const matchedJobs: MatchedJob[] = data.map((job: any) => ({
          matchId: job.match_id,
          job: {
            id: job.id,
            title: job.title,
            company: job.company,
            source: normalizeSource(job.source),
            city: job.location,
            contract: job.contract,
            date: job.posted_at,
            salary: "",
            skills: job.cv_keywords || [],
            desc: job.summary || "",
            scrapedAt: job.scraped_at,
            applyUrl: job.source_url,
          },
          score: job.match_score || 0,
          matched: job.cv_keywords || [],
          missing: job.missing_skills || [],
          coverLetter: job.cover_letter || "",
        }));
        setMatches(matchedJobs);
      }
    } catch (e) {
      console.error("Failed to load CV matches:", e);
    } finally {
      setLoadingMatches(false);
    }
  }, []);

  const loadApplications = useCallback(async () => {
    try {
      const response = await fetch(`${API_BASE}/applications`);
      if (!response.ok) return;
      const data = await response.json();
      const legacy = window.localStorage.getItem(LEGACY_APPLICATIONS_STORAGE_KEY);
      if (legacy) {
        try {
          const oldApplications = JSON.parse(legacy);
          const storedIds = new Set((Array.isArray(data) ? data : []).map((item: any) => item.id));
          if (Array.isArray(oldApplications)) {
            await Promise.all(oldApplications
              .filter((item: any) => !storedIds.has(item.job?.id))
              .map(async (item: any) => {
                const created = await fetch(`${API_BASE}/applications`, {
                  method: "POST",
                  headers: { "Content-Type": "application/json" },
                  body: JSON.stringify({ job_id: item.job?.id, match_id: item.matchId, applied_at: item.appliedAt }),
                });
                if (created.ok && item.replied) {
                  await fetch(`${API_BASE}/applications/${item.job?.id}`, {
                    method: "PATCH",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ replied: true }),
                  });
                }
              }));
          }
          window.localStorage.removeItem(LEGACY_APPLICATIONS_STORAGE_KEY);
          if (oldApplications?.length) {
            const migrated = await fetch(`${API_BASE}/applications`);
            if (migrated.ok) data.splice(0, data.length, ...(await migrated.json()));
          }
        } catch (migrationError) {
          console.error("Failed to migrate legacy applications:", migrationError);
        }
      }
      setApplications(Array.isArray(data) ? data.map((application: any): AppliedJob => ({
        matchId: application.match_id,
        job: {
          id: application.id,
          title: application.title ?? "",
          company: application.company ?? "",
          source: normalizeSource(application.source),
          city: application.location ?? "",
          contract: application.contract ?? "",
          date: application.posted_at ?? "",
          salary: "",
          skills: application.cv_keywords ?? [],
          desc: application.description ?? application.summary ?? "",
          scrapedAt: application.scraped_at,
          applyUrl: application.source_url,
          source_url: application.source_url,
        },
        score: application.match_score ?? 0,
        matched: application.cv_keywords ?? [],
        missing: application.missing_skills ?? [],
          coverLetter: application.cover_letter ?? "",
        appliedAt: application.applied_at,
        replied: Boolean(application.replied),
      })) : []);
    } catch (e) {
      console.error("Failed to load applications:", e);
    }
  }, []);

  const loadScrapeRuns = useCallback(async () => {
    try {
      const response = await fetch(`${API_BASE}/scrape-runs?limit=30`);
      if (!response.ok) return;
      const data: ScrapeRun[] = await response.json();
      setScrapeRuns(data);
      setSelectedScrapeRunId((current) =>
        current && data.some((run) => run.id === current) ? current : data[0]?.id ?? null,
      );
    } catch (e) {
      console.error("Failed to load scrape runs:", e);
    }
  }, []);

  const loadBackendState = useCallback(async () => {
    try {
      const response = await fetch(`${API_BASE}/health`);
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
    loadApplications();
    loadScrapeRuns();
    loadBackendState();
  }, [loadJobs, loadCVMatches, loadApplications, loadScrapeRuns, loadBackendState]);

  const pollPipelineStatus = useCallback(async () => {
    try {
      const response = await fetch(`${API_BASE}/pipeline/status`);
      if (response.ok) {
        const status: PipelineStatus = await response.json();
        
        setRunState(
          status.running
            ? "running"
            : status.stopped
              ? "stopped"
              : status.error
                ? "error"
                : status.completed_at
                  ? "done"
                  : "idle",
        );
        setSteps(convertPipelineSteps(status.steps));
        setProgress({ pct: status.progress, label: status.label });
        setPipelineSub(status.label);
        setLogLines(convertPipelineLogs(status.logs));
        
        if (status.running) {
          statusPollRef.current = window.setTimeout(pollPipelineStatus, 1000);
        } else if (status.stopped) {
          showToast("Pipeline stopped", "ok");
        } else if (status.completed_at && !status.error) {
          showToast("Pipeline completed successfully!", "ok");
          loadJobs();
          loadScrapeRuns();
          loadCVMatches(selectedScrapeRunId ?? undefined);
        } else if (status.error) {
          showToast(`Pipeline failed: ${status.error}`, "err");
        }
      }
    } catch (e) {
      console.error("Failed to poll pipeline status:", e);
    }
  }, [showToast, loadJobs, loadScrapeRuns, loadCVMatches, selectedScrapeRunId]);

  const runPipeline = useCallback(
    async (cvFile: File | null, skipScraping: boolean, matchCv: boolean) => {
      if (runState === "running") return;
      
      setRunState("running");
      setPipelineStartedAt(Date.now());
      setPipelineSub("Starting...");
      setLogLines([]);
      setProgress({ pct: 0, label: "Initializing" });
      setSteps([]);

      const formData = new FormData();
      if (cvFile) formData.append("cv_file", cvFile);
      formData.append("skip_scraping", String(skipScraping));
      formData.append("match_cv", String(matchCv));
      if (matchCv && skipScraping && selectedScrapeRunId !== null) {
        formData.append("scrape_run_id", String(selectedScrapeRunId));
      }

      try {
        const response = await fetch(`${API_BASE}/pipeline/run`, {
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
    [runState, selectedScrapeRunId, showToast, pollPipelineStatus]
  );

  const matchCv = useCallback(() => {
    if (!cvFile || selectedScrapeRunId === null || runState === "running") return;
    setView("scraper");
    runPipeline(cvFile, true, true);
  }, [cvFile, selectedScrapeRunId, runState, runPipeline]);

  const stopPipeline = useCallback(async () => {
    try {
      const response = await fetch(`${API_BASE}/pipeline/stop`, { method: "POST" });
      const result = await response.json();
      if (!response.ok || !result.success) {
        showToast(result.message || "No pipeline is running", "err");
        return;
      }
      showToast("Stopping pipeline...", "ok");
      pollPipelineStatus();
    } catch {
      showToast("Could not stop the pipeline", "err");
    }
  }, [pollPipelineStatus, showToast]);

  const selectScrapeRun = useCallback((runId: number) => {
    setSelectedScrapeRunId(runId);
    loadCVMatches(runId);
  }, [loadCVMatches]);

  const deleteScrapeRun = useCallback(async (runId: number) => {
    if (!window.confirm("Delete this scrape run? Its snapshot will be removed.")) return;
    try {
      const response = await fetch(`${API_BASE}/scrape-runs/${runId}`, { method: "DELETE" });
      if (!response.ok) throw new Error("Delete failed");
      await loadScrapeRuns();
      await loadCVMatches();
      showToast("Scrape run deleted", "ok");
    } catch {
      showToast("Could not delete scrape run", "err");
    }
  }, [loadCVMatches, loadScrapeRuns, showToast]);

  const generateCoverLetter = useCallback(async (match: MatchedJob): Promise<string | null> => {
    const formData = new FormData();
    formData.append("job_id", String(match.job.id));
    if (match.matchId !== undefined) formData.append("match_id", String(match.matchId));
    if (cvFile) formData.append("cv_file", cvFile);
    try {
      const response = await fetch(`${API_BASE}/cover-letters`, { method: "POST", body: formData });
      const result = await response.json();
      if (!response.ok || !result.success) throw new Error(result.detail || "Generation failed");
      await loadApplications();
      showToast("Cover letter generated", "ok");
      return result.cover_letter;
    } catch (error) {
      showToast(error instanceof Error ? error.message : "Could not generate cover letter", "err");
      return null;
    }
  }, [cvFile, loadApplications, showToast]);

  const matchDisabled = !cv || runState === "running";
  const appBusy = loadingJobs || loadingMatches;
  const elapsedSeconds = pipelineStartedAt
    ? Math.max(0, (Date.now() - pipelineStartedAt) / 1000)
    : 0;
  const remainingSeconds = runState === "running" && progress.pct > 0
    ? Math.max(0, elapsedSeconds * (100 - progress.pct) / progress.pct)
    : null;
  const progressEta = remainingSeconds === null
    ? "Estimating time remaining..."
    : remainingSeconds < 60
      ? `About ${Math.ceil(remainingSeconds)} sec remaining`
      : `About ${Math.ceil(remainingSeconds / 60)} min remaining`;

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

  const toggleApplied = useCallback(async (match: MatchedJob) => {
    const existing = applications.some((application) => application.job.id === match.job.id);
    try {
      const response = existing
        ? await fetch(`${API_BASE}/applications/${match.job.id}`, { method: "DELETE" })
        : await fetch(`${API_BASE}/applications`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ job_id: match.job.id, match_id: match.matchId }),
          });
      if (!response.ok) throw new Error("Application request failed");
      await loadApplications();
    } catch {
      showToast("Could not update application tracker", "err");
    }
  }, [applications, loadApplications, showToast]);

  const toggleReplied = useCallback(async (jobId: number) => {
    const application = applications.find((item) => item.job.id === jobId);
    if (!application) return;
    try {
      const response = await fetch(`${API_BASE}/applications/${jobId}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ replied: !application.replied }),
      });
      if (!response.ok) throw new Error("Reply status request failed");
      await loadApplications();
    } catch {
      showToast("Could not update reply status", "err");
    }
  }, [applications, loadApplications, showToast]);

  const removeApplication = useCallback(async (jobId: number) => {
    try {
      const response = await fetch(`${API_BASE}/applications/${jobId}`, { method: "DELETE" });
      if (!response.ok) throw new Error("Application request failed");
      await loadApplications();
    } catch {
      showToast("Could not remove application", "err");
    }
  }, [loadApplications, showToast]);

  const downloadExport = useCallback(async (type: "cv-matches" | "jobs") => {
    try {
      const response = await fetch(`${API_BASE}/export/${type}`);
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
      {appBusy && (
        <div className="loading-veil" role="status" aria-live="polite" aria-label="Loading">
          <div className="loading-card">
            <span className="loading-orbit" aria-hidden="true"><span /></span>
            <span className="loading-label">
              {loadingMatches ? "Loading matches" : "Loading jobs"}
            </span>
          </div>
        </div>
      )}
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
              error={jobsError}
              matches={matches}
              applications={applications}
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
              progressEta={runState === "running" ? progressEta : undefined}
              pipelineSub={pipelineSub}
              logLines={logLines}
              cv={cv}
              cvFile={cvFile}
              cvError={cvError}
              scrapeRuns={scrapeRuns}
              selectedScrapeRunId={selectedScrapeRunId}
              onSelectScrapeRun={selectScrapeRun}
              onApplyCv={applyCv}
              onRemoveCv={removeCv}
              onRun={runPipeline}
              onStop={stopPipeline}
              onDeleteScrapeRun={deleteScrapeRun}
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
              appliedIds={new Set(applications.map((application) => application.job.id))}
              onToggleApplied={toggleApplied}
              onGenerateCoverLetter={generateCoverLetter}
              onDownloadMatches={() => downloadExport("cv-matches")}
              scrapeRuns={scrapeRuns}
              selectedScrapeRunId={selectedScrapeRunId}
              onSelectScrapeRun={selectScrapeRun}
            />
          )}
          {view === "applications" && (
            <ApplicationsView
              applications={applications}
              jobs={jobs}
              sources={SOURCES as Source[]}
              onApply={handleApply}
              onRemove={removeApplication}
              onToggleReplied={toggleReplied}
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