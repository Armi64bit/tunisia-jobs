import { useMemo, useState } from "react";
import { SOURCES, SAMPLE_CV_SKILLS } from "../lib/demo-data";
import { skillScore } from "../lib/api";
import type { Job, Source } from "../lib/types";
import { BoltIcon, SearchIcon } from "./icons";

interface OverviewViewProps {
  jobs: Job[];
  sources: Source[];
  cvLoaded: boolean;
  onGoScraper: () => void;
  loading?: boolean;
}

interface Agg {
  bySource: Record<string, number>;
  byCity: string[];
  byContract: string[];
  companies: Record<string, number>;
}

function aggregate(jobs: Job[]): Agg {
  const bySource: Record<string, number> = {};
  const companies: Record<string, number> = {};
  const byCity: Record<string, number> = {};
  const byContract: Record<string, number> = {};
  jobs.forEach((j) => {
    bySource[j.source] = (bySource[j.source] || 0) + 1;
    companies[j.company] = (companies[j.company] || 0) + 1;
    byCity[j.city] = (byCity[j.city] || 0) + 1;
    byContract[j.contract] = (byContract[j.contract] || 0) + 1;
  });
  return {
    bySource,
    byCity: Object.keys(byCity).sort(),
    byContract: Object.keys(byContract).sort(),
    companies,
  };
}

