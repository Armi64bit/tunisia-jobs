import type { ViewId } from "../lib/types";
import { BoltIcon, CheckBadgeIcon, GridIcon, TargetIcon } from "./icons";

interface SidebarProps {
  active: ViewId;
  onSwitch: (view: ViewId) => void;
}

const NAV: { id: ViewId; label: string; Icon: typeof GridIcon }[] = [
  { id: "overview", label: "Overview", Icon: GridIcon },
  { id: "scraper", label: "Scraper run", Icon: BoltIcon },
  { id: "matches", label: "CV matches", Icon: TargetIcon },
  { id: "applications", label: "Job offers", Icon: CheckBadgeIcon },
];

export default function Sidebar({ active, onSwitch }: SidebarProps) {
  return (
    <aside className="sidebar" aria-label="Primary">
      <nav className="od-stack" style={{ "--od-gap": "4px" } as React.CSSProperties}>
        {NAV.map(({ id, label, Icon }) => (
          <button
            key={id}
            className="nav-btn"
            data-view={id}
            aria-current={active === id ? "page" : undefined}
            onClick={() => onSwitch(id)}
          >
            <Icon />
            {label}
          </button>
        ))}
      </nav>
      <div className="sidebar-foot">Pipeline: keejob · rekrute · emploitunisie · linkedin</div>
    </aside>
  );
}