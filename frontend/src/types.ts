export interface EvaluationData {
  score: number;
  reasoning: string;
  details: Record<string, unknown>;
}

export interface EvaluableContext {
  input?: string;
  expected_output?: string;
  actual_output?: string;
  metadata?: Record<string, unknown>;
}

export interface AssertRecordData {
  evaluator_names: string[];
  input_labels: string[];
  /** Shape: [passes][inputs][evaluators] */
  results: EvaluationData[][][];
  passed: boolean;
  criteria_message: string;
  scoring_strategy: string;
  evaluable_dicts: EvaluableContext[];
}

export interface TestRecordData {
  name: string;
  status: "passed" | "failed" | "error";
  message: string | null;
  asserts: AssertRecordData[];
}

export interface ScorecardReportData {
  command_args: string;
  timestamp: string;
  summary: string;
  test_records: TestRecordData[];
  pixie_repo_url: string;
  feedback_url: string;
  brand_icon_url: string;
}
