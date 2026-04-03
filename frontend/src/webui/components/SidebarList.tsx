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
          <button
            type="button"
            className={`block w-full truncate border-none px-5 py-2 text-left font-mono text-xs transition-colors ${
              selected === item.path
                ? "bg-accent font-semibold text-white"
                : "bg-transparent text-ink-secondary hover:bg-surface-hover hover:text-ink"
            }`}
            onClick={() => onSelect(item.path)}
            title={item.name}
          >
            {item.name}
          </button>
        </li>
      ))}
    </ul>
  );
}
