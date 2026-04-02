/** Project Context panel — sidebar list of markdown files + content viewer */

import { useState, useEffect } from "react";
import type { ArtifactEntry } from "../types";
import { SidebarList } from "./SidebarList";
import { MarkdownPanel } from "./MarkdownPanel";

interface ProjectContextPanelProps {
  files: ArtifactEntry[];
  mdVersions: Record<string, number>;
  autoSelect?: string | null;
}

export function ProjectContextPanel({
  files,
  mdVersions,
  autoSelect,
}: ProjectContextPanelProps) {
  const [selected, setSelected] = useState<string | null>(
    files[0]?.path ?? null,
  );

  useEffect(() => {
    if (autoSelect && files.some((f) => f.path === autoSelect)) {
      setSelected(autoSelect);
    }
  }, [autoSelect, files]);

  // Select first if current selection is no longer valid
  useEffect(() => {
    if (
      selected &&
      !files.some((f) => f.path === selected) &&
      files.length > 0
    ) {
      setSelected(files[0].path);
    } else if (!selected && files.length > 0) {
      setSelected(files[0].path);
    }
  }, [files, selected]);

  return (
    <div className="split-panel">
      <aside className="split-sidebar">
        <SidebarList
          items={files}
          selected={selected}
          onSelect={setSelected}
          emptyMessage="No project context files"
        />
      </aside>
      <div className="split-main">
        {selected ? (
          <MarkdownPanel path={selected} version={mdVersions[selected] ?? 0} />
        ) : (
          <div className="empty-state">
            <p>Select a file to view</p>
          </div>
        )}
      </div>
    </div>
  );
}
