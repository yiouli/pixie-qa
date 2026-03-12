# Skill v2: setup-vs-iterate, eval boundary, rootdir discovery

## What changed and why

### 1. Renamed default root directory from `.pixie` to `pixie_qa`

The dot-prefix `.pixie` caused Python import resolution issues (treated as hidden
directory, confused with relative imports). Renamed to `pixie_qa` — a plain,
importable name that avoids these problems.

- `pixie/config.py`: `DEFAULT_ROOT` changed from `".pixie"` to `"pixie_qa"`
- All documentation updated: SKILL.md, pixie-api.md, specs/agent-skill.md

### 2. Test runner rootdir discovery (pytest-style)

The old `_load_module()` in `pixie/evals/runner.py` added the test file's parent
and grandparent to `sys.path`. This broke for test files nested deeper than two
levels from the project root (e.g. `pixie_qa/tests/test_foo.py`).

Rewrote `_load_module()` to use rootdir discovery: `_find_rootdir()` walks up from
the test file directory looking for `pyproject.toml`, `setup.py`, or `setup.cfg` —
the same strategy pytest uses. The discovered rootdir is added to `sys.path`,
making project-root imports work regardless of test file depth.

### 3. SKILL.md: setup vs. iteration checkpoint

Added a "Setup vs. Iteration" section at the top of the skill. When the user says
"setup QA" / "set up evals" / "add tests", the agent now stops after Stage 6
(first test run) and reports results without fixing anything. It only proceeds
to Stage 7 (investigate and fix) if the user explicitly confirms.

Previously, the skill had no checkpoint — the agent would eagerly iterate on
failures, modifying application code without being asked.

### 4. SKILL.md: eval boundary guidance

Added "The eval boundary: what to evaluate" section. Evals focus on LLM-dependent
behaviour only (response quality, routing decisions, prompt effectiveness). Tool
implementations, database queries, keyword matching, and other deterministic logic
are explicitly out of scope — they should be tested with traditional unit tests.

The investigation section (Stage 7) now classifies failures into "LLM-related"
and "non-LLM" categories with guidance on how to handle each.

### 5. SKILL.md: instrument production code only

Strengthened Stage 3 with explicit rules against creating wrapper functions or
alternate code paths for eval purposes. Added a ❌ WRONG example showing the
anti-pattern (creating `run_for_eval()` that duplicates `main()` logic) and
✅ CORRECT examples showing `@observe` on existing functions and
`start_observation` context manager inside existing functions.

## Files affected

| File                                                     | Change                                            |
| -------------------------------------------------------- | ------------------------------------------------- |
| `pixie/config.py`                                        | `DEFAULT_ROOT = "pixie_qa"`                       |
| `pixie/instrumentation/handlers.py`                      | Docstring updated                                 |
| `pixie/evals/runner.py`                                  | New `_find_rootdir()`, rewritten `_load_module()` |
| `tests/pixie/test_config.py`                             | Updated assertions for `"pixie_qa"` default       |
| `tests/pixie/evals/test_runner.py`                       | 8 new tests (rootdir + import resolution)         |
| `.claude/skills/eval-driven-dev/SKILL.md`                | Major rewrite (issues 3, 4, 5 + rename)           |
| `.claude/skills/eval-driven-dev/references/pixie-api.md` | Config table updated                              |
| `specs/agent-skill.md`                                   | `.pixie` → `pixie_qa` throughout                  |

## Migration notes

- **Breaking default change**: The default root directory changed from `.pixie` to
  `pixie_qa`. Existing projects using the old default should either:
  - Set `PIXIE_ROOT=.pixie` to preserve the old location, or
  - Rename the directory: `mv .pixie pixie_qa`
- **Test runner**: `_load_module()` now uses rootdir discovery instead of
  parent/grandparent. No action needed — this is backwards compatible and more
  reliable.
- **Skill behaviour**: Agents following the updated SKILL.md will stop after
  initial test setup and ask before iterating on failures.
