/** Sidebar list for selecting items (scorecards, datasets) */

import type { ArtifactEntry } from "../types";

interface SidebarListProps {
  items: ArtifactEntry[];
  selected: string | null;
  onSelect: (path: string) => void;
  emptyMessage?: string;
}

export function SidebarList({
  items,
  selected,
  onSelect,
  emptyMessage = "No items found",
}: SidebarListProps) {
  if (items.length === 0) {
    return (
      <div className="px-5 py-6 font-sans text-sm italic text-ink-muted">
        {emptyMessage}
      </div>
    );
  }

  return (
    <ul className="list-none">
      {items.map((item) => (
        <li key={item.path}>
          {/** Result directories are UTC test IDs (YYYYMMDD-HHMMSS); display as local time for readability. */}
          {(() => {
            const isResultRun = item.path.startsWith("results/");
            const parsed = isResultRun ? parseRunIdUtc(item.name) : null;
            const displayName = parsed
              ? formatLocalDateTime(parsed)
              : item.name;

            return (
              <button
                type="button"
                className={`block w-full truncate border-none px-5 py-2 text-left font-mono text-xs transition-colors ${
                  selected === item.path
                    ? "bg-accent font-semibold text-white"
                    : "bg-transparent text-ink-secondary hover:bg-surface-hover hover:text-ink"
                }`}
                onClick={() => onSelect(item.path)}
                title={
                  isResultRun
                    ? `${displayName} (${item.name} UTC ID)`
                    : item.name
                }
              >
                {displayName}
              </button>
            );
          })()}
        </li>
      ))}
    </ul>
  );
}

function parseRunIdUtc(runId: string): Date | null {
  const m = /^(\d{4})(\d{2})(\d{2})-(\d{2})(\d{2})(\d{2})$/.exec(runId);
  if (!m) {
    return null;
  }

  const year = Number(m[1]);
  const month = Number(m[2]);
  const day = Number(m[3]);
  const hour = Number(m[4]);
  const minute = Number(m[5]);
  const second = Number(m[6]);

  // Run IDs are generated in UTC on the server; build Date from UTC parts.
  const utcMs = Date.UTC(year, month - 1, day, hour, minute, second);
  const d = new Date(utcMs);
  return Number.isNaN(d.getTime()) ? null : d;
}

function formatLocalDateTime(date: Date): string {
  return date.toLocaleString(undefined, {
    year: "numeric",
    month: "short",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}
