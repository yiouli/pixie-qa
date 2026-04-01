/** Markdown viewer panel */

import { useState, useEffect } from "react";
import { markdownToHtml } from "../markdown";

interface MarkdownPanelProps {
  path: string;
  /** Increment to force reload */
  version?: number;
}

export function MarkdownPanel({ path, version }: MarkdownPanelProps) {
  const [html, setHtml] = useState<string>("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    fetch(`/api/file?path=${encodeURIComponent(path)}`)
      .then((r) => r.json())
      .then((d: { content: string }) => {
        setHtml(markdownToHtml(d.content));
        setLoading(false);
      })
      .catch(() => {
        setHtml("<p>Failed to load file.</p>");
        setLoading(false);
      });
  }, [path, version]);

  if (loading) {
    return <div className="empty-state">Loading…</div>;
  }

  return (
    <article
      className="markdown-content"
      dangerouslySetInnerHTML={{ __html: html }}
    />
  );
}
