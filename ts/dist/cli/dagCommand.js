"use strict";
/**
 * `pixie-qa dag` CLI subcommands — validate and check-trace.
 *
 * Commands:
 *   pixie-qa dag validate <json_file> [--project-root PATH]
 *   pixie-qa dag check-trace <json_file>
 */
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.dagValidate = dagValidate;
exports.dagCheckTrace = dagCheckTrace;
const fs_1 = __importDefault(require("fs"));
const path_1 = __importDefault(require("path"));
const index_1 = require("../dag/index");
const traceCheck_1 = require("../dag/traceCheck");
/**
 * Validate a DAG JSON file and generate a Mermaid diagram.
 *
 * @returns Exit code: 0 on success, 1 on validation failure.
 */
function dagValidate(jsonFile, projectRoot) {
    const jsonPath = path_1.default.resolve(jsonFile);
    const [nodes, parseErrors] = (0, index_1.parseDag)(jsonPath);
    if (parseErrors.length > 0) {
        console.log("PARSE ERRORS:");
        for (const err of parseErrors) {
            console.log(`  - ${err}`);
        }
        return 1;
    }
    const root = projectRoot ? path_1.default.resolve(projectRoot) : path_1.default.dirname(jsonPath);
    const result = (0, index_1.validateDag)(nodes, root);
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
    const mermaid = (0, index_1.generateMermaid)(nodes);
    const mermaidPath = jsonPath.replace(/\.json$/, ".md");
    const mermaidContent = `# Data Flow DAG\n\n\`\`\`mermaid\n${mermaid}\n\`\`\`\n`;
    fs_1.default.writeFileSync(mermaidPath, mermaidContent, "utf-8");
    console.log(`PASSED — DAG is valid (${nodes.length} nodes).`);
    console.log(`Mermaid diagram written to: ${mermaidPath}`);
    return 0;
}
/**
 * Check the last captured trace against a DAG JSON file.
 *
 * @returns Exit code: 0 if trace matches, 1 otherwise.
 */
async function dagCheckTrace(jsonFile) {
    const result = await (0, traceCheck_1.checkLastTrace)(path_1.default.resolve(jsonFile));
    if (!result.valid) {
        console.log(`TRACE CHECK FAILED — ${result.errors.length} error(s):`);
        for (const err of result.errors) {
            console.log(`  - ${err}`);
        }
        return 1;
    }
    console.log(`TRACE CHECK PASSED — ${result.matched.length} DAG node(s) matched.`);
    return 0;
}
//# sourceMappingURL=dagCommand.js.map