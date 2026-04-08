/** Pretty-formatted, collapsible JSON viewer panel */

import { useState, useEffect } from "react";
import JsonView from "react18-json-view";
import "react18-json-view/src/style.css";

interface JsonPanelProps {
  path: string;
  version?: number;
}

export function JsonPanel({ path, version }: JsonPanelProps) {
  const [data, setData] = useState<unknown>(null);
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
      .then((d: unknown) => {
        setData(d);
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
      <div className="overflow-x-auto rounded-md bg-bg-inset px-5 py-4">
        <JsonView
          src={data}
          collapsed={2}
          collapseStringMode="address"
          collapseStringsAfterLength={120}
          theme="default"
          enableClipboard={false}
        />
      </div>
    </div>
  );
}
