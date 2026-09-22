"use client";

import { useEffect, useRef, useState } from "react";
import { fmtKB } from "../lib/format";
import type { CvInfo, LogLine, RunState, RunStep } from "../lib/types";
import {
  AlertIcon,
  CheckIcon,
  CircleIcon,
  DownloadIcon,
  FileIcon,
  PlayIcon,
  SpinnerIcon,
  TargetIcon,
  UploadIcon,
  XIcon,
} from "./icons";

interface ScraperViewProps {
  runState: RunState;
  steps: RunStep[];
  progressPct: number;
  progressLabel: string;
  pipelineSub: string;
  logLines: LogLine[];
  cv: CvInfo | null;
  cvError: string | null;
  onApplyCv: (file: File) => void;
  onRemoveCv: () => void;
  onRun: (cvFile: File | null, skipScraping: boolean, matchCv: boolean) => void;
  onMatch: () => void;
  matchDisabled: boolean;
  onDownloadJobs: () => void;
}

function stepIcon(status: RunStep["status"], key: number) {
  if (status === "done") return <CheckIcon className="step-icon done" key={key} />;
  if (status === "running") return <SpinnerIcon className="step-icon running" key={key} />;
  if (status === "error") return <AlertIcon className="step-icon error" key={key} />;
  return <CircleIcon className="step-icon" key={key} />;
}

