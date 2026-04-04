/**
 * `pixie-qa dag` CLI subcommands — validate and check-trace.
 *
 * Commands:
 *   pixie-qa dag validate <json_file> [--project-root PATH]
 *   pixie-qa dag check-trace <json_file>
 */

import fs from "fs";
import path from "path";

import { generateMermaid, parseDag, validateDag } from "../dag/index";
import { checkLastTrace } from "../dag/traceCheck";

/**
 * Validate a DAG JSON file and generate a Mermaid diagram.
 *
 * @returns Exit code: 0 on success, 1 on validation failure.
 */
export function dagValidate(
  jsonFile: string,
  projectRoot?: string
): number {
  const jsonPath = path.resolve(jsonFile);
  const [nodes, parseErrors] = parseDag(jsonPath);

  if (parseErrors.length > 0) {
    console.log("PARSE ERRORS:");
    for (const err of parseErrors) {
      console.log(`  - ${err}`);
    }
    return 1;
  }

  const root = projectRoot ? path.resolve(projectRoot) : path.dirname(jsonPath);
  const result = validateDag(nodes, root);

  if (!result.valid) {
    console.log(`VALIDATION FAILED — ${result.errors.length} error(s):`);
    for (const err of result.errors) {
      console.log(`  - ${err}`);
    }
    for (const warn of result.warnings) {
      console.log(`  [warn] ${warn}`);
    }
    return 1;
  }

  for (const warn of result.warnings) {
    console.log(`  [warn] ${warn}`);
  }

  // Generate Mermaid diagram
  const mermaid = generateMermaid(nodes);
  const mermaidPath = jsonPath.replace(/\.json$/, ".md");
  const mermaidContent = `# Data Flow DAG\n\n\`\`\`mermaid\n${mermaid}\n\`\`\`\n`;
  fs.writeFileSync(mermaidPath, mermaidContent, "utf-8");

  console.log(`PASSED — DAG is valid (${nodes.length} nodes).`);
  console.log(`Mermaid diagram written to: ${mermaidPath}`);
  return 0;
}

/**
 * Check the last captured trace against a DAG JSON file.
 *
 * @returns Exit code: 0 if trace matches, 1 otherwise.
 */
export async function dagCheckTrace(jsonFile: string): Promise<number> {
  const result = await checkLastTrace(path.resolve(jsonFile));

  if (!result.valid) {
    console.log(`TRACE CHECK FAILED — ${result.errors.length} error(s):`);
    for (const err of result.errors) {
      console.log(`  - ${err}`);
    }
    return 1;
  }

  console.log(
    `TRACE CHECK PASSED — ${result.matched.length} DAG node(s) matched.`
  );
  return 0;
}
