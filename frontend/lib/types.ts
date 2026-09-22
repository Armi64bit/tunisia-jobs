export type SourceId = "keejob" | "rekrute" | "emploitunisie" | "linkedin";

export interface Source {
  id: SourceId;
  name: string;
}

export interface Job {
  id: number;
  title: string;
  company: string;
  source: SourceId;
  city: string;
  contract: string;
  date: string;
  salary: string;
  skills: string[];
  desc: string;
  scrapedAt?: string;
  applyUrl?: string;
  source_url?: string;
}

export interface CvInfo {
  name: string;
  size: number;
  sample: boolean;
}

export interface MatchedJob {
  job: Job;
  score: number;
  matched: string[];
  missing: string[];
}

export type StepStatus = "ready" | "running" | "done" | "error";

export interface RunStep {
  id: SourceId;
  name: string;
  status: StepStatus;
  found: number;
}

export type RunState = "idle" | "running" | "done" | "error";

export type LogKind = "act" | "ok" | "err" | "";

export interface LogLine {
  id: number;
  t: string;
  text: string;
  kind: LogKind;
}

export type ViewId = "overview" | "scraper" | "matches";

export interface BackendState {
  online: boolean;
  label: string;
}

// Backend pipeline types
export interface PipelineStep {
  id: string;
  name: string;
  status: StepStatus;
  found: number;
}

export interface PipelineLog {
  id: number;
  t: string;
  text: string;
  kind: LogKind;
}

export interface PipelineStatus {
  running: boolean;
  progress: number;
  label: string;
  steps: PipelineStep[];
  logs: PipelineLog[];
  started_at: string | null;
  completed_at: string | null;
  error: string | null;
  cv_path: string | null;
}

export interface ScrapeRun {
  id: number;
  source: string;
  started_at: string | null;
  completed_at: string | null;
  jobs_found: number;
  jobs_new: number;
  status: string;
}