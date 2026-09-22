import { JOBS, SOURCES, SAMPLE_CV_SKILLS } from "./demo-data";
import type { BackendState, Job, Source } from "./types";

const isServer = typeof window === "undefined";
const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8001";
const PROXY_BASE = isServer ? API_BASE : "/api/proxy";

export function getApiBaseUrl(): string {
  return API_BASE;
}

export function backendConfigured(): boolean {
  return true;
}

async function safeGet<T>(path: string): Promise<T | null> {
  try {
    const res = await fetch(`${PROXY_BASE}${path}`, {
      headers: { Accept: "application/json" },
    });
    if (!res.ok) return null;
    return (await res.json()) as T;
  } catch {
    return null;
  }
}

async function safePost<T>(path: string, body: FormData | object): Promise<T | null> {
  try {
    const options: RequestInit = {
      method: "POST",
      headers: body instanceof FormData ? {} : { "Content-Type": "application/json" },
      body: body instanceof FormData ? body : JSON.stringify(body),
    };
    const res = await fetch(`${PROXY_BASE}${path}`, options);
    if (!res.ok) return null;
    return (await res.json()) as T;
  } catch {
    return null;
  }
}

export async function fetchJobs(): Promise<{ jobs: Job[]; demo: boolean }> {
  const data = await safeGet<Job[]>("/jobs?limit=200");
  if (data && Array.isArray(data)) return { jobs: data, demo: false };
  return { jobs: JOBS.slice(), demo: true };
}

export async function fetchSources(): Promise<{ sources: Source[]; demo: boolean }> {
  const data = await safeGet<Source[]>("/sources");
  if (data && Array.isArray(data)) return { sources: data, demo: false };
  return { sources: SOURCES, demo: true };
}

export async function fetchCVMatches(): Promise<{ matches: Job[]; demo: boolean }> {
  const data = await safeGet<Job[]>("/cv-matches?limit=100");
  if (data && Array.isArray(data)) return { matches: data, demo: false };
  return { matches: [], demo: true };
}

export async function fetchBackendState(): Promise<BackendState> {
  const data = await safeGet<BackendState>("/health");
  return data
    ? { online: true, label: "Backend: live" }
    : { online: false, label: "Backend: offline" };
}

export function skillScore(job: Job, skills: string[] = SAMPLE_CV_SKILLS): number {
  if (!job.skills?.length) return 0;
  const hit = job.skills.filter((s) => skills.includes(s)).length;
  return Math.round((hit / job.skills.length) * 100);
}

export interface PipelineStep {
  id: string;
  name: string;
  status: "ready" | "running" | "done" | "error";
  found: number;
}

export interface PipelineLog {
  id: number;
  t: string;
  text: string;
  kind: "act" | "ok" | "err" | "";
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

export async function fetchPipelineStatus(): Promise<PipelineStatus | null> {
  return safeGet<PipelineStatus>("/pipeline/status");
}

export async function startPipeline(
  cvFile: File | null,
  skipScraping: boolean,
  matchCv: boolean
): Promise<{ success: boolean; message: string; cv_path?: string } | null> {
  const formData = new FormData();
  if (cvFile) {
    formData.append("cv_file", cvFile);
  }
  formData.append("skip_scraping", String(skipScraping));
  formData.append("match_cv", String(matchCv));
  return safePost<{ success: boolean; message: string; cv_path?: string }>("/pipeline/run", formData);
}

export async function downloadExport(type: "cv-matches" | "jobs"): Promise<Blob | null> {
  try {
    const res = await fetch(`${PROXY_BASE}/export/${type}`);
    if (!res.ok) return null;
    return await res.blob();
  } catch {
    return null;
  }
}