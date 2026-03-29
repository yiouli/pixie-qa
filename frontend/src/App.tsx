import { useState } from "react";
import type { ScorecardReportData } from "./types";
import { BrandHeader } from "./components/BrandHeader";
import { Overview } from "./components/Overview";
import { TestSection } from "./components/TestSection";
import { EvalDetailModal } from "./components/EvalDetailModal";
import { FeedbackModal } from "./components/FeedbackModal";
import type { EvalDetailData } from "./components/EvalDetailModal";
import "./styles.css";

export default function App({ data }: { data: ScorecardReportData }) {
  const [feedbackOpen, setFeedbackOpen] = useState(false);
  const [evalDetail, setEvalDetail] = useState<EvalDetailData | null>(null);

  return (
    <>
      <BrandHeader
        repoUrl={data.pixie_repo_url}
        onFeedback={() => setFeedbackOpen(true)}
      />

      <main className="main-content">
        <Overview
          commandArgs={data.command_args}
          timestamp={data.timestamp}
          testRecords={data.test_records}
        />

        {data.test_records.map((tr) => (
          <TestSection key={tr.name} record={tr} onShowDetail={setEvalDetail} />
        ))}
      </main>

      <FeedbackModal
        open={feedbackOpen}
        onClose={() => setFeedbackOpen(false)}
        feedbackUrl={data.feedback_url}
        commandArgs={data.command_args}
        timestamp={data.timestamp}
      />

      <EvalDetailModal data={evalDetail} onClose={() => setEvalDetail(null)} />
    </>
  );
}
