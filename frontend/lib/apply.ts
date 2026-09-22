import type { Job, SourceId } from "./types";

export interface ApplyLink {
  url: string;
  kind: "posting" | "search";
}

const BOARD_SEARCH: Record<SourceId, (q: string) => string> = {
  keejob: (q) =>
    `https://www.keejob.com/offres-emploi/?keywords=${encodeURIComponent(q)}&page=1`,
  rekrute: (q) =>
    `https://www.rekrute.com/offres.html?query=${encodeURIComponent(q)}&keyword=${encodeURIComponent(q)}`,
  emploitunisie: () => "https://www.emploitunisie.com/recherche-jobs-tunisie",
  linkedin: (q) =>
    `https://www.linkedin.com/jobs/search/?keywords=${encodeURIComponent(q)}&location=Tunisia&geoId=103384667`,
};

export function resolveApply(job: Job): ApplyLink {
  if (job.applyUrl && job.applyUrl.trim()) {
    return { url: job.applyUrl, kind: "posting" };
  }
  const search = BOARD_SEARCH[job.source] ?? BOARD_SEARCH.keejob;
  return { url: search(job.title), kind: "search" };
}