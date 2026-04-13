/** JSONL viewer — renders each line as a collapsible JSON object in a stack */

import { useState, useEffect } from "react";
import JsonView from "react18-json-view";
import "react18-json-view/src/style.css";

/** How many nesting levels to show expanded by default per row. */
const DEFAULT_COLLAPSE_DEPTH = 2;
/** Truncate long strings in the viewer after this many characters. */
const STRING_COLLAPSE_LENGTH = 120;

interface JsonlPanelProps {
  path: string;
  version?: number;
}

interface JsonlRow {
  index: number;
  data: unknown;
}

/** Parse a JSONL string into an array of parsed rows */
function parseJsonl(content: string): JsonlRow[] {
  const rows: JsonlRow[] = [];
  const lines = content.split("\n");
  let index = 0;
  for (const line of lines) {
    const trimmed = line.trim();
    if (!trimmed) continue;
    try {
      rows.push({ index, data: JSON.parse(trimmed) });
    } catch {
      rows.push({ index, data: { _parseError: true, _raw: trimmed } });
    }
    index++;
  }
  return rows;
}

export function JsonlPanel({ path, version }: JsonlPanelProps) {
  const [rows, setRows] = useState<JsonlRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    setError(null);
    fetch(`/api/file?path=${encodeURIComponent(path)}`)
      .then((r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.json();
      })
      .then((d: { content: string }) => {
        setRows(parseJsonl(d.content));
        setLoading(false);
      })
      .catch((err) => {
        setError(String(err));
        setLoading(false);
      });
  }, [path, version]);

  if (loading) {
    return (
      <div className="flex h-full items-center justify-center font-sans text-base text-ink-muted">
        Loading…
      </div>
    );
  }

  if (error) {
    return (
      <div className="mx-auto max-w-200 px-10 py-8">
        <h1 className="mb-4 border-b-2 border-border pb-2 font-mono text-lg font-bold">
          {path}
        </h1>
        <p className="text-fail">Failed to load file: {error}</p>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-200 px-10 py-8 pb-16">
      <h1 className="mb-4 border-b-2 border-border pb-2 font-mono text-lg font-bold">
        {path}
      </h1>
      <p className="mb-4 text-sm text-ink-muted">
        {rows.length} {rows.length === 1 ? "row" : "rows"}
      </p>
      <div className="flex flex-col gap-3">
        {rows.map((row) => (
          <div
            key={row.index}
            className="rounded-md border border-border bg-bg-inset px-5 py-4"
          >
            <div className="mb-2 font-mono text-xs font-semibold text-ink-muted">
              Row {row.index}
            </div>
            <JsonView
              src={row.data}
              collapsed={DEFAULT_COLLAPSE_DEPTH}
              collapseStringMode="address"
              collapseStringsAfterLength={STRING_COLLAPSE_LENGTH}
              theme="default"
              enableClipboard={false}
            />
          </div>
        ))}
      </div>
    </div>
  );
}
