"use client";

import { useState } from "react";
import { CircleIcon, DownloadIcon, UploadIcon } from "./icons";
import type { Job, MatchedJob, ScrapeRun, Source } from "../lib/types";
import { companyLine, whyGoodMatch } from "../lib/matches";

function ChevronIcon() {
  return (
    <svg
      className="match-chevron"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={1.5}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d="m6 9 6 6 6-6" />
    </svg>
  );
}

interface MatchesViewProps {
  matches: MatchedJob[];
  cvName: string | null;
  jobs: Job[];
  sources: Source[];
  onGoScraper: () => void;
  onApply: (job: Job) => void;
  appliedIds: Set<number>;
  onToggleApplied: (match: MatchedJob) => void;
  onGenerateCoverLetter: (match: MatchedJob) => Promise<string | null>;
  onDownloadMatches: () => void;
  scrapeRuns: ScrapeRun[];
  selectedScrapeRunId: number | null;
  onSelectScrapeRun: (runId: number) => void;
}

export default function MatchesView({
  matches,
  cvName,
  jobs,
  sources,
  onGoScraper,
  onApply,
  appliedIds,
  onToggleApplied,
  onGenerateCoverLetter,
  onDownloadMatches,
  scrapeRuns,
  selectedScrapeRunId,
  onSelectScrapeRun,
}: MatchesViewProps) {
  const [expanded, setExpanded] = useState<Record<number, boolean>>({});
  const [coverLetters, setCoverLetters] = useState<Record<number, string>>({});
  const [coverLetterLoading, setCoverLetterLoading] = useState<number | null>(null);

  const top = matches[0]?.score ?? 0;
  const strong = matches.filter((m) => m.score >= 60).length;
  const totalSkills = matches.reduce((acc, m) => acc + m.job.skills.length, 0);

  const sourceName = (id: string) =>
    sources.find((s) => s.id === id)?.name ?? id;

  const toggle = (id: number) =>
    setExpanded((prev) => ({ ...prev, [id]: !prev[id] }));

  return (
    <section className="view" id="view-matches" aria-labelledby="mt-title">
      <div className="page-head">
        <div>
          <p className="eyebrow">CV matching</p>
          <h1 className="page-title" id="mt-title">Top matches</h1>
          <p className="page-sub" id="mt-sub">
            {cvName
              ? `Jobs ranked against ${cvName}.`
              : "Sample candidate profile skills compared against every listing."}
          </p>
        </div>
        <label className="od-field" style={{ "--od-gap": "8px" } as React.CSSProperties}>
          <span className="od-nowrap">Scrape result</span>
          <select
            value={selectedScrapeRunId ?? ""}
            onChange={(e) => onSelectScrapeRun(Number(e.target.value))}
            disabled={scrapeRuns.length === 0}
          >
            {scrapeRuns.length === 0 ? (
              <option value="">No completed scrapes</option>
            ) : (
              scrapeRuns.map((run) => (
                <option value={run.id} key={run.id}>
                  {run.source} · {run.completed_at ? new Date(run.completed_at).toLocaleString() : "in progress"}
                </option>
              ))
            )}
          </select>
        </label>
        <div className="od-row" style={{ "--od-gap": "8px" } as React.CSSProperties}>
          <button className="btn btn-secondary" onClick={onGoScraper}>
            <UploadIcon />
            Upload a CV
          </button>
          <button className="btn btn-secondary" onClick={onDownloadMatches}>
            <DownloadIcon />
            Download matches CSV
          </button>
        </div>
      </div>

      <div className="summary-strip" id="match-summary">
        <div className="summary-card">
          <div className="od-stat" style={{ "--od-gap": "2px" } as React.CSSProperties}>
            <span className="stat-num od-nowrap">{top}<small>%</small></span>
            <span className="stat-cap">Best match</span>
            <span className="stat-delta flat">Top-scoring listing</span>
          </div>
        </div>
        <div className="summary-card">
          <div className="od-stat" style={{ "--od-gap": "2px" } as React.CSSProperties}>
            <span className="stat-num od-nowrap">{strong} <small>strong</small></span>
            <span className="stat-cap">Strong matches</span>
            <span className="stat-delta flat">Score 60% or higher</span>
          </div>
        </div>
        <div className="summary-card">
          <div className="od-stat" style={{ "--od-gap": "2px" } as React.CSSProperties}>
            <span className="stat-num od-nowrap">{totalSkills} <small>checked</small></span>
            <span className="stat-cap">Skills scanned</span>
            <span className="stat-delta flat">Across all listings</span>
          </div>
        </div>
      </div>

      <div className="match-list stagger" id="match-list">
        {matches.length === 0 && (
          <div className="empty-state" style={{ gridColumn: "1 / -1" }}>
            <CircleIcon />
            <strong>No matches yet</strong>
            <p>Upload a CV and run the scraper, then check back here.</p>
          </div>
        )}
        {matches.map((m, i) => {
          const open = !!expanded[m.job.id];
          const applied = appliedIds.has(m.job.id);
          const coverLetter = coverLetters[m.job.id] ?? m.coverLetter ?? "";
          return (
            <article
              className={`match-card${open ? " open" : ""}`}
              key={m.job.id}
              data-id={m.job.id}
              role="button"
              tabIndex={0}
              aria-expanded={open}
              aria-label={`${m.job.title} at ${m.job.company} — toggle details`}
              style={{ animationDelay: `${i * 40}ms` }}
              onClick={() => toggle(m.job.id)}
              onKeyDown={(e) => {
                if (e.key === "Enter" || e.key === " ") {
                  e.preventDefault();
                  toggle(m.job.id);
                }
              }}
            >
              <div className="match-top">
                <span className="match-rank">#{i + 1}</span>
                <span className="od-row" style={{ "--od-gap": "10px" } as React.CSSProperties}>
                  <button
                    className={`application-toggle${applied ? " applied" : ""}`}
                    type="button"
                    aria-pressed={applied}
                    onClick={(e) => {
                      e.stopPropagation();
                      onToggleApplied(m);
                    }}
                  >
                    {applied ? "Applied" : "Not yet"}
                  </button>
                  <span className="match-score od-nowrap">
                    {m.score}
                    <small>%</small>
                  </span>
                  <ChevronIcon />
                </span>
              </div>
              <div className="od-stack" style={{ "--od-gap": "2px" } as React.CSSProperties}>
                <h3 className="match-title od-truncate">{m.job.title}</h3>
                <span className="match-comp">
                  {m.job.company} · {m.job.city} · {m.job.contract}
                </span>
              </div>
              <div
                className="score-track"
                role="img"
                aria-label={`Match score ${m.score} percent`}
              >
                <div className="score-fill" style={{ width: `${m.score}%` }} />
              </div>
              <div className="match-tags">
                <span className="tag-note">Covered</span>
                {m.matched.length ? (
                  m.matched.map((s) => (
                    <span className="skill-chip match" key={s}>{s}</span>
                  ))
                ) : (
                  <span className="skill-chip miss">none shared</span>
                )}
              </div>
              {m.missing.length > 0 && (
                <div className="match-tags">
                  <span className="tag-note">Missing</span>
                  {m.missing.map((s) => (
                    <span className="skill-chip miss" key={s}>{s}</span>
                  ))}
                </div>
              )}

              <div className="match-expand" hidden={!open}>
                <div className="od-stack" style={{ "--od-gap": "6px" } as React.CSSProperties}>
                  <span className="match-detail-title">About the role</span>
                  <p className="match-detail-body">{m.job.desc}</p>
                  <span className="match-meta">
                    <span>Posted {m.job.date || "unknown"}</span>
                    <span className="sep-dot">·</span>
                    <span>Scraped {m.job.scrapedAt || "unknown"}</span>
                    <span className="sep-dot">·</span>
                    <span>{m.job.contract}</span>
                    <span className="sep-dot">·</span>
                    <span>{m.job.salary}</span>
                  </span>
                </div>
                <div className="od-stack" style={{ "--od-gap": "6px" } as React.CSSProperties}>
                  <span className="match-detail-title">About {m.job.company}</span>
                  <p className="match-detail-body">
                    {companyLine(jobs, m.job.company)}
                  </p>
                </div>
                <div className="od-stack" style={{ "--od-gap": "6px" } as React.CSSProperties}>
                  <span className="match-detail-title">Why this is a strong match</span>
                  <div className="match-why">{whyGoodMatch(m)}</div>
                </div>
                <div className="od-row" style={{ "--od-gap": "12px" } as React.CSSProperties}>
                  <button
                    className="btn btn-secondary btn-sm"
                    type="button"
                    disabled={coverLetterLoading === m.job.id}
                    onClick={async (e) => {
                      e.stopPropagation();
                      setCoverLetterLoading(m.job.id);
                      const generated = await onGenerateCoverLetter(m);
                      if (generated) setCoverLetters((current) => ({ ...current, [m.job.id]: generated }));
                      setCoverLetterLoading(null);
                    }}
                  >
                    {coverLetterLoading === m.job.id ? "Generating..." : coverLetter ? "Regenerate cover letter" : "Generate cover letter"}
                  </button>
                  {coverLetter && (
                    <button
                      className="btn btn-ghost btn-sm"
                      type="button"
                      onClick={(e) => {
                        e.stopPropagation();
                        navigator.clipboard.writeText(coverLetter);
                      }}
                    >
                      Copy letter
                    </button>
                  )}
                  <button
                    className="btn btn-primary btn-sm match-apply"
                    type="button"
                    onClick={(e) => {
                      e.stopPropagation();
                      onApply(m.job);
                    }}
                  >
                    Apply on {sourceName(m.job.source)}
                  </button>
                </div>
                {coverLetter && <pre className="cover-letter">{coverLetter}</pre>}
              </div>
            </article>
          );
        })}
      </div>
    </section>
  );
}