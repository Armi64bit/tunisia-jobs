"use client";

import { useState } from "react";
import { CheckBadgeIcon, CircleIcon } from "./icons";
import type { AppliedJob, Job, Source } from "../lib/types";
import { companyLine, whyGoodMatch } from "../lib/matches";

interface ApplicationsViewProps {
  applications: AppliedJob[];
  jobs: Job[];
  sources: Source[];
  onApply: (job: Job) => void;
  onRemove: (jobId: number) => void;
  onToggleReplied: (jobId: number) => void;
}

export default function ApplicationsView({
  applications,
  jobs,
  sources,
  onApply,
  onRemove,
  onToggleReplied,
}: ApplicationsViewProps) {
  const [expanded, setExpanded] = useState<Record<number, boolean>>({});
  const sourceName = (id: string) => sources.find((source) => source.id === id)?.name ?? id;
  const repliedCount = applications.filter((application) => application.replied).length;
  const waitingCount = applications.length - repliedCount;
  const averageScore = applications.length
    ? Math.round(applications.reduce((total, application) => total + application.score, 0) / applications.length)
    : 0;

  return (
    <section className="view" id="view-applications" aria-labelledby="applications-title">
      <div className="page-head">
        <div>
          <p className="eyebrow">Application tracker</p>
          <h1 className="page-title" id="applications-title">Job offers</h1>
          <p className="page-sub">
            A quick view of your applications, responses, and follow-up queue.
          </p>
        </div>
      </div>

      <div className="application-dashboard" aria-label="Application summary">
        <div className="application-stat">
          <span className="application-stat-value">{applications.length}</span>
          <span className="application-stat-label">Applied</span>
          <span className="application-stat-note">Tracked offers</span>
        </div>
        <div className="application-stat waiting">
          <span className="application-stat-value">{waitingCount}</span>
          <span className="application-stat-label">Awaiting reply</span>
          <span className="application-stat-note">Follow-up queue</span>
        </div>
        <div className="application-stat replied">
          <span className="application-stat-value">{repliedCount}</span>
          <span className="application-stat-label">Replied</span>
          <span className="application-stat-note">Responses received</span>
        </div>
        <div className="application-stat score">
          <span className="application-stat-value">{averageScore}<small>%</small></span>
          <span className="application-stat-label">Average match</span>
          <span className="application-stat-note">Across tracked offers</span>
        </div>
      </div>

      <div className="application-section-head">
        <div>
          <p className="eyebrow">Tracked offers</p>
          <h2 className="application-section-title">Your applications</h2>
        </div>
        <span className="application-section-count">{applications.length} total</span>
      </div>

      <div className="application-list stagger">
        {applications.length === 0 ? (
          <div className="empty-state">
            <CircleIcon />
            <strong>No applications tracked yet</strong>
            <p>Use the red Not yet toggle on a CV match after you apply.</p>
          </div>
        ) : (
          applications.map((application) => (
            <article
              className={`application-card${expanded[application.job.id] ? " open" : ""}`}
              key={application.job.id}
              onClick={() => setExpanded((current) => ({
                ...current,
                [application.job.id]: !current[application.job.id],
              }))}
            >
              <div className="application-card-head">
                <div className="od-stack" style={{ "--od-gap": "4px" } as React.CSSProperties}>
                  <span className="application-source">{sourceName(application.job.source)}</span>
                  <h2 className="application-title">{application.job.title}</h2>
                  <span className="match-comp">
                    {application.job.company} · {application.job.city} · {application.job.contract}
                  </span>
                </div>
                <div className="application-card-status">
                  <CheckBadgeIcon className="application-check" />
                  <span className="application-chevron" aria-hidden="true">⌄</span>
                </div>
              </div>
              <div className="application-meta">
                <span>Applied {new Date(application.appliedAt).toLocaleString()}</span>
                <span>Match {application.score}%</span>
                <span>{application.job.date ? `Posted ${application.job.date}` : "Posted date unknown"}</span>
              </div>
              <button
                className={`reply-toggle${application.replied ? " replied" : ""}`}
                type="button"
                aria-pressed={application.replied}
                onClick={(event) => {
                  event.stopPropagation();
                  onToggleReplied(application.job.id);
                }}
              >
                <span className="reply-dot" aria-hidden="true" />
                {application.replied ? "Replied" : "Waiting for reply"}
              </button>
              <div className="application-expand" hidden={!expanded[application.job.id]}>
                <div className="od-stack" style={{ "--od-gap": "6px" } as React.CSSProperties}>
                  <span className="match-detail-title">About the role</span>
                  <p className="application-description">
                    {application.job.desc || companyLine(jobs, application.job.company)}
                  </p>
                  <span className="match-meta">
                    <span>CV match #{application.matchId ?? "unknown"}</span>
                    <span className="sep-dot">·</span>
                    <span>Posted {application.job.date || "unknown"}</span>
                    <span className="sep-dot">·</span>
                    <span>Applied {new Date(application.appliedAt).toLocaleString()}</span>
                  </span>
                </div>
                <div className="match-tags">
                  <span className="tag-note">Covered</span>
                  {application.matched.length ? application.matched.map((skill) => (
                    <span className="skill-chip match" key={skill}>{skill}</span>
                  )) : <span className="skill-chip miss">none shared</span>}
                </div>
                {application.missing.length > 0 && (
                  <div className="match-tags">
                    <span className="tag-note">Missing</span>
                    {application.missing.map((skill) => (
                      <span className="skill-chip miss" key={skill}>{skill}</span>
                    ))}
                  </div>
                )}
                <div className="od-stack" style={{ "--od-gap": "6px" } as React.CSSProperties}>
                  <span className="match-detail-title">Why this is a strong match</span>
                  <div className="match-why">{whyGoodMatch(application)}</div>
                </div>
                {application.coverLetter && (
                  <div className="od-stack" style={{ "--od-gap": "8px" } as React.CSSProperties}>
                    <div className="od-row" style={{ "--od-gap": "12px" } as React.CSSProperties}>
                      <span className="match-detail-title">Cover letter</span>
                      <button
                        className="btn btn-ghost btn-sm"
                        type="button"
                        onClick={(event) => {
                          event.stopPropagation();
                          navigator.clipboard.writeText(application.coverLetter || "");
                        }}
                      >
                        Copy letter
                      </button>
                    </div>
                    <pre className="cover-letter">{application.coverLetter}</pre>
                  </div>
                )}
                <div className="od-row application-actions" style={{ "--od-gap": "12px" } as React.CSSProperties}>
                  <button className="btn btn-primary btn-sm" type="button" onClick={(event) => {
                    event.stopPropagation();
                    onApply(application.job);
                  }}>
                    Open listing
                  </button>
                  <button className="btn btn-secondary btn-sm" type="button" onClick={(event) => {
                    event.stopPropagation();
                    onRemove(application.job.id);
                  }}>
                    Mark not applied
                  </button>
                </div>
              </div>
            </article>
          ))
        )}
      </div>
    </section>
  );
}