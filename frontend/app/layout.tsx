import type { Metadata, Viewport } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "TunisJobs — scrape & match dashboard",
  description:
    "Dark-mode dashboard for the Tunisia jobs scraper: browse scraped results, upload a CV, run the scraper with live progress, and review CV-to-job matches.",
};

export const viewport: Viewport = {
  colorScheme: "dark",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}