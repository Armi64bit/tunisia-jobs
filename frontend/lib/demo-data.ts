import type { Job, Source } from "./types";

export const SOURCES: Source[] = [
  { id: "keejob", name: "Keejob" },
  { id: "rekrute", name: "Rekrute" },
  { id: "emploitunisie", name: "Emploi Tunisie" },
  { id: "linkedin", name: "LinkedIn" },
];

export const SAMPLE_CV_SKILLS = [
  "Python",
  "TypeScript",
  "React",
  "SQL",
  "Docker",
  "PostgreSQL",
  "FastAPI",
  "AWS",
];

export const SAMPLE_CV_NAME = "Sample candidate profile";

export const JOBS: Job[] = [
  { id: 1, title: "Frontend Developer", company: "NovaWorks", source: "keejob", city: "Tunis", contract: "CDI", date: "2 d", salary: "1 900–2 400 TND", skills: ["TypeScript", "Next.js", "React"], desc: "Own the web dashboard experience: component architecture, performance, and clean interaction states. Pair with product and backend on API contracts." },
  { id: 2, title: "Backend Engineer (Python)", company: "Carthage Data", source: "keejob", city: "Tunis", contract: "CDI", date: "1 d", salary: "2 200–2 800 TND", skills: ["Python", "FastAPI", "PostgreSQL"], desc: "Build ingestion and matching services for the job platform. Strong SQL, async Python, and clean test coverage expected." },
  { id: 3, title: "Data Analyst", company: "SidiBou Analytics", source: "rekrute", city: "Sousse", contract: "CDD", date: "3 d", salary: "1 500–1 900 TND", skills: ["SQL", "Power BI", "Excel"], desc: "Turn scraped job-market data into dashboards and trend reports for clients across retail and industry." },
  { id: 4, title: "Fullstack Developer", company: "Medina Lab", source: "emploitunisie", city: "La Marsa", contract: "CDI", date: "5 d", salary: "2 000–2 600 TND", skills: ["React", "Node.js", "MongoDB"], desc: "Feature work across web and API layers for a bookings product. Comfort shipping both frontend and backend." },
  { id: 5, title: "DevOps Engineer", company: "Hammamet Cloud", source: "linkedin", city: "Hammamet", contract: "CDI", date: "1 d", salary: "2 400–3 000 TND", skills: ["Docker", "Kubernetes", "AWS"], desc: "Own CI/CD, container orchestration, and cloud cost for a growing SaaS. Terraform experience valued." },
  { id: 6, title: "Mobile Developer (Flutter)", company: "NovaWorks", source: "keejob", city: "Tunis", contract: "CDD", date: "4 d", salary: "1 800–2 300 TND", skills: ["Flutter", "Dart", "Firebase"], desc: "Deliver a cross-platform customer app. Clean architecture and app-store release experience required." },
  { id: 7, title: "Machine Learning Engineer", company: "Carthage Data", source: "linkedin", city: "Tunis", contract: "CDI", date: "6 d", salary: "2 600–3 200 TND", skills: ["Python", "TensorFlow", "NLP"], desc: "Train and serve matching/classification models on large text corpora. MLOps and evaluation rigor expected." },
  { id: 8, title: "QA Engineer", company: "SidiBou Analytics", source: "rekrute", city: "Sousse", contract: "CDD", date: "8 d", salary: "1 400–1 800 TND", skills: ["Selenium", "Postman", "Cypress"], desc: "Automate regression suites for web dashboards and REST APIs. Defect triage with engineering team." },
  { id: 9, title: "UI Designer", company: "Medina Lab", source: "emploitunisie", city: "La Marsa", contract: "CDI", date: "7 d", salary: "1 600–2 000 TND", skills: ["Figma", "Design Systems", "Prototyping"], desc: "Own the product design language: tokens, component states, and motion guidance for web and mobile." },
  { id: 10, title: "Salesforce Developer", company: "Hammamet Cloud", source: "linkedin", city: "Tunis", contract: "CDI", date: "2 d", salary: "2 200–2 700 TND", skills: ["Salesforce", "Apex", "Lightning"], desc: "Customize a sales platform: automation, integrations, and LWC components for the commercial team." },
  { id: 11, title: "Data Engineer", company: "Carthage Data", source: "keejob", city: "Tunis", contract: "CDI", date: "3 d", salary: "2 400–2 900 TND", skills: ["Airflow", "Spark", "dbt"], desc: "Design reliable batch and streaming pipelines feeding analytics. Airbyte ingestion experience a plus." },
  { id: 12, title: "React Native Developer", company: "SidiBou Analytics", source: "rekrute", city: "Sousse", contract: "CDI", date: "9 d", salary: "1 900–2 400 TND", skills: ["React Native", "TypeScript", "Redux"], desc: "Ship and maintain a field-data collection app used by field teams. Release management across stores." },
  { id: 13, title: "Cloud Security Engineer", company: "Hammamet Cloud", source: "linkedin", city: "Tunis", contract: "CDI", date: "5 d", salary: "2 600–3 200 TND", skills: ["AWS", "IAM", "SIEM"], desc: "Harden cloud workloads, run audits, and respond to incidents. Security certifications welcomed." },
  { id: 14, title: "Scraper / ETL Specialist", company: "Medina Lab", source: "emploitunisie", city: "Tunis", contract: "CDD", date: "2 d", salary: "1 700–2 100 TND", skills: ["Python", "Requests", "SQL"], desc: "Maintain job-board scrapers and reconciliation jobs. Resilience to HTML drift and rate-limit handling required." },
  { id: 15, title: "Product Manager", company: "NovaWorks", source: "keejob", city: "Tunis", contract: "CDI", date: "10 d", salary: "2 500–3 100 TND", skills: ["Roadmapping", "Analytics", "A/B Testing"], desc: "Drive the market-data product: discovery, prioritization, and measurable launches with a small seasoned team." },
  { id: 16, title: "Systems Administrator", company: "SidiBou Analytics", source: "rekrute", city: "Sousse", contract: "CDD", date: "12 d", salary: "1 600–2 000 TND", skills: ["Linux", "Docker", "Bash"], desc: "Run on-prem and cloud infrastructure: monitoring, patching, and reliable backups for internal tooling." },
];

