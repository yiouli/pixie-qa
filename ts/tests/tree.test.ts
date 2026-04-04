import { describe, it, expect } from "vitest";
import { ObservationNode, buildTree } from "../src/storage/tree";
import type { ObserveSpan, LLMSpan } from "../src/instrumentation/spans";

// ── Test helpers ─────────────────────────────────────────────────────────────

function makeObserveSpan(overrides: Partial<ObserveSpan> = {}): ObserveSpan {
  return {
    spanId: "s1",
    traceId: "t1",
    parentSpanId: null,
    startedAt: new Date("2024-01-01T00:00:00Z"),
    endedAt: new Date("2024-01-01T00:00:01Z"),
    durationMs: 1000,
    name: "root",
    input: "in",
    output: "out",
    metadata: {},
    error: null,
    ...overrides,
  };
}

function makeLLMSpan(overrides: Partial<LLMSpan> = {}): LLMSpan {
  return {
    spanId: "llm-1",
    traceId: "t1",
    parentSpanId: null,
    startedAt: new Date("2024-01-01T00:00:00Z"),
    endedAt: new Date("2024-01-01T00:00:01Z"),
    durationMs: 500,
    operation: "chat",
    provider: "openai",
    requestModel: "gpt-4",
    responseModel: "gpt-4",
    inputTokens: 10,
    outputTokens: 20,
    cacheReadTokens: 0,
    cacheCreationTokens: 0,
    requestTemperature: null,
    requestMaxTokens: null,
    requestTopP: null,
    finishReasons: ["stop"],
    responseId: null,
    outputType: null,
    errorType: null,
    inputMessages: [
      { role: "user", content: [{ type: "text", text: "hi" }] },
    ],
    outputMessages: [
      {
        role: "assistant",
        content: [{ type: "text", text: "hello" }],
        toolCalls: [],
        finishReason: "stop",
      },
    ],
    toolDefinitions: [],
    ...overrides,
  };
}

// ── ObservationNode ──────────────────────────────────────────────────────────

describe("ObservationNode", () => {
  it("delegates spanId, traceId, parentSpanId", () => {
    const span = makeObserveSpan({ spanId: "s1", traceId: "t1" });
    const node = new ObservationNode(span);
    expect(node.spanId).toBe("s1");
    expect(node.traceId).toBe("t1");
    expect(node.parentSpanId).toBeNull();
  });

  it("uses span.name for observe spans", () => {
    const node = new ObservationNode(makeObserveSpan({ name: "my-step" }));
    expect(node.name).toBe("my-step");
  });

  it("uses '(unnamed)' for observe spans with null name", () => {
    const node = new ObservationNode(makeObserveSpan({ name: null }));
    expect(node.name).toBe("(unnamed)");
  });

  it("uses requestModel for LLM spans", () => {
    const node = new ObservationNode(
      makeLLMSpan({ requestModel: "claude-3" })
    );
    expect(node.name).toBe("claude-3");
  });

  it("delegates durationMs", () => {
    const node = new ObservationNode(makeObserveSpan({ durationMs: 42 }));
    expect(node.durationMs).toBe(42);
  });
});

// ── find / findByType ────────────────────────────────────────────────────────

describe("ObservationNode.find", () => {
  it("finds nodes by name in subtree", () => {
    const root = new ObservationNode(makeObserveSpan({ name: "root" }));
    const child = new ObservationNode(makeObserveSpan({ name: "child", spanId: "s2" }));
    const grandchild = new ObservationNode(
      makeObserveSpan({ name: "child", spanId: "s3" })
    );
    root.children = [child];
    child.children = [grandchild];

    const found = root.find("child");
    expect(found).toHaveLength(2);
  });

  it("returns empty array when nothing matches", () => {
    const root = new ObservationNode(makeObserveSpan({ name: "root" }));
    expect(root.find("nonexistent")).toHaveLength(0);
  });

  it("includes the root node itself if it matches", () => {
    const root = new ObservationNode(makeObserveSpan({ name: "target" }));
    const found = root.find("target");
    expect(found).toHaveLength(1);
    expect(found[0].spanId).toBe(root.spanId);
  });
});

describe("ObservationNode.findByType", () => {
  it("finds all LLM nodes", () => {
    const root = new ObservationNode(makeObserveSpan());
    const llm = new ObservationNode(makeLLMSpan());
    root.children = [llm];
    expect(root.findByType("llm")).toHaveLength(1);
    expect(root.findByType("observe")).toHaveLength(1);
  });

  it("returns empty when no spans of requested type", () => {
    const root = new ObservationNode(makeObserveSpan());
    expect(root.findByType("llm")).toHaveLength(0);
  });
});

// ── buildTree ────────────────────────────────────────────────────────────────

