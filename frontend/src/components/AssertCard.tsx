import { useState } from "react";
import type { AssertRecordData } from "../types";
import { StatusBadge } from "./StatusBadge";
import { PassTable } from "./PassTable";
import type { EvalDetailData } from "./EvalDetailModal";

interface AssertCardProps {
  record: AssertRecordData;
  index: number;
  onShowDetail: (data: EvalDetailData) => void;
}

export function AssertCard({ record, index, onShowDetail }: AssertCardProps) {
  const nPasses = record.results.length;
  const [activeTab, setActiveTab] = useState(0);

  return (
    <div className="assert-card">
      <div className="assert-header">
        <span className="assert-title">Assertion #{index}</span>
        <StatusBadge status={record.passed ? "passed" : "failed"} />
      </div>

      <p className="scoring-strategy">
        <strong>Scoring strategy:</strong> {record.scoring_strategy}
      </p>
      <p className="criteria-msg">
        <strong>Result:</strong> {record.criteria_message}
      </p>

      {nPasses <= 1 ? (
        <PassTable
          passResults={record.results[0] ?? []}
          evaluatorNames={record.evaluator_names}
          inputLabels={record.input_labels}
          evaluableDicts={record.evaluable_dicts}
          onShowDetail={onShowDetail}
        />
      ) : (
        <>
          <div className="tab-buttons">
            {Array.from({ length: nPasses }, (_, i) => (
              <button
                key={i}
                className={`tab-btn ${i === activeTab ? "active" : ""}`}
                onClick={() => setActiveTab(i)}
              >
                Pass {i + 1}
              </button>
            ))}
          </div>
          <PassTable
            passResults={record.results[activeTab]}
            evaluatorNames={record.evaluator_names}
            inputLabels={record.input_labels}
            evaluableDicts={record.evaluable_dicts}
            onShowDetail={onShowDetail}
          />
        </>
      )}
    </div>
  );
}
