/** Markdown viewer panel */

import { useState, useEffect } from "react";
import { MarkdownRenderer } from "./MarkdownRenderer";

interface MarkdownPanelProps {
  path: string;
  /** Increment to force reload */
  version?: number;
}

export function MarkdownPanel({ path, version }: MarkdownPanelProps) {
  const [content, setContent] = useState<string>("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    fetch(`/api/file?path=${encodeURIComponent(path)}`)
      .then((r) => r.json())
      .then((d: { content: string }) => {
        setContent(d.content);
        setLoading(false);
      })
      .catch(() => {
        setContent("Failed to load file.");
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

  return (
    <MarkdownRenderer className="markdown-content">{content}</MarkdownRenderer>
  );
}
