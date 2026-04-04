/**
 * Higher-level eval utilities: runAndEvaluate, assertPass, assertDatasetPass.
 */

import type { Evaluable, JsonValue } from "../storage/evaluable";
import { UNSET, asEvaluable } from "../storage/evaluable";
import type { ObservationNode } from "../storage/tree";
import { buildTree } from "../storage/tree";
import { ScoreThreshold, type PassCriteria } from "./criteria";
import type { Evaluation, Evaluator } from "./evaluation";
import { evaluate } from "./evaluation";
import { captureTraces } from "./traceCapture";

// ── Constants ────────────────────────────────────────────────────────────────

/**
 * Default max number of runnables executing concurrently within a
 * single `assertPass` / `assertDatasetPass` call.
 */
export const DEFAULT_RUNNABLE_CONCURRENCY = 4;

// ── EvalAssertionError ───────────────────────────────────────────────────────

/**
 * Raised by `assertPass` when the pass criteria are not met.
 */
export class EvalAssertionError extends Error {
  readonly results: Evaluation[][];

  constructor(message: string, results: Evaluation[][]) {
    super(message);
    this.name = "EvalAssertionError";
    this.results = results;
  }
}

// ── Internal helpers ─────────────────────────────────────────────────────────

function defaultPassCriteria(results: Evaluation[][]): [boolean, string] {
  const allScores = results.flatMap((row) => row.map((e) => e.score));
  const avg =
    allScores.length > 0
      ? allScores.reduce((a, b) => a + b, 0) / allScores.length
      : 0;
  const passed = allScores.every((s) => s >= 0.5);
  return [passed, `Average score: ${avg.toFixed(2)}, all >= 0.5: ${passed}`];
}

function getRunnableConcurrency(): number {
  const raw = process.env["PIXIE_RUNNABLE_CONCURRENCY"];
  if (raw !== undefined) {
    const parsed = parseInt(raw, 10);
    if (!isNaN(parsed)) return parsed;
  }
  return DEFAULT_RUNNABLE_CONCURRENCY;
}

// ── runAndCapture ────────────────────────────────────────────────────────────

type Runnable = (evalInput: unknown) => unknown | Promise<unknown>;
type FromTrace = (trace: ObservationNode[]) => Evaluable;

async function runAndCapture(
  runnable: Runnable,
  evalInput: unknown,
  opts?: {
    expectedOutput?: unknown;
    fromTrace?: FromTrace;
  }
): Promise<[Evaluable, ObservationNode[]]> {
  const { handler } = await captureTraces(async () => {
    await Promise.resolve(runnable(evalInput));
  });

  if (handler.spans.length === 0) {
    throw new Error("No spans captured during runnable execution");
  }

  const traceTree = buildTree(handler.spans);

  let evaluable: Evaluable;
  if (opts?.fromTrace) {
    evaluable = opts.fromTrace(traceTree);
  } else {
    evaluable = asEvaluable(traceTree[0].span);
  }

  if (opts?.expectedOutput !== undefined) {
    evaluable = {
      evalInput: evaluable.evalInput,
      evalOutput: evaluable.evalOutput,
      evalMetadata: evaluable.evalMetadata,
      expectedOutput: opts.expectedOutput as JsonValue,
      evaluators: evaluable.evaluators,
      description: evaluable.description,
    };
  }

  return [evaluable, traceTree];
}

// ── runAndEvaluate ───────────────────────────────────────────────────────────

/**
 * Run a runnable while capturing traces, then evaluate.
 *
 * The runnable is called exactly once.
 */
export async function runAndEvaluate(
  evaluator: Evaluator,
  runnable: Runnable,
  evalInput: unknown,
  opts?: {
    expectedOutput?: unknown;
    fromTrace?: FromTrace;
  }
): Promise<Evaluation> {
  const [evaluable, traceTree] = await runAndCapture(
    runnable,
    evalInput,
    opts
  );
  return evaluate(evaluator, evaluable, { trace: traceTree });
}

// ── processSingleInput ───────────────────────────────────────────────────────

