-- schema.sql
CREATE TABLE sectors (
    id          SERIAL PRIMARY KEY,
    name        VARCHAR(120) NOT NULL UNIQUE,
    parent_id   INT REFERENCES sectors(id)
);
 
CREATE TABLE companies (
    id          SERIAL PRIMARY KEY,
    name        VARCHAR(200) NOT NULL,
    size        VARCHAR(50),
    sector_id   INT REFERENCES sectors(id),
    website     VARCHAR(300),
    UNIQUE(name)
);
 
CREATE TABLE jobs (
    id          SERIAL PRIMARY KEY,
    title       VARCHAR(300) NOT NULL,
    company_id  INT REFERENCES companies(id),
    sector_id   INT REFERENCES sectors(id),
    location    VARCHAR(120),
    contract    VARCHAR(60),   -- CDI, CDD, Stage, Freelance
    experience  VARCHAR(60),
    description TEXT,
    source      VARCHAR(40) NOT NULL,  -- linkedin|emploi_tn|tanitjobs|rekrute
    source_url  VARCHAR(500),
    posted_at   DATE,
    scraped_at  TIMESTAMP DEFAULT NOW(),
    is_active   BOOLEAN DEFAULT TRUE
);
 
CREATE TABLE skills (
    id              SERIAL PRIMARY KEY,
    name            VARCHAR(120) NOT NULL,
    normalized_name VARCHAR(120) NOT NULL UNIQUE,
    category        VARCHAR(60)  -- frontend|backend|data|devops|mobile|soft
);
 
CREATE TABLE job_skills (
    job_id      INT REFERENCES jobs(id) ON DELETE CASCADE,
    skill_id    INT REFERENCES skills(id),
    is_required BOOLEAN DEFAULT TRUE,
    PRIMARY KEY (job_id, skill_id)
);
 
CREATE TABLE salaries (
    id          SERIAL PRIMARY KEY,
    job_id      INT REFERENCES jobs(id) ON DELETE CASCADE,
    min_tnd     NUMERIC(10,2),
    max_tnd     NUMERIC(10,2),
    currency    VARCHAR(10) DEFAULT 'TND',
    period      VARCHAR(20) DEFAULT 'monthly'
);
 
CREATE TABLE scrape_logs (
    id          SERIAL PRIMARY KEY,
    source      VARCHAR(40) NOT NULL,
    run_at      TIMESTAMP DEFAULT NOW(),
    jobs_found  INT DEFAULT 0,
    jobs_new    INT DEFAULT 0,
    status      VARCHAR(20) DEFAULT 'success',
    error_msg   TEXT
);

CREATE TABLE scrape_runs (
    id           SERIAL PRIMARY KEY,
    source       VARCHAR(40) NOT NULL,
    started_at   TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP,
    jobs_found   INT DEFAULT 0,
    jobs_new     INT DEFAULT 0,
    status       VARCHAR(20) DEFAULT 'running',
    error_msg    TEXT
);

CREATE TABLE scrape_run_jobs (
    run_id       INT REFERENCES scrape_runs(id) ON DELETE CASCADE,
    job_id       INT REFERENCES jobs(id) ON DELETE CASCADE,
    PRIMARY KEY (run_id, job_id)
);

CREATE TABLE job_applications (
    job_id      INT PRIMARY KEY REFERENCES jobs(id) ON DELETE CASCADE,
    match_id    INT,
    applied_at  TIMESTAMP NOT NULL DEFAULT NOW(),
    replied     BOOLEAN NOT NULL DEFAULT FALSE
);
 
-- Useful indexes
CREATE INDEX idx_jobs_source    ON jobs(source);
CREATE INDEX idx_jobs_posted_at ON jobs(posted_at);
CREATE INDEX idx_jobs_sector    ON jobs(sector_id);
CREATE INDEX idx_job_skills_job ON job_skills(job_id);
CREATE INDEX idx_scrape_runs_completed_at ON scrape_runs(completed_at);
CREATE INDEX idx_job_applications_replied ON job_applications(replied);
CREATE INDEX idx_job_applications_match ON job_applications(match_id);
