import type { TestRecordData } from "../types";
import { StatusBadge } from "./StatusBadge";

interface OverviewProps {
  commandArgs: string;
  timestamp: string;
  testRecords: TestRecordData[];
}

export function Overview({
  commandArgs,
  timestamp,
  testRecords,
}: OverviewProps) {
  const total = testRecords.length;
  const passed = testRecords.filter((t) => t.status === "passed").length;
  const allPassed = passed === total;

  return (
    <div className="card">
      <h2>Test Run Overview</h2>
      <p className="meta-line">
        <strong>Command:</strong> <code>{commandArgs}</code>
      </p>
      <p className="meta-line">
        <strong>Timestamp:</strong> {timestamp}
      </p>
      <p className={`summary-line ${allPassed ? "pass" : "fail"}`}>
        {passed}/{total} tests passed
      </p>

      <table>
        <thead>
          <tr>
            <th>Test</th>
            <th>Status</th>
          </tr>
        </thead>
        <tbody>
          {testRecords.map((tr) => (
            <tr key={tr.name}>
              <td>{tr.name}</td>
              <td>
                <StatusBadge status={tr.status} />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
