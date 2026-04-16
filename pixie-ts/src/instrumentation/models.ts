/**
 * Pydantic-equivalent models for trace log records.
 */

import type { JsonValue } from "../eval/evaluable.js";

export const INPUT_DATA_KEY = "input_data";

/** First record in a trace JSONL. */
export interface InputDataLog {
  readonly type: "kwargs";
  readonly value: Record<string, JsonValue>;
}

/** LLM span record capturing the semantically meaningful fields. */
export interface LLMSpanLog {
  readonly type: "llm_span";
  readonly operation: string | null;
  readonly provider: string | null;
  readonly requestModel: string | null;
  readonly responseModel: string | null;
  readonly inputMessages: Record<string, unknown>[];
  readonly outputMessages: Record<string, unknown>[];
  readonly toolDefinitions: Record<string, unknown>[];
  readonly finishReasons: string[];
  readonly outputType: string | null;
  readonly errorType: string | null;
}

/** Full LLM span record including timing and token data. */
export interface LLMSpanTrace extends Omit<LLMSpanLog, "type"> {
  readonly type: "llm_span_trace";
  readonly inputTokens: number;
  readonly outputTokens: number;
  readonly durationMs: number;
  readonly startedAt: string | null;
  readonly endedAt: string | null;
}

export function createInputDataLog(
  value: Record<string, JsonValue>,
): InputDataLog {
  return { type: "kwargs", value };
}

export function createLlmSpanLog(
  opts: Partial<Omit<LLMSpanLog, "type">> = {},
): LLMSpanLog {
  return {
    type: "llm_span",
    operation: opts.operation ?? null,
    provider: opts.provider ?? null,
    requestModel: opts.requestModel ?? null,
    responseModel: opts.responseModel ?? null,
    inputMessages: opts.inputMessages ?? [],
    outputMessages: opts.outputMessages ?? [],
    toolDefinitions: opts.toolDefinitions ?? [],
    finishReasons: opts.finishReasons ?? [],
    outputType: opts.outputType ?? null,
    errorType: opts.errorType ?? null,
  };
}
