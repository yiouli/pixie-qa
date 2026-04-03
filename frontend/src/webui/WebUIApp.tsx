/** Main Web UI application */

import { useState, useCallback } from "react";
import type { Manifest, FileChangeEvent, NavigateEvent } from "./types";
import { useSSE } from "./useSSE";
import { TabBar } from "./components/TabBar";
import { ResultsPanel } from "./components/ResultsPanel";
import { ScorecardsPanel } from "./components/ScorecardsPanel";
import { DatasetsPanel } from "./components/DatasetsPanel";
import { ProjectContextPanel } from "./components/ProjectContextPanel";

const BRAND_ICON_URL =
  "https://github.com/user-attachments/assets/76c18199-f00a-4fb3-a12f-ce6c173727af";
const REPO_URL = "https://github.com/yiouli/pixie-qa";
const FEEDBACK_URL = "https://feedback.gopixie.ai/feedback";

interface TabDef {
  id: string;
  label: string;
}

const TABS: TabDef[] = [
  { id: "results", label: "Results" },
  { id: "scorecards", label: "Scorecards" },
  { id: "datasets", label: "Datasets" },
  { id: "project-context", label: "Project Context" },
];

/** Read initial tab & item selection from URL query params (?tab=...&id=...) */
function getInitialSelection(): { tab: string; id: string | null } {
  const params = new URLSearchParams(window.location.search);
  const rawTab = params.get("tab");
  // Normalise legacy md:* tab values to project-context
  const tab =
    rawTab && rawTab.startsWith("md:")
      ? "project-context"
      : (rawTab ?? "results");
  const id = params.get("id") ?? null;
  return { tab, id };
}

export default function WebUIApp() {
  const initial = getInitialSelection();

  const [manifest, setManifest] = useState<Manifest>({
    markdown_files: [],
    datasets: [],
    scorecards: [],
    results: [],
  });
  const [activeTab, setActiveTab] = useState(initial.tab);
  const [scorecardAutoSelect, setScorecardAutoSelect] = useState<string | null>(
    initial.tab === "scorecards" ? initial.id : null,
  );
  const [datasetAutoSelect, setDatasetAutoSelect] = useState<string | null>(
    initial.tab === "datasets" ? initial.id : null,
  );
  const [resultAutoSelect, setResultAutoSelect] = useState<string | null>(
    initial.tab === "results" ? initial.id : null,
  );
  const [mdAutoSelect, setMdAutoSelect] = useState<string | null>(
    initial.tab === "project-context" ? initial.id : null,
  );
  const [mdVersions, setMdVersions] = useState<Record<string, number>>({});
  const [feedbackOpen, setFeedbackOpen] = useState(false);

  const onManifest = useCallback((m: Manifest) => {
    setManifest(m);
  }, []);

  const onFileChange = useCallback((changes: FileChangeEvent[]) => {
    for (const change of changes) {
      if (change.path.startsWith("results/")) {
        setActiveTab("results");
        if (change.type === "added" || change.type === "modified") {
          // Extract the result dir path (results/<test_id>)
          const parts = change.path.split("/");
          if (parts.length >= 2) {
            setResultAutoSelect(`results/${parts[1]}`);
          }
        }
      } else if (change.path.startsWith("scorecards/")) {
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
        setActiveTab("project-context");
        setMdAutoSelect(change.path);
        setMdVersions((prev) => ({
          ...prev,
          [change.path]: (prev[change.path] ?? 0) + 1,
        }));
      }
    }
  }, []);

  const onNavigate = useCallback((nav: NavigateEvent) => {
    const tab = nav.tab.startsWith("md:") ? "project-context" : nav.tab;
    setActiveTab(tab);
    if (nav.id) {
      if (tab === "results") {
        setResultAutoSelect(nav.id);
      } else if (tab === "scorecards") {
        setScorecardAutoSelect(nav.id);
      } else if (tab === "datasets") {
        setDatasetAutoSelect(nav.id);
      } else if (tab === "project-context") {
        setMdAutoSelect(nav.id);
      }
    }
  }, []);

  useSSE({ onManifest, onFileChange, onNavigate });

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

      <TabBar tabs={TABS} activeTab={activeTab} onSelect={setActiveTab} />

      <div className="webui-content">
        {activeTab === "results" && (
          <ResultsPanel
            results={manifest.results}
            autoSelect={resultAutoSelect}
          />
        )}
        {activeTab === "scorecards" && (
          <ScorecardsPanel
            scorecards={manifest.scorecards}
            autoSelect={scorecardAutoSelect}
          />
        )}
        {activeTab === "datasets" && (
          <DatasetsPanel
            datasets={manifest.datasets}
            autoSelect={datasetAutoSelect}
          />
        )}
        {activeTab === "project-context" && (
          <ProjectContextPanel
            files={manifest.markdown_files}
            mdVersions={mdVersions}
            autoSelect={mdAutoSelect}
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
