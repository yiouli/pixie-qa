"use strict";
/**
 * Data-flow DAG parsing, validation, and Mermaid generation.
 *
 * The DAG schema is intentionally simple:
 *
 * - `name` is the unique lower_snake_case node identifier.
 * - `parent` (or legacy `parentId`) links nodes into a tree.
 * - `isLlmCall` marks nodes that represent LLM spans during trace checks.
 */
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.isValidDagName = isValidDagName;
exports.parseDag = parseDag;
exports.validateDag = validateDag;
exports.generateMermaid = generateMermaid;
const fs_1 = __importDefault(require("fs"));
const path_1 = __importDefault(require("path"));
// Lower snake_case node names, e.g. "handle_turn".
const DAG_NAME_PATTERN = /^[a-z][a-z0-9_]*$/;
/**
 * Return whether `name` matches lower_snake_case DAG naming.
 */
function isValidDagName(name) {
    return DAG_NAME_PATTERN.test(name);
}
/**
 * Parse a DAG JSON file into a list of DagNode objects.
 *
 * Returns `[nodes, errors]` where `errors` is empty on success.
 */
function parseDag(jsonPath) {
    const errors = [];
    let raw;
    try {
        const content = fs_1.default.readFileSync(jsonPath, "utf-8");
        raw = JSON.parse(content);
    }
    catch (exc) {
        if (exc.code === "ENOENT") {
            return [[], [`File not found: ${jsonPath}`]];
        }
        return [[], [`Invalid JSON: ${exc.message}`]];
    }
    if (!Array.isArray(raw)) {
        return [[], ["DAG JSON must be a top-level array of node objects."]];
    }
    const nodes = [];
    for (let i = 0; i < raw.length; i++) {
        const item = raw[i];
        if (typeof item !== "object" || item === null || Array.isArray(item)) {
            errors.push(`Node at index ${i}: expected object, got ${typeof item}`);
            continue;
        }
        // Required fields
        const required = ["name", "code_pointer", "description"];
        const missing = required.filter((f) => !(f in item));
        if (missing.length > 0) {
            errors.push(`Node at index ${i}: missing required fields: ${missing.join(", ")}`);
            continue;
        }
        // Optional metadata must be an object when present.
        const metadataRaw = item["metadata"] ?? {};
        if (typeof metadataRaw !== "object" || metadataRaw === null || Array.isArray(metadataRaw)) {
            errors.push(`Node '${String(item["name"] ?? `index ${i}`)}' metadata must be an object.`);
            continue;
        }
        // `is_llm_call` defaults to false when omitted.
        const isLlmCallRaw = item["is_llm_call"] ?? false;
        if (typeof isLlmCallRaw !== "boolean") {
            errors.push(`Node '${String(item["name"])}': is_llm_call must be true or false.`);
            continue;
        }
        // Backward-compatible parent parsing: prefer `parent` but accept
        // legacy `parent_id` for existing DAG files.
        const parentRaw = item["parent"];
        const legacyParentRaw = item["parent_id"];
        if (parentRaw !== undefined &&
            parentRaw !== null &&
            legacyParentRaw !== undefined &&
            legacyParentRaw !== null &&
            String(parentRaw) !== String(legacyParentRaw)) {
            errors.push(`Node '${String(item["name"])}': parent and parent_id disagree.`);
            continue;
        }
        const parentNameRaw = "parent" in item ? parentRaw : legacyParentRaw;
        const node = {
            name: String(item["name"]),
            codePointer: String(item["code_pointer"]),
            description: String(item["description"]),
            parent: parentNameRaw != null ? String(parentNameRaw) : null,
            isLlmCall: isLlmCallRaw,
            metadata: metadataRaw,
        };
        nodes.push(node);
    }
    return [nodes, errors];
}
/**
 * Parse code_pointer into (filePath, symbol, startLine, endLine, error).
 */
function parseCodePointer(codePointer) {
    // Find the split point: first ':' after a file extension
    const extIdx = codePointer.search(/\.(py|ts|js|tsx|jsx):/);
    if (extIdx === -1) {
        return [
            "", "", null, null,
            `code_pointer must contain '<file>.<ext>:<symbol>', got '${codePointer}'`,
        ];
    }
    // Find the extension end
    const colonAfterExt = codePointer.indexOf(":", extIdx + 1);
    if (colonAfterExt === -1) {
        return [
            "", "", null, null,
            `code_pointer must contain '<file>.<ext>:<symbol>', got '${codePointer}'`,
        ];
    }
    const fileStr = codePointer.substring(0, colonAfterExt);
    const rest = codePointer.substring(colonAfterExt + 1);
    if (!rest) {
        return [
            "", "", null, null,
            `code_pointer missing symbol after file path in '${codePointer}'`,
        ];
    }
    const parts = rest.split(":");
    const symbol = parts[0];
    let startLine = null;
    let endLine = null;
    if (parts.length === 1) {
        // just symbol
    }
    else if (parts.length === 3) {
        startLine = parseInt(parts[1], 10);
        endLine = parseInt(parts[2], 10);
        if (isNaN(startLine) || isNaN(endLine)) {
            return [
                "", "", null, null,
                `Invalid line numbers in code_pointer '${codePointer}'`,
            ];
        }
    }
    else {
        return [
            "", "", null, null,
            `code_pointer must be '<file>:<symbol>' or '<file>:<symbol>:<start>:<end>', got '${codePointer}'`,
        ];
    }
    return [fileStr, symbol, startLine, endLine, null];
}
/**
 * Validate that start..end is a valid line range in filePath.
 */
