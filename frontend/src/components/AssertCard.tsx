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

      <PassTable
        passResults={record.results}
        evaluatorNames={record.evaluator_names}
        inputLabels={record.input_labels}
        evaluableDicts={record.evaluable_dicts}
        onShowDetail={onShowDetail}
      />
    </div>
  );
}
