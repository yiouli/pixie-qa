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

  useEffect(() => {
    if (autoSelect) {
      setSelected(autoSelect);
    }
  }, [autoSelect]);

  // Select first if current selection is no longer valid
  useEffect(() => {
    if (
      selected &&
      !scorecards.some((s) => s.path === selected) &&
      scorecards.length > 0
    ) {
      setSelected(scorecards[0].path);
    }
  }, [scorecards, selected]);

  return (
    <div className="split-panel">
      <aside className="split-sidebar">
        <SidebarList
          items={scorecards}
          selected={selected}
          onSelect={setSelected}
          emptyMessage="No scorecards yet"
        />
      </aside>
      <div className="split-main">
        {selected ? (
          <iframe
            key={selected}
            src={`/api/file?path=${encodeURIComponent(selected)}`}
            className="scorecard-iframe"
            title="Scorecard"
          />
        ) : (
          <div className="empty-state">
            <p>Select a scorecard to view</p>
          </div>
        )}
      </div>
    </div>
  );
}