function checkLineRange(filePath, start, end) {
    if (start > end) {
        return `Invalid line range ${start}:${end} in ${filePath} — start must be <= end`;
    }
    const content = fs_1.default.readFileSync(filePath, "utf-8");
    const lineCount = content.split("\n").length;
    if (start < 1) {
        return `Invalid start line ${start} in ${filePath} — must be >= 1`;
    }
    if (end > lineCount) {
        return (`Line range ${start}:${end} exceeds file length (${lineCount} lines) ` +
            `in ${filePath}`);
    }
    return null;
}
/**
 * Validate the structural integrity of a DAG and its code pointers.
 *
 * Checks:
 * 1. Node names are unique.
 * 2. Node names use lower_snake_case.
 * 3. Every parent reference points to an existing node name.
 * 4. Exactly one root node (parent is null).
 * 5. No cycles in the parent chain.
 * 6. Code pointers reference existing files (if projectRoot is given).
 */
function validateDag(nodes, projectRoot) {
    const result = { valid: true, errors: [], warnings: [] };
    const nodeNames = new Set(nodes.map((n) => n.name));
    if (nodes.length === 0) {
        result.valid = false;
        result.errors.push("DAG is empty — at least one node is required.");
        return result;
    }
    // Check for duplicate node names
    const seenNames = new Set();
    for (const node of nodes) {
        if (seenNames.has(node.name)) {
            result.valid = false;
            result.errors.push(`Duplicate node name: '${node.name}'`);
        }
        seenNames.add(node.name);
    }
    // Enforce lower_snake_case names
    for (const node of nodes) {
        if (!isValidDagName(node.name)) {
            result.valid = false;
            result.errors.push(`Node '${node.name}': name must be lower_snake_case (e.g., 'handle_turn').`);
        }
        if (node.parent !== null && !isValidDagName(node.parent)) {
            result.valid = false;
            result.errors.push(`Node '${node.name}': parent '${node.parent}' must be lower_snake_case.`);
        }
    }
    // Check parent references
    const roots = [];
    for (const node of nodes) {
        if (node.parent === null) {
            roots.push(node);
        }
        else if (!nodeNames.has(node.parent)) {
            result.valid = false;
            result.errors.push(`Node '${node.name}': parent '${node.parent}' does not reference any node.`);
        }
    }
    if (roots.length === 0) {
        result.valid = false;
        result.errors.push("No root node found (no node with parent=null).");
    }
    else if (roots.length > 1) {
        const rootNames = roots.map((r) => r.name);
        result.valid = false;
        result.errors.push(`Multiple root nodes found: ${rootNames.join(", ")}. Expected exactly one root.`);
    }
    // Check for cycles
    const nameMap = new Map(nodes.map((n) => [n.name, n]));
    for (const node of nodes) {
        const visited = new Set();
        let current = node.name;
        while (current !== null) {
            if (visited.has(current)) {
                result.valid = false;
                result.errors.push(`Cycle detected involving node '${node.name}'.`);
                break;
            }
            visited.add(current);
            const parent = nameMap.get(current);
            current = parent ? parent.parent : null;
        }
    }
    // Check code pointers (file existence, line ranges)
    for (const node of nodes) {
        const [fileStr, , startLine, endLine, parseErr] = parseCodePointer(node.codePointer);
        if (parseErr !== null) {
            result.valid = false;
            result.errors.push(`Node '${node.name}': invalid code_pointer: ${parseErr}`);
            continue;
        }
        // Resolve file path (absolute or relative)
        let filePath = fileStr;
        if (!path_1.default.isAbsolute(filePath)) {
            if (projectRoot === undefined) {
                continue; // Can't resolve relative paths without projectRoot
            }
            filePath = path_1.default.join(projectRoot, filePath);
        }
        if (!fs_1.default.existsSync(filePath)) {
            result.valid = false;
            result.errors.push(`Node '${node.name}': code_pointer file not found: ${filePath}`);
            continue;
        }
        // Check line number range validity
        if (startLine !== null && endLine !== null) {
            const lineErr = checkLineRange(filePath, startLine, endLine);
            if (lineErr !== null) {
                result.valid = false;
                result.errors.push(`Node '${node.name}': ${lineErr}`);
            }
        }
    }
    return result;
}
/**
 * Return Mermaid shape delimiters based on root/LLM flags.
 */
function mermaidShape(node) {
    if (node.parent === null)
        return ["([", "])"];
    if (node.isLlmCall)
        return ["[[", "]]"];
    return ["[", "]"];
}
/**
 * Generate a Mermaid flowchart from the DAG nodes.
 */
function generateMermaid(nodes) {
    const lines = ["graph TD"];
    const mermaidIds = new Map(nodes.map((node, i) => [node.name, `n${i}`]));
    // Define nodes with labels
    for (const node of nodes) {
        let label = node.name.replace(/"/g, "'");
        if (node.isLlmCall) {
            label = `${label}<br/><i>LLM</i>`;
        }
        const [shapeOpen, shapeClose] = mermaidShape(node);
        lines.push(`    ${mermaidIds.get(node.name)}${shapeOpen}"${label}"${shapeClose}`);
    }
    // Define edges
    for (const node of nodes) {
        if (node.parent !== null) {
            lines.push(`    ${mermaidIds.get(node.parent)} --> ${mermaidIds.get(node.name)}`);
        }
    }
    return lines.join("\n");
}
//# sourceMappingURL=index.js.map