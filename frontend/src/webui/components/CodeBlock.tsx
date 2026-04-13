/** Syntax-highlighted code block using react-syntax-highlighter */

import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { oneLight } from "react-syntax-highlighter/dist/esm/styles/prism";

interface CodeBlockProps {
  /** Language for syntax highlighting (e.g. "python", "json") */
  language?: string;
  /** The code string to render */
  children: string;
  /** Show line numbers (default: false) */
  showLineNumbers?: boolean;
}

/** Map common language aliases */
function normalizeLanguage(lang: string | undefined): string {
  if (!lang) return "text";
  const lower = lang.toLowerCase();
  const aliases: Record<string, string> = {
    py: "python",
    js: "javascript",
    ts: "typescript",
    tsx: "tsx",
    jsx: "jsx",
    sh: "bash",
    shell: "bash",
    yml: "yaml",
  };
  return aliases[lower] ?? lower;
}

export function CodeBlock({
  language,
  children,
  showLineNumbers = false,
}: CodeBlockProps) {
  const lang = normalizeLanguage(language);

  return (
    <SyntaxHighlighter
      style={oneLight}
      language={lang}
      showLineNumbers={showLineNumbers}
      customStyle={{
        margin: 0,
        borderRadius: "0.375rem",
        fontSize: "0.875rem",
        lineHeight: "1.625",
      }}
      codeTagProps={{ style: { fontFamily: "var(--font-mono)" } }}
    >
      {children}
    </SyntaxHighlighter>
  );
}