describe("buildTree", () => {
  it("builds a single root from parentless spans", () => {
    const span = makeObserveSpan();
    const roots = buildTree([span]);
    expect(roots).toHaveLength(1);
    expect(roots[0].spanId).toBe("s1");
    expect(roots[0].children).toHaveLength(0);
  });

  it("links children to parents", () => {
    const parent = makeObserveSpan({ spanId: "p1" });
    const child = makeObserveSpan({ spanId: "c1", parentSpanId: "p1" });
    const roots = buildTree([parent, child]);
    expect(roots).toHaveLength(1);
    expect(roots[0].children).toHaveLength(1);
    expect(roots[0].children[0].spanId).toBe("c1");
  });

  it("orphaned nodes become roots", () => {
    const orphan = makeObserveSpan({
      spanId: "o1",
      parentSpanId: "missing-parent",
    });
    const roots = buildTree([orphan]);
    expect(roots).toHaveLength(1);
  });

  it("sorts children by startedAt ascending", () => {
    const parent = makeObserveSpan({ spanId: "p1" });
    const child2 = makeObserveSpan({
      spanId: "c2",
      parentSpanId: "p1",
      startedAt: new Date("2024-01-01T00:00:02Z"),
    });
    const child1 = makeObserveSpan({
      spanId: "c1",
      parentSpanId: "p1",
      startedAt: new Date("2024-01-01T00:00:01Z"),
    });
    const roots = buildTree([parent, child2, child1]);
    expect(roots[0].children[0].spanId).toBe("c1");
    expect(roots[0].children[1].spanId).toBe("c2");
  });

  it("sorts roots by startedAt ascending", () => {
    const r2 = makeObserveSpan({
      spanId: "r2",
      startedAt: new Date("2024-01-01T00:00:02Z"),
    });
    const r1 = makeObserveSpan({
      spanId: "r1",
      startedAt: new Date("2024-01-01T00:00:01Z"),
    });
    const roots = buildTree([r2, r1]);
    expect(roots[0].spanId).toBe("r1");
    expect(roots[1].spanId).toBe("r2");
  });

  it("handles empty input", () => {
    expect(buildTree([])).toHaveLength(0);
  });

  it("handles mixed span types", () => {
    const obs = makeObserveSpan({ spanId: "obs" });
    const llm = makeLLMSpan({ spanId: "llm", parentSpanId: "obs" });
    const roots = buildTree([obs, llm]);
    expect(roots).toHaveLength(1);
    expect(roots[0].children).toHaveLength(1);
    expect(roots[0].findByType("llm")).toHaveLength(1);
  });
});

// ── toText ───────────────────────────────────────────────────────────────────

describe("ObservationNode.toText", () => {
  it("serializes an observe span with input/output", () => {
    const node = new ObservationNode(
      makeObserveSpan({ name: "step", input: "q", output: "a", durationMs: 42 })
    );
    const text = node.toText();
    expect(text).toContain("step [42ms]");
    expect(text).toContain("input: q");
    expect(text).toContain("output: a");
  });

  it("shows error for observe spans", () => {
    const node = new ObservationNode(
      makeObserveSpan({ error: "Something failed" })
    );
    const text = node.toText();
    expect(text).toContain("<e>Something failed</e>");
  });

  it("shows metadata for observe spans", () => {
    const node = new ObservationNode(
      makeObserveSpan({ metadata: { key: "value" } })
    );
    const text = node.toText();
    expect(text).toContain("metadata:");
    expect(text).toContain('"key"');
  });

  it("serializes an LLM span with model and provider", () => {
    const node = new ObservationNode(
      makeLLMSpan({ requestModel: "gpt-4", provider: "openai", durationMs: 200 })
    );
    const text = node.toText();
    expect(text).toContain("gpt-4 [openai, 200ms]");
  });

  it("shows token counts for LLM spans", () => {
    const node = new ObservationNode(
      makeLLMSpan({ inputTokens: 100, outputTokens: 50 })
    );
    const text = node.toText();
    expect(text).toContain("100 in / 50 out");
  });

  it("shows tool definitions for LLM spans", () => {
    const node = new ObservationNode(
      makeLLMSpan({
        toolDefinitions: [
          { name: "search", description: null, parameters: null },
          { name: "calc", description: null, parameters: null },
        ],
      })
    );
    const text = node.toText();
    expect(text).toContain("tools: [search, calc]");
  });

  it("indents children", () => {
    const root = new ObservationNode(makeObserveSpan({ name: "root" }));
    const child = new ObservationNode(
      makeObserveSpan({ name: "child", spanId: "s2" })
    );
    root.children = [child];
    const text = root.toText();
    const lines = text.split("\n");
    const childLine = lines.find((l) => l.includes("child"));
    expect(childLine).toBeDefined();
    expect(childLine!.startsWith("  ")).toBe(true);
  });
});
