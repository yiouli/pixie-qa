/** Scorecards panel — sidebar list + iframe viewer */

import { useState, useEffect } from "react";
import type { ArtifactEntry } from "../types";
import { SidebarList } from "./SidebarList";

interface ScorecardsPanelProps {
  scorecards: ArtifactEntry[];
  autoSelect?: string | null;
}

export function ScorecardsPanel({
  scorecards,
  autoSelect,
}: ScorecardsPanelProps) {
  const [selected, setSelected] = useState<string | null>(
    scorecards[0]?.path ?? null,
  );

  // Apply autoSelect when it changes OR when scorecards first populate
  useEffect(() => {
    if (autoSelect && scorecards.some((s) => s.path === autoSelect)) {
      setSelected(autoSelect);
    }
  }, [autoSelect, scorecards]);

  // Select first if current selection is no longer valid
  useEffect(() => {
    if (
      selected &&
      !scorecards.some((s) => s.path === selected) &&
      scorecards.length > 0
    ) {
      setSelected(scorecards[0].path);
    } else if (!selected && scorecards.length > 0) {
      setSelected(scorecards[0].path);
    }
  }, [scorecards, selected]);

  return (
    <div className="flex h-full">
      <aside className="w-60 min-w-60 overflow-y-auto border-r border-border bg-surface py-2">
        <SidebarList
          items={scorecards}
          selected={selected}
          onSelect={setSelected}
          emptyMessage="No scorecards yet"
        />
      </aside>
      <div className="flex-1 overflow-auto">
        {selected ? (
          <iframe
            key={selected}
            src={`/api/file?path=${encodeURIComponent(selected)}`}
            className="h-full w-full border-none"
            title="Scorecard"
          />
        ) : (
          <div className="flex h-full items-center justify-center font-sans text-base text-ink-muted">
            <p>Select a scorecard to view</p>
          </div>
        )}
      </div>
    </div>
  );
}