export const NEW_JOBS: Job[] = [
  { id: 17, title: "Senior Fullstack Engineer", company: "Hammamet Cloud", source: "linkedin", city: "Tunis", contract: "CDI", date: "0 d", salary: "2 800–3 400 TND", skills: ["React", "Node.js", "PostgreSQL"], desc: "Lead a squad shipping the core product. Design reviews, mentoring, and reliable delivery are the role." },
  { id: 18, title: "NLP Research Engineer", company: "Carthage Data", source: "linkedin", city: "Tunis", contract: "CDI", date: "0 d", salary: "2 700–3 300 TND", skills: ["Python", "Transformers", "PyTorch"], desc: "Advance language models for matching quality. Publications or strong open-source contribution a plus." },
  { id: 19, title: "Frontend Intern", company: "Medina Lab", source: "emploitunisie", city: "La Marsa", contract: "Stage", date: "0 d", salary: "500–800 TND", skills: ["JavaScript", "HTML", "CSS"], desc: "Six-month internship building product features with a mentor. Strong fundamentals required." },
  { id: 20, title: "Sales Operations Analyst", company: "NovaWorks", source: "keejob", city: "Tunis", contract: "CDI", date: "0 d", salary: "1 600–2 000 TND", skills: ["Excel", "CRM", "SQL"], desc: "Support the commercial team with pipeline reporting, clean data, and lightweight automation." },
  { id: 21, title: "Test Automation Engineer", company: "Carthage Data", source: "rekrute", city: "Tunis", contract: "CDI", date: "0 d", salary: "1 900–2 400 TND", skills: ["Cypress", "Python", "CI"], desc: "Build end-to-end suites for web and API. Own flaky-test reduction and CI integration." },
  { id: 22, title: "Database Administrator", company: "SidiBou Analytics", source: "rekrute", city: "Sousse", contract: "CDD", date: "0 d", salary: "2 000–2 500 TND", skills: ["PostgreSQL", "Redis", "Backup"], desc: "Administer production databases: schema migrations, high availability, and performance tuning." },
];