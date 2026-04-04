/**
 * Data-flow DAG parsing, validation, and Mermaid generation.
 *
 * The DAG schema is intentionally simple:
 *
 * - `name` is the unique lower_snake_case node identifier.
 * - `parent` (or legacy `parentId`) links nodes into a tree.
 * - `isLlmCall` marks nodes that represent LLM spans during trace checks.
 */
/**
 * Return whether `name` matches lower_snake_case DAG naming.
 */
export declare function isValidDagName(name: string): boolean;
/** A single node in the data-flow DAG. */
export interface DagNode {
    readonly name: string;
    /** Absolute or relative file path with symbol and optional line range. */
    readonly codePointer: string;
    readonly description: string;
    readonly parent: string | null;
    readonly isLlmCall: boolean;
    readonly metadata: Record<string, unknown>;
}
/** Result of a DAG or trace validation. */
export interface ValidationResult {
    valid: boolean;
    errors: string[];
    warnings: string[];
}
/**
 * Parse a DAG JSON file into a list of DagNode objects.
 *
 * Returns `[nodes, errors]` where `errors` is empty on success.
 */
export declare function parseDag(jsonPath: string): [DagNode[], string[]];
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
export declare function validateDag(nodes: DagNode[], projectRoot?: string): ValidationResult;
/**
 * Generate a Mermaid flowchart from the DAG nodes.
 */
export declare function generateMermaid(nodes: DagNode[]): string;
//# sourceMappingURL=index.d.ts.map