export default function OverviewView({
  jobs,
  sources,
  cvLoaded,
  onGoScraper,
  loading = false,
}: OverviewViewProps) {
  const [q, setQ] = useState("");
  const [src, setSrc] = useState("all");
  const [city, setCity] = useState("all");
  const [contract, setContract] = useState("all");
  const [expanded, setExpanded] = useState<Record<number, boolean>>({});

  const agg = useMemo(() => aggregate(jobs), [jobs]);

  const stats = useMemo(() => {
    const total = jobs.length;
    const topCompany =
      Object.keys(agg.companies).sort(
        (x, y) => agg.companies[y] - agg.companies[x],
      )[0] || "—";
    const avgSkills = Math.round(
      jobs.reduce((acc, j) => acc + j.skills.length, 0) / Math.max(1, total),
    );
    return { total, topCompany, avgSkills };
  }, [jobs, agg]);

  const maxSource = useMemo(
    () =>
      sources.reduce((max, s) => Math.max(max, agg.bySource[s.id] || 0), 0),
    [sources, agg],
  );

  const companies = useMemo(
    () =>
      Object.keys(agg.companies)
        .map((name) => ({ name, n: agg.companies[name] }))
        .sort((a, b) => b.n - a.n)
        .slice(0, 5),
    [agg],
  );

  const filtered = useMemo(() => {
    const query = q.trim().toLowerCase();
    return jobs.filter((j) => {
      const matchQ =
        !query ||
        j.title.toLowerCase().includes(query) ||
        j.company.toLowerCase().includes(query) ||
        j.desc.toLowerCase().includes(query) ||
        j.skills.some((s) => s.toLowerCase().includes(query));
      return (
        matchQ &&
        (src === "all" || j.source === src) &&
        (city === "all" || j.city === city) &&
        (contract === "all" || j.contract === contract)
      );
    });
  }, [jobs, q, src, city, contract]);

  const sourceName = (id: string) =>
    sources.find((s) => s.id === id)?.name ?? id;

  const initials = (name: string) =>
    name
      .split(/\s+/)
      .map((w) => w[0])
      .join("")
      .slice(0, 2)
      .toUpperCase();

  return (
    <section className="view" id="view-overview" aria-labelledby="ov-title">
      <div className="page-head">
        <div>
          <p className="eyebrow">Market overview</p>
          <h1 className="page-title" id="ov-title">Scraped jobs</h1>
          <p className="page-sub">
            Live view of job listings collected across four Tunisian boards,
            with skill and company intelligence.
          </p>
        </div>
        <button className="btn btn-primary" onClick={onGoScraper}>
          <BoltIcon />
          Run a scrape
        </button>
      </div>

      <div className="stat-grid">
        <div className="stat-card">
          <div className="od-stat" style={{ "--od-gap": "2px" } as React.CSSProperties}>
            <span className="stat-num od-nowrap">{stats.total} <small>jobs</small></span>
            <span className="stat-cap">Listings collected</span>
            <span className="stat-delta flat">Across all boards</span>
          </div>
        </div>
        <div className="stat-card">
          <div className="od-stat" style={{ "--od-gap": "2px" } as React.CSSProperties}>
            <span className="stat-num od-nowrap">{sources.length} <small>sources</small></span>
            <span className="stat-cap">Boards active</span>
            <span className="stat-delta flat">keejob · rekrute · plus</span>
          </div>
        </div>
        <div className="stat-card">
          <div className="od-stat" style={{ "--od-gap": "2px" } as React.CSSProperties}>
            <span className="stat-num od-nowrap">{stats.avgSkills} <small>avg</small></span>
            <span className="stat-cap">Skills per listing</span>
            <span className="stat-delta flat">From parsed postings</span>
          </div>
        </div>
        <div className="stat-card">
          <div className="od-stat" style={{ "--od-gap": "2px" } as React.CSSProperties}>
            <span className="stat-num od-nowrap od-truncate">{stats.topCompany}</span>
            <span className="stat-cap">Top employer</span>
            <span className="stat-delta flat">By postings count</span>
          </div>
        </div>
      </div>

      <div className="mp-grid">
        <article className="panel section-block">
          <div className="panel-head">
            <div>
              <h2 className="panel-title">Jobs by source</h2>
              <p className="panel-sub">Distribution across boards</p>
            </div>
          </div>
          <div className="bar-list">
            {sources.map((s) => {
              const n = agg.bySource[s.id] || 0;
              const w = maxSource ? Math.round((n / maxSource) * 100) : 0;
              return (
                <div className="bar-row" key={s.id}>
                  <span className="bar-label">{s.name}</span>
                  <div className="bar-track">
                    <div className="bar-fill" style={{ width: `${w}%` }} />
                  </div>
                  <span className="bar-val">{n}</span>
                </div>
              );
            })}
          </div>
        </article>

        <article className="panel section-block">
          <div className="panel-head">
            <div>
              <h2 className="panel-title">Top employers</h2>
              <p className="panel-sub">Postings per company</p>
            </div>
          </div>
          <div className="comp-list">
            {companies.map((r) => (
              <div className="comp-row" style={{ minWidth: 0 }} key={r.name}>
                <span className="avatar-row od-fill">
                  <span className="avatar">{initials(r.name)}</span>
                  <span className="comp-name od-truncate od-fill">{r.name}</span>
                </span>
                <span className="comp-count">{r.n}</span>
              </div>
            ))}
          </div>
        </article>
      </div>

      <article className="panel">
        <div className="panel-head">
          <div>
            <h2 className="panel-title">Job listings</h2>
            <p className="panel-sub" id="jobs-sub">
              {jobs.length} active postings
            </p>
          </div>
          {loading && (
            <span className="badge-sample" style={{ fontSize: "var(--text-xs)" }}>
              Loading…
            </span>
          )}
        </div>
        <form
          className="toolbar"
          role="search"
          aria-label="Filter jobs"
          onSubmit={(e) => e.preventDefault()}
        >
          <div className="field search-wrap">
            <label className="field-label" htmlFor="f-q">Search</label>
            <SearchIcon />
            <input
              className="input"
              id="f-q"
              type="search"
              placeholder="Title, company, skill…"
              autoComplete="off"
              value={q}
              onChange={(e) => setQ(e.target.value)}
            />
          </div>
          <div className="field">
            <label className="field-label" htmlFor="f-src">Source</label>
            <select
              className="input"
              id="f-src"
              value={src}
              onChange={(e) => setSrc(e.target.value)}
            >
              <option value="all">All sources</option>
              {Object.keys(agg.bySource).map((id) => (
                <option key={id} value={id}>{sourceName(id)}</option>
              ))}
            </select>
          </div>
          <div className="field">
            <label className="field-label" htmlFor="f-city">City</label>
            <select
              className="input"
              id="f-city"
              value={city}
              onChange={(e) => setCity(e.target.value)}
            >
              <option value="all">All cities</option>
              {agg.byCity.map((c) => (
                <option key={c} value={c}>{c}</option>
              ))}
            </select>
          </div>
          <div className="field">
            <label className="field-label" htmlFor="f-contract">Contract</label>
            <select
              className="input"
              id="f-contract"
              value={contract}
              onChange={(e) => setContract(e.target.value)}
            >
              <option value="all">All contracts</option>
              {agg.byContract.map((c) => (
                <option key={c} value={c}>{c}</option>
              ))}
            </select>
          </div>
          <div className="result-count" aria-live="polite">
            <strong>{filtered.length}</strong> shown
          </div>
        </form>

        <div className="job-list" id="job-list">
          {filtered.length === 0 && (
            <div className="empty-state">
              <SearchIcon />
              <strong>No listings match</strong>
              <p>Try clearing a filter or widening the search, then run a fresh scrape.</p>
            </div>
          )}
          {filtered.map((j) => {
            const score = skillScore(j);
            const open = !!expanded[j.id];
            return (
              <div className="job-row" data-id={j.id} key={j.id}>
                <button
                  className="job-main"
                  role="button"
                  aria-expanded={open}
                  aria-label={`${j.title} at ${j.company}`}
                  onClick={() =>
                    setExpanded((prev) => ({ ...prev, [j.id]: !prev[j.id] }))
                  }
                >
                  <span className="od-stack" style={{ "--od-gap": "2px", minWidth: 0 } as React.CSSProperties}>
                    <span className="job-title od-truncate">{j.title}</span>
                    <span className="job-meta">
                      <span className="job-comp">{j.company}</span>
                      <span className="sep">·</span>
                      <span className="od-truncate">{j.city}</span>
                    </span>
                  </span>
                  <span className="job-contract od-nowrap">{j.contract}</span>
                  <span className="job-salary od-nowrap">{j.salary}</span>
                  <span className="chip-source od-nowrap">{sourceName(j.source)}</span>
                </button>
                {open && (
                  <div className="job-expand">
                    <p className="job-desc">{j.desc}</p>
                    <div className="od-cluster" style={{ "--od-gap": "8px" } as React.CSSProperties}>
                      <span className="tag-note">Skills</span>
                      {j.skills.map((s) => {
                        const hit = SAMPLE_CV_SKILLS.includes(s);
                        return (
                          <span className={`skill-chip${hit ? " match" : ""}`} key={s}>
                            {s}
                            {cvLoaded ? (hit ? " ✓" : " —") : ""}
                          </span>
                        );
                      })}
                      {score > 0 && (
                        <span className="tag-note">Match {score}%</span>
                      )}
                    </div>
                    <span className="job-date">Posted {j.date} ago</span>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </article>
    </section>
  );
}