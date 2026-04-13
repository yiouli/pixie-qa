/** Project Context panel — sidebar list of project files + content viewer */

import { useState, useEffect } from "react";
import type { ArtifactEntry } from "../types";
import { SidebarList } from "./SidebarList";
import { MarkdownPanel } from "./MarkdownPanel";
import { JsonPanel } from "./JsonPanel";
import { JsonlPanel } from "./JsonlPanel";
import { CodeBlock } from "./CodeBlock";

interface ProjectContextPanelProps {
  files: ArtifactEntry[];
  mdVersions: Record<string, number>;
  autoSelect?: string | null;
}

/** Return true if the file should be rendered as markdown */
function isMarkdown(path: string): boolean {
  return path.endsWith(".md");
}

/** Return true if the file should be rendered as collapsible JSON */
function isJson(path: string): boolean {
  return path.endsWith(".json");
}

/** Return true if the file should be rendered as a JSONL stack */
function isJsonl(path: string): boolean {
  return path.endsWith(".jsonl");
}

/** Infer language from file extension */
function inferLanguage(path: string): string | undefined {
  const ext = path.split(".").pop()?.toLowerCase();
  if (!ext) return undefined;
  const map: Record<string, string> = {
    py: "python",
    js: "javascript",
    ts: "typescript",
    tsx: "tsx",
    jsx: "jsx",
    sh: "bash",
    yml: "yaml",
    yaml: "yaml",
    toml: "toml",
    css: "css",
    html: "html",
    sql: "sql",
    rs: "rust",
    go: "go",
    rb: "ruby",
    java: "java",
    c: "c",
    cpp: "cpp",
    h: "c",
  };
  return map[ext];
}

/** Code/text viewer with syntax highlighting */
function CodePanel({ path, version }: { path: string; version?: number }) {
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

  const language = inferLanguage(path);

  return (
    <div className="mx-auto max-w-200 px-10 py-8 pb-16">
      <h1 className="mb-4 border-b-2 border-border pb-2 font-mono text-lg font-bold">
        {path}
      </h1>
      <CodeBlock language={language} showLineNumbers>
        {content}
      </CodeBlock>
    </div>
  );
}

export function ProjectContextPanel({
  files,
  mdVersions,
  autoSelect,
}: ProjectContextPanelProps) {
  const [selected, setSelected] = useState<string | null>(
    files[0]?.path ?? null,
  );

  useEffect(() => {
    if (autoSelect && files.some((f) => f.path === autoSelect)) {
      setSelected(autoSelect);
    }
  }, [autoSelect, files]);

  // Select first if current selection is no longer valid
  useEffect(() => {
    if (
      selected &&
      !files.some((f) => f.path === selected) &&
      files.length > 0
    ) {
      setSelected(files[0].path);
    } else if (!selected && files.length > 0) {
      setSelected(files[0].path);
    }
  }, [files, selected]);

  return (
    <div className="flex h-full">
      <aside className="w-60 min-w-60 overflow-y-auto border-r border-border bg-surface py-2">
        <SidebarList
          items={files}
          selected={selected}
          onSelect={setSelected}
          emptyMessage="No project context files"
        />
      </aside>
      <div className="flex-1 overflow-auto">
        {selected ? (
          isMarkdown(selected) ? (
            <MarkdownPanel
              path={selected}
              version={mdVersions[selected] ?? 0}
            />
          ) : isJsonl(selected) ? (
            <JsonlPanel path={selected} version={mdVersions[selected] ?? 0} />
          ) : isJson(selected) ? (
            <JsonPanel path={selected} version={mdVersions[selected] ?? 0} />
          ) : (
            <CodePanel path={selected} version={mdVersions[selected] ?? 0} />
          )
        ) : (
          <div className="flex h-full items-center justify-center font-sans text-base text-ink-muted">
            <p>Select a file to view</p>
          </div>
        )}
      </div>
    </div>
  );
}