export default function ScraperView({
  runState,
  steps,
  progressPct,
  progressLabel,
  pipelineSub,
  logLines,
  cv,
  cvError,
  onApplyCv,
  onRemoveCv,
  onRun,
  onMatch,
  matchDisabled,
  onDownloadJobs,
}: ScraperViewProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const logRef = useRef<HTMLDivElement>(null);
  const [drag, setDrag] = useState(false);
  const [cvFile, setCvFile] = useState<File | null>(null);
  const [skipScraping, setSkipScraping] = useState(false);
  const [matchCv, setMatchCv] = useState(false);
  const running = runState === "running";

  useEffect(() => {
    if (logRef.current) {
      logRef.current.scrollTop = logRef.current.scrollHeight;
    }
  }, [logLines]);

  const handleRun = () => {
    onRun(cvFile, skipScraping, matchCv);
  };

  return (
    <section className="view" id="view-scraper" aria-labelledby="sc-title">
      <div className="page-head">
        <div>
          <p className="eyebrow">Pipeline control</p>
          <h1 className="page-title" id="sc-title">Scraper run</h1>
          <p className="page-sub">
            Drop a CV to enable matching, then launch the pipeline and watch each
            source live.
          </p>
        </div>
      </div>

      <div className="scraper-grid section-block">
        <article className="panel">
          <div className="panel-head">
            <div>
              <h2 className="panel-title">CV upload</h2>
              <p className="panel-sub">PDF required for matching</p>
            </div>
          </div>
          <div className="od-stack" style={{ "--od-gap": "12px", padding: "var(--space-5)" } as React.CSSProperties}>
            <div
              className={`dropzone${drag ? " drag" : ""}`}
              tabIndex={0}
              role="button"
              aria-label="Upload CV PDF"
              onClick={() => inputRef.current?.click()}
              onKeyDown={(e) => {
                if (e.key === "Enter" || e.key === " ") {
                  e.preventDefault();
                  inputRef.current?.click();
                }
              }}
              onDragEnter={(e) => {
                e.preventDefault();
                setDrag(true);
              }}
              onDragOver={(e) => {
                e.preventDefault();
                setDrag(true);
              }}
              onDragLeave={(e) => {
                e.preventDefault();
                setDrag(false);
              }}
              onDrop={(e) => {
                e.preventDefault();
                setDrag(false);
                if (e.dataTransfer.files && e.dataTransfer.files[0]) {
                  const f = e.dataTransfer.files[0];
                  setCvFile(f);
                  onApplyCv(f);
                }
              }}
            >
              <UploadIcon />
              <span className="dz-title" id="dz-title">Drop your CV here</span>
              <span className="dz-sub">PDF up to 10 MB — or click to browse</span>
            </div>
            <input
              ref={inputRef}
              type="file"
              accept="application/pdf,.pdf"
              hidden
              onChange={(e) => {
                const f = e.target.files && e.target.files[0];
                if (f) {
                  setCvFile(f);
                  onApplyCv(f);
                }
                e.target.value = "";
              }}
            />

            {cv && (
              <div className="file-chip" id="file-chip">
                <FileIcon />
                <span className="od-stack" style={{ "--od-gap": "0" } as React.CSSProperties}>
                  <span className="file-name od-truncate">{cv.name}</span>
                  <span className="file-size">{fmtKB(cv.size)}</span>
                </span>
                <button
                  className="file-remove"
                  type="button"
                  aria-label="Remove CV"
                  onClick={() => {
                    setCvFile(null);
                    onRemoveCv();
                  }}
                >
                  <XIcon />
                </button>
              </div>
            )}

            {cvError && (
              <p className="err-text" role="alert">
                <AlertIcon />
                {cvError}
              </p>
            )}

            <div className="od-row" style={{ "--od-gap": "12px" } as React.CSSProperties}>
              <button className="btn btn-primary" id="btn-make-matches" disabled={matchDisabled} onClick={onMatch}>
                <TargetIcon />
                Match my CV
              </button>
              <span className="od-fill od-field" style={{ "--od-gap": "2px" } as React.CSSProperties}>
                <span
                  className="od-truncate"
                  style={{ color: "var(--muted)", fontSize: "var(--text-xs)" }}
                  id="cv-hint"
                >
                  {cv
                    ? "CV loaded — ready to match"
                    : "No CV loaded — matches use the sample profile"}
                </span>
              </span>
            </div>

            <div className="od-stack" style={{ "--od-gap": "8px" } as React.CSSProperties}>
              <label className="od-field" style={{ "--od-gap": "8px" } as React.CSSProperties}>
                <input
                  type="checkbox"
                  checked={skipScraping}
                  onChange={(e) => setSkipScraping(e.target.checked)}
                />
                <span className="od-truncate">Skip scraping (use existing DB)</span>
              </label>
              {cv && (
                <label className="od-field" style={{ "--od-gap": "8px" } as React.CSSProperties}>
                  <input
                    type="checkbox"
                    checked={matchCv}
                    onChange={(e) => setMatchCv(e.target.checked)}
                    disabled={!cv}
                  />
                  <span className="od-truncate">Match CV after scraping</span>
                </label>
              )}
            </div>
          </div>
        </article>

        <article className="panel">
          <div className="panel-head">
            <div>
              <h2 className="panel-title">Pipeline</h2>
              <p className="panel-sub" id="pipeline-sub">{pipelineSub}</p>
            </div>
            <div className="od-row" style={{ "--od-gap": "8px" } as React.CSSProperties}>
              <button
                className="btn btn-primary"
                id="btn-run"
                disabled={running}
                onClick={handleRun}
              >
                <PlayIcon />
                {runState === "done" || runState === "error" ? "Run again" : "Start scrape"}
              </button>
              <button
                className="btn btn-secondary"
                id="btn-download-jobs"
                onClick={onDownloadJobs}
                disabled={runState === "running"}
              >
                <DownloadIcon />
                Download jobs CSV
              </button>
            </div>
          </div>
          <div className="step-list" id="step-list">
            {steps.length === 0 && (
              <div className="empty-state">
                <TargetIcon />
                <strong>Pipeline ready</strong>
                <p>Press "Start scrape" to pull every board and update the dataset live.</p>
              </div>
            )}
            {steps.map((s, i) => (
              <div className="step-row" key={s.id}>
                {stepIcon(s.status, i)}
                <span className="od-stack" style={{ "--od-gap": "0" } as React.CSSProperties}>
                  <span className="step-name">{s.name}</span>
                  <span className="step-count">{s.found ? `${s.found} found` : "—"}</span>
                </span>
                <span className={`step-state ${s.status}`}>{s.status}</span>
              </div>
            ))}
          </div>
          <div className="progress-wrap">
            <div className="progress-head">
              <span className="progress-label" id="progress-label">{progressLabel}</span>
              <span className="progress-pct" id="progress-pct">{Math.round(progressPct)}%</span>
            </div>
            <div className="progress-track">
              <div
                className="progress-fill"
                id="progress-fill"
                role="progressbar"
                aria-valuemin={0}
                aria-valuemax={100}
                aria-valuenow={Math.round(progressPct)}
                style={{ width: `${progressPct}%` }}
              />
            </div>
          </div>
        </article>
      </div>

      <article className="panel">
        <div className="panel-head">
          <div>
            <h2 className="panel-title">Run log</h2>
            <p className="panel-sub">Last session</p>
          </div>
        </div>
        <div className="log-body log-panel" id="log-body" aria-live="polite" ref={logRef}>
          {logLines.length === 0 && (
            <div className="log-line act" key="boot">
              <span className="t">—</span>
              <span>Idle. Start a scrape to begin.</span>
            </div>
          )}
          {logLines.map((line) => (
            <div className={`log-line ${line.kind}`} key={line.id}>
              <span className="t">{line.t}</span>
              <span>{line.text}</span>
            </div>
          ))}
        </div>
      </article>
    </section>
  );
}