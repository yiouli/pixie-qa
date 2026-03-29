import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import App from "./App";
import type { ScorecardReportData } from "./types";

async function loadData(): Promise<ScorecardReportData> {
  if (import.meta.env.DEV) {
    const res = await fetch("/mock-data.json");
    return res.json();
  }
  const raw = window.PIXIE_REPORT_DATA;
  if (typeof raw === "string") {
    return JSON.parse(raw);
  }
  return raw;
}

loadData().then((data) => {
  document.title = `Pixie Scorecard — ${data.timestamp}`;
  createRoot(document.getElementById("root")!).render(
    <StrictMode>
      <App data={data} />
    </StrictMode>,
  );
});
