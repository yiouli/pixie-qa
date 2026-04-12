/** Types for the pixie web UI */

export interface ArtifactEntry {
  name: string;
  path: string;
}

export interface Manifest {
  markdown_files: ArtifactEntry[];
  datasets: ArtifactEntry[];
  scorecards: ArtifactEntry[];
  results: ArtifactEntry[];
}

export interface NamedDataItem {
  name: string;
  value: unknown;
}

export interface DatasetItem {
  input_data?: Record<string, unknown>;
  description?: string;
  eval_input?: NamedDataItem[];
  expectation?: unknown;
  eval_metadata?: Record<string, unknown>;
  evaluators?: string[];
  [key: string]: unknown;
}

export interface DatasetData {
  name: string;
  items: DatasetItem[];
  /** Dataset-level default evaluators (from the JSON "evaluators" field). */
  defaultEvaluators: string[];
}

export interface FileChangeEvent {
  type: "added" | "modified" | "deleted";
  path: string;
}

export interface NavigateEvent {
  tab: string;
  id?: string;
}

// ── Test result types ──────────────────────────────────────────────────

export interface EvaluationResultData {
  evaluator: string;
  score: number;
  reasoning: string;
}

export interface PendingEvaluationData {
  evaluator: string;
  status: "pending";
  criteria: string;
}

export type AnyEvaluationData = EvaluationResultData | PendingEvaluationData;

export function isPendingEvaluation(
  ev: AnyEvaluationData,
): ev is PendingEvaluationData {
  return "status" in ev && (ev as PendingEvaluationData).status === "pending";
}

export interface EntryResultData {
  input: unknown;
  output: unknown;
  expectedOutput?: unknown;
  description?: string;
  evaluations: AnyEvaluationData[];
  analysis?: string;
}

export interface DatasetResultData {
  dataset: string;
  entries: EntryResultData[];
  analysis?: string;
}

export interface ResultMeta {
  testId: string;
  command: string;
  startedAt: string;
  endedAt: string;
}

export interface TestResultData {
  meta: ResultMeta;
  datasets: DatasetResultData[];
}
