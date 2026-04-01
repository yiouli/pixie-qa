/** Main Web UI application */

import { useState, useCallback, useRef } from "react";
import type { Manifest, FileChangeEvent } from "./types";
import { useSSE } from "./useSSE";
import { TabBar } from "./components/TabBar";
import { ScorecardsPanel } from "./components/ScorecardsPanel";
import { DatasetsPanel } from "./components/DatasetsPanel";
import { MarkdownPanel } from "./components/MarkdownPanel";

const BRAND_ICON_URL =
  "https://github.com/user-attachments/assets/76c18199-f00a-4fb3-a12f-ce6c173727af";
const REPO_URL = "https://github.com/yiouli/pixie-qa";
const FEEDBACK_URL = "https://feedback.gopixie.ai/feedback";

interface TabDef {
  id: string;
  label: string;
  type: "scorecards" | "datasets" | "markdown";
  path?: string;
}

function buildTabs(manifest: Manifest): TabDef[] {
  const tabs: TabDef[] = [
    { id: "scorecards", label: "Scorecards", type: "scorecards" },
    { id: "datasets", label: "Datasets", type: "datasets" },
  ];
  for (const md of manifest.markdown_files) {
    // Derive label from filename: "01-entry-point.md" → "Entry Point"
    const stem = md.name.replace(/\.md$/, "");
    const label = stem
      .replace(/^\d+-/, "")
      .replace(/-/g, " ")
      .replace(/\b\w/g, (c) => c.toUpperCase());
    tabs.push({ id: `md:${md.path}`, label, type: "markdown", path: md.path });
  }
  return tabs;
}

/** Read initial tab & item selection from URL query params (?tab=...&id=...) */
function getInitialSelection(): { tab: string; id: string | null } {
  const params = new URLSearchParams(window.location.search);
  return {
    tab: params.get("tab") ?? "scorecards",
    id: params.get("id") ?? null,
  };
}

export default function WebUIApp() {
  const initial = getInitialSelection();

  const [manifest, setManifest] = useState<Manifest>({
    markdown_files: [],
    datasets: [],
    scorecards: [],
  });
  const [activeTab, setActiveTab] = useState(initial.tab);
  const [scorecardAutoSelect, setScorecardAutoSelect] = useState<string | null>(
    initial.tab === "scorecards" ? initial.id : null,
  );
  const [datasetAutoSelect, setDatasetAutoSelect] = useState<string | null>(
    initial.tab === "datasets" ? initial.id : null,
  );
  const [mdVersions, setMdVersions] = useState<Record<string, number>>({});
  const [feedbackOpen, setFeedbackOpen] = useState(false);

  const tabsRef = useRef<TabDef[]>([]);

  const onManifest = useCallback((m: Manifest) => {
    setManifest(m);
  }, []);

  const onFileChange = useCallback((changes: FileChangeEvent[]) => {
    for (const change of changes) {
      if (change.path.startsWith("scorecards/")) {
        setActiveTab("scorecards");
        if (change.type === "added" || change.type === "modified") {
          setScorecardAutoSelect(change.path);
        }
      } else if (change.path.startsWith("datasets/")) {
        setActiveTab("datasets");
        if (change.type === "added" || change.type === "modified") {
          setDatasetAutoSelect(change.path);
        }
      } else if (change.path.endsWith(".md")) {
        const tabId = `md:${change.path}`;
        setActiveTab(tabId);
        setMdVersions((prev) => ({
          ...prev,
          [change.path]: (prev[change.path] ?? 0) + 1,
        }));
      }
    }
  }, []);

  useSSE({ onManifest, onFileChange });

  const tabs = buildTabs(manifest);
  tabsRef.current = tabs;

  // Find active tab definition
  const activeTabDef = tabs.find((t) => t.id === activeTab) ?? tabs[0];

  return (
    <div className="webui-root">
      <header className="brand-header">
        <div className="brand-lockup">
          <img
            src={BRAND_ICON_URL}
            className="brand-icon"
            alt="Pixie"
            loading="lazy"
            referrerPolicy="no-referrer"
          />
          <span className="brand-name">pixie</span>
        </div>
        <div className="brand-actions">
          <button
            type="button"
            className="btn-ghost"
            onClick={() => setFeedbackOpen(true)}
          >
            Share feedback
          </button>
          <a
            className="btn-primary"
            href={REPO_URL}
            target="_blank"
            rel="noreferrer"
          >
            ★ Star on GitHub
          </a>
        </div>
      </header>

      <TabBar
        tabs={tabs.map((t) => ({ id: t.id, label: t.label }))}
        activeTab={activeTab}
        onSelect={setActiveTab}
      />

      <div className="webui-content">
        {activeTabDef?.type === "scorecards" && (
          <ScorecardsPanel
            scorecards={manifest.scorecards}
            autoSelect={scorecardAutoSelect}
          />
        )}
        {activeTabDef?.type === "datasets" && (
          <DatasetsPanel
            datasets={manifest.datasets}
            autoSelect={datasetAutoSelect}
          />
        )}
        {activeTabDef?.type === "markdown" && activeTabDef.path && (
          <MarkdownPanel
            path={activeTabDef.path}
            version={mdVersions[activeTabDef.path] ?? 0}
          />
        )}
      </div>

      {feedbackOpen && (
        <FeedbackOverlay onClose={() => setFeedbackOpen(false)} />
      )}
    </div>
  );
}

function FeedbackOverlay({ onClose }: { onClose: () => void }) {
  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal-card" onClick={(e) => e.stopPropagation()}>
        <button type="button" className="modal-close" onClick={onClose}>
          ✕
        </button>
        <h2>Share Feedback</h2>
        <p style={{ margin: "1rem 0", fontFamily: "var(--font-sans)" }}>
          We'd love to hear from you! Visit our feedback page:
        </p>
        <a
          href={FEEDBACK_URL}
          target="_blank"
          rel="noreferrer"
          className="btn-primary"
          style={{ display: "inline-block" }}
        >
          Open Feedback Form
        </a>
      </div>
    </div>
  );
}
