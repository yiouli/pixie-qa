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
    return <div className="sidebar-empty">{emptyMessage}</div>;
  }

  return (
    <ul className="sidebar-list">
      {items.map((item) => (
        <li key={item.path}>
          <button
            type="button"
            className={`sidebar-item${selected === item.path ? " active" : ""}`}
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
