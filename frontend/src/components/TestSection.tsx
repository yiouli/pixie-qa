import type { TestRecordData } from "../types";
import { StatusBadge } from "./StatusBadge";
import { AssertCard } from "./AssertCard";
import type { EvalDetailData } from "./EvalDetailModal";

interface TestSectionProps {
  record: TestRecordData;
  onShowDetail: (data: EvalDetailData) => void;
}

export function TestSection({ record, onShowDetail }: TestSectionProps) {
  return (
    <div className="card">
      <div className="test-header">
        <span className="test-name">{record.name}</span>
        <StatusBadge status={record.status} />
      </div>

      {record.message && <pre className="error-msg">{record.message}</pre>}

      {record.asserts.length === 0 ? (
        <p className="no-asserts">
          No assert_pass / assert_dataset_pass calls recorded.
        </p>
      ) : (
        record.asserts.map((ar, idx) => (
          <AssertCard
            key={idx}
            record={ar}
            index={idx + 1}
            onShowDetail={onShowDetail}
          />
        ))
      )}
    </div>
  );
}
