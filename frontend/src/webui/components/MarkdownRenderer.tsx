/** Shared markdown renderer using react-markdown + syntax highlighting */

import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { CodeBlock } from "./CodeBlock";
import type { Components } from "react-markdown";
import type { ReactNode } from "react";

interface MarkdownRendererProps {
  /** Raw markdown string */
  children: string;
  /** Additional CSS class for the wrapper */
  className?: string;
}

/** Extract text content from React children (for pre > code fallback) */
function extractText(children: ReactNode): string | null {
  if (typeof children === "string") return children.replace(/\n$/, "");
  if (Array.isArray(children)) {
    const parts = children.map(extractText).filter((c) => c !== null);
    return parts.length > 0 ? parts.join("") : null;
  }
  if (
    children &&
    typeof children === "object" &&
    "props" in children &&
    (children as { props: { children?: ReactNode } }).props
  ) {
    return extractText(
      (children as { props: { children?: ReactNode } }).props
        .children as ReactNode,
    );
  }
  return null;
}

/** Custom components for react-markdown rendering */
const markdownComponents: Components = {
  code({ className, children }) {
    const match = /language-(\w+)/.exec(className || "");
    const codeString = String(children).replace(/\n$/, "");

    // Fenced code block (has language class) — render with syntax highlighting
    if (match) {
      return <CodeBlock language={match[1]}>{codeString}</CodeBlock>;
    }

    // Inline code
    return (
      <code className="rounded-sm bg-bg-inset px-1.5 py-px font-mono text-sm text-ink">
        {children}
      </code>
    );
  },
  pre({ children, className }) {
    // If children is already a CodeBlock (from the code component), pass through
    // Otherwise wrap plain code blocks
    const codeChild = Array.isArray(children) ? children[0] : children;
    if (
      codeChild &&
      typeof codeChild === "object" &&
      "type" in codeChild &&
      codeChild.type === CodeBlock
    ) {
      return <>{children}</>;
    }
    // Plain fenced code block without language — render with CodeBlock
    const text = extractText(children);
    if (text !== null) {
      return <CodeBlock>{text}</CodeBlock>;
    }
    return <pre className={className}>{children}</pre>;
  },
};

export function MarkdownRenderer({
  children,
  className,
}: MarkdownRendererProps) {
  return (
    <div className={className}>
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={markdownComponents}
      >
        {children}
      </ReactMarkdown>
    </div>
  );
}
