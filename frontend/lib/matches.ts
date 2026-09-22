import type { Job, MatchedJob } from "./types";

export function companyLine(jobs: Job[], company: string): string {
  const posts = jobs.filter((j) => j.company === company);
  const counts: Record<string, number> = {};
  posts.forEach((j) =>
    j.skills.forEach((s) => {
      counts[s] = (counts[s] || 0) + 1;
    }),
  );
  const top = Object.keys(counts)
    .sort((a, b) => counts[b] - counts[a])
    .slice(0, 3);
  return (
    `${company} has ${posts.length} active posting${posts.length === 1 ? "" : "s"} in this dataset` +
    (top.length ? `, most in-demand skills: ${top.join(", ")}` : "") +
    "."
  );
}

export function whyGoodMatch(m: MatchedJob): string {
  const req = m.matched.length + m.missing.length;
  if (!req) return "No required skills were parsed for this listing.";
  const parts = [`Your CV covers ${m.matched.length} of ${req} required skills`];
  if (m.matched.length) parts.push(`matched: ${m.matched.join(", ")}`);
  if (m.missing.length) parts.push(`gaps to address: ${m.missing.join(", ")}`);
  if (m.score >= 80) parts.push("top-tier overlap, an excellent application target");
  else if (m.score >= 60) parts.push("solid overlap, worth applying with the gaps addressed");
  else if (m.score >= 40) parts.push("partial overlap, tailor your CV to the listed skills");
  else parts.push("low overlap against the listed requirements");
  return `${parts.join(". ")}.`;
}