/** Simple markdown-to-HTML renderer (no dependencies) */

/** Escape HTML entities */
function esc(s: string): string {
  return s
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

/** Convert markdown text to HTML */
export function markdownToHtml(md: string): string {
  const lines = md.split("\n");
  const out: string[] = [];
  let inCode = false;
  let inTable = false;
  let inList = false;
  let listType: "ul" | "ol" = "ul";

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];

    // Fenced code blocks
    if (line.startsWith("```")) {
      if (inCode) {
        out.push("</code></pre>");
        inCode = false;
      } else {
        const lang = line.slice(3).trim();
        out.push(
          `<pre class="md-code-block"><code${lang ? ` class="language-${esc(lang)}"` : ""}>`,
        );
        inCode = true;
      }
      continue;
    }
    if (inCode) {
      out.push(esc(line));
      out.push("\n");
      continue;
    }

    // Close table if line doesn't start with |
    if (inTable && !line.startsWith("|")) {
      out.push("</tbody></table>");
      inTable = false;
    }

    // Close list if line doesn't match list pattern
    if (
      inList &&
      !/^(\s*[-*+]\s|\s*\d+\.\s)/.test(line) &&
      line.trim() !== ""
    ) {
      out.push(listType === "ul" ? "</ul>" : "</ol>");
      inList = false;
    }

    // Empty line
    if (line.trim() === "") {
      if (inList) {
        out.push(listType === "ul" ? "</ul>" : "</ol>");
        inList = false;
      }
      continue;
    }

    // Headings
    const headingMatch = line.match(/^(#{1,6})\s+(.+)$/);
    if (headingMatch) {
      const level = headingMatch[1].length;
      out.push(`<h${level}>${inlineFormat(headingMatch[2])}</h${level}>`);
      continue;
    }

    // Table rows
    if (line.startsWith("|")) {
      // Skip separator rows
      if (/^\|[\s\-:|]+\|$/.test(line)) continue;
      const cells = line
        .split("|")
        .slice(1, -1)
        .map((c) => c.trim());
      if (!inTable) {
        out.push('<table class="md-table"><thead><tr>');
        cells.forEach((c) => out.push(`<th>${inlineFormat(c)}</th>`));
        out.push("</tr></thead><tbody>");
        inTable = true;
      } else {
        out.push("<tr>");
        cells.forEach((c) => out.push(`<td>${inlineFormat(c)}</td>`));
        out.push("</tr>");
      }
      continue;
    }

    // Unordered lists
    const ulMatch = line.match(/^(\s*)[-*+]\s+(.+)$/);
    if (ulMatch) {
      if (!inList) {
        out.push("<ul>");
        inList = true;
        listType = "ul";
      }
      out.push(`<li>${inlineFormat(ulMatch[2])}</li>`);
      continue;
    }

    // Ordered lists
    const olMatch = line.match(/^(\s*)\d+\.\s+(.+)$/);
    if (olMatch) {
      if (!inList) {
        out.push("<ol>");
        inList = true;
        listType = "ol";
      }
      out.push(`<li>${inlineFormat(olMatch[2])}</li>`);
      continue;
    }

    // Paragraph
    out.push(`<p>${inlineFormat(line)}</p>`);
  }

  // Close open blocks
  if (inCode) out.push("</code></pre>");
  if (inTable) out.push("</tbody></table>");
  if (inList) out.push(listType === "ul" ? "</ul>" : "</ol>");

  return out.join("\n");
}

/** Apply inline formatting: bold, italic, code, links */
function inlineFormat(text: string): string {
  let s = esc(text);
  // inline code (must be before bold/italic to prevent conflicts)
  s = s.replace(/`([^`]+)`/g, '<code class="md-inline-code">$1</code>');
  // bold
  s = s.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");
  // italic
  s = s.replace(/\*(.+?)\*/g, "<em>$1</em>");
  // links
  s = s.replace(
    /\[([^\]]+)\]\(([^)]+)\)/g,
    '<a href="$2" target="_blank" rel="noreferrer">$1</a>',
  );
  return s;
}