async function processSingleInput(
  idx: number,
  inp: unknown,
  evaluators: Evaluator[],
  evaluables: Evaluable[] | null,
  runnable: Runnable,
  fromTrace: FromTrace | undefined,
  semaphore: { acquire(): Promise<void>; release(): void } | null
): Promise<Evaluation[]> {
  const runRunnable = async (): Promise<[Evaluable, ObservationNode[]]> => {
    const captureOpts: { expectedOutput?: unknown; fromTrace?: FromTrace } = {};
    if (evaluables !== null) {
      captureOpts.expectedOutput = evaluables[idx].expectedOutput;
    }
    if (fromTrace) {
      captureOpts.fromTrace = fromTrace;
    }

    if (semaphore) {
      await semaphore.acquire();
      try {
        return await runAndCapture(runnable, inp, captureOpts);
      } finally {
        semaphore.release();
      }
    }
    return runAndCapture(runnable, inp, captureOpts);
  };

  if (evaluables !== null) {
    const evItem = evaluables[idx];
    if (evItem.evalOutput === null) {
      const [evaluable, traceTree] = await runRunnable();
      const evalPromises = evaluators.map((ev) =>
        evaluate(ev, evaluable, { trace: traceTree })
      );
      return Promise.all(evalPromises);
    } else {
      const evalPromises = evaluators.map((ev) => evaluate(ev, evItem));
      return Promise.all(evalPromises);
    }
  } else {
    const [evaluable, traceTree] = await runRunnable();
    const evalPromises = evaluators.map((ev) =>
      evaluate(ev, evaluable, { trace: traceTree })
    );
    return Promise.all(evalPromises);
  }
}

// ── Semaphore utility ────────────────────────────────────────────────────────

function createSemaphore(
  max: number
): { acquire(): Promise<void>; release(): void } {
  let count = 0;
  const queue: Array<() => void> = [];

  return {
    acquire(): Promise<void> {
      if (count < max) {
        count++;
        return Promise.resolve();
      }
      return new Promise<void>((resolve) => queue.push(resolve));
    },
    release(): void {
      const next = queue.shift();
      if (next) {
        next();
      } else {
        count--;
      }
    },
  };
}

// ── assertPass ───────────────────────────────────────────────────────────────

/**
 * Run evaluators against a runnable over multiple inputs.
 *
 * The results matrix has shape `[evalInputs][evaluators]`.
 * If the pass criteria are not met, throws `EvalAssertionError`.
 */
export async function assertPass(
  runnable: Runnable,
  evalInputs: unknown[],
  evaluators: Evaluator[],
  opts?: {
    evaluables?: Evaluable[];
    passCriteria?: PassCriteria;
    fromTrace?: FromTrace;
  }
): Promise<void> {
  const evaluables = opts?.evaluables ?? null;
  if (evaluables !== null && evaluables.length !== evalInputs.length) {
    throw new Error(
      `evaluables length (${evaluables.length}) must match evalInputs length (${evalInputs.length})`
    );
  }

  const defaultCriteria = new ScoreThreshold();
  const criteria = opts?.passCriteria ?? defaultCriteria.__call__.bind(defaultCriteria);
  const sem = createSemaphore(getRunnableConcurrency());

  const inputTasks = evalInputs.map((inp, idx) =>
    processSingleInput(
      idx,
      inp,
      evaluators,
      evaluables,
      runnable,
      opts?.fromTrace,
      sem
    )
  );
  const results: Evaluation[][] = await Promise.all(inputTasks);

  const [passed, message] = criteria(results);

  if (!passed) {
    throw new EvalAssertionError(message, results);
  }
}

// ── assertDatasetPass ────────────────────────────────────────────────────────

/**
 * Load a dataset by name, then run `assertPass` with its items.
 */
export async function assertDatasetPass(
  runnable: Runnable,
  datasetName: string,
  evaluators: Evaluator[],
  opts?: {
    datasetDir?: string;
    passCriteria?: PassCriteria;
    fromTrace?: FromTrace;
  }
): Promise<void> {
  const { DatasetStore } = await import("../dataset/store");
  const store = new DatasetStore(opts?.datasetDir);
  const dataset = store.get(datasetName);
  const items = [...dataset.items];
  const evalInputs = items.map((item) => item.evalInput);

  await assertPass(runnable, evalInputs, evaluators, {
    evaluables: items,
    passCriteria: opts?.passCriteria,
    fromTrace: opts?.fromTrace,
  });
}
