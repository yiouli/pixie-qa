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

export interface DatasetItem {
  eval_input?: unknown;
  eval_output?: unknown;
  eval_metadata?: unknown;
  expected_output?: unknown;
  input?: unknown;
  output?: unknown;
  actual_output?: unknown;
  metadata?: unknown;
  [key: string]: unknown;
}

export interface DatasetData {
  name: string;
  items: DatasetItem[];
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

export interface EntryResultData {
  input: unknown;
  output: unknown;
  expectedOutput?: unknown;
  description?: string;
  evaluations: EvaluationResultData[];
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
