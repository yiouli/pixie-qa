import { useState } from "react";
import type { EvaluationData, EvaluableContext } from "../types";
import type { EvalDetailData } from "./EvalDetailModal";

interface PassTableProps {
  passResults: EvaluationData[][];
  evaluatorNames: string[];
  inputLabels: string[];
  evaluableDicts: EvaluableContext[];
  onShowDetail: (data: EvalDetailData) => void;
}

export function PassTable({
  passResults,
  evaluatorNames,
  inputLabels,
  evaluableDicts,
  onShowDetail,
}: PassTableProps) {
  const nInputs = passResults.length;
  const nEvaluators = evaluatorNames.length;

  // Per-evaluator pass counts
  const evalPassCounts = evaluatorNames.map(
    (_, eIdx) =>
      passResults.filter(
        (inpEvals) => eIdx < inpEvals.length && inpEvals[eIdx].score >= 0.5,
      ).length,
  );

  return (
    <>
      {/* Summary table */}
      <table>
        <thead>
          <tr>
            <th>Evaluator</th>
            <th>Passed</th>
          </tr>
        </thead>
        <tbody>
          {evaluatorNames.map((name, eIdx) => (
            <tr key={name}>
              <td>{name}</td>
              <td>
                {evalPassCounts[eIdx]}/{nInputs}
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      {/* Detail table */}
      {nEvaluators > 0 && nInputs > 0 && (
        <table>
          <thead>
            <tr>
              <th>Input</th>
              {evaluatorNames.map((name) => (
                <th key={name}>{name}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {passResults.map((inpEvals, iIdx) => {
              const label =
                iIdx < inputLabels.length ? inputLabels[iIdx] : `#${iIdx + 1}`;
              const ctx =
                iIdx < evaluableDicts.length ? evaluableDicts[iIdx] : {};

              return (
                <tr key={iIdx}>
                  <td className="input-label-cell">
                    <InputCell label={label} fullInput={ctx.input} />
                  </td>
                  {evaluatorNames.map((_, eIdx) => {
                    if (eIdx >= inpEvals.length) {
                      return <td key={eIdx}>—</td>;
                    }
                    const ev = inpEvals[eIdx];
                    const passed = ev.score >= 0.5;
                    return (
                      <td
                        key={eIdx}
                        className={passed ? "score-pass" : "score-fail"}
                      >
                        {ev.score.toFixed(2)}
                        <a
                          href="#"
                          className="details-link"
                          onClick={(e) => {
                            e.preventDefault();
                            onShowDetail({
                              score: ev.score,
                              reasoning: ev.reasoning,
                              input: ctx.input,
                              expectedOutput: ctx.expected_output,
                              actualOutput: ctx.actual_output,
                              metadata: ctx.metadata,
                            });
                          }}
                        >
                          details
                        </a>
                      </td>
                    );
                  })}
                </tr>
              );
            })}
          </tbody>
        </table>
      )}
    </>
  );
}

function InputCell({
  label,
  fullInput,
}: {
  label: string;
  fullInput?: string;
}) {
  const [expanded, setExpanded] = useState(false);

  const showToggle = fullInput != null && fullInput !== label;

  return (
    <>
      <span className="input-text">
        {showToggle && expanded ? fullInput : label}
      </span>
      {showToggle && (
        <a
          href="#"
          className="show-more-link"
          onClick={(e) => {
            e.preventDefault();
            setExpanded((v) => !v);
          }}
        >
          {expanded ? "show less" : "show more"}
        </a>
      )}
    </>
  );
}
