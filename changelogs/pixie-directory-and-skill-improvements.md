# `.pixie/` directory convention & skill improvements

## What changed

### 1. Unified `.pixie/` directory (config defaults)

All pixie artefacts now live under a single `.pixie/` directory by default:

- Observation DB: `.pixie/observations.db` (was `pixie_observations.db`)
- Datasets: `.pixie/datasets/` (was `pixie_datasets/`)
- New `root` config field (env var `PIXIE_ROOT`) controls the base directory.
- `db_path` and `dataset_dir` are derived from `root` unless overridden individually.

### 2. `enable_storage()` robustness

- Creates the database parent directory automatically (`os.makedirs` with `exist_ok=True`).
- Handles being called from an already-running async event loop by dispatching to a `ThreadPoolExecutor`.
- Already idempotent (no-op on second call).

### 3. `pixie test` subcommand

- Added `pixie test <path> [-k filter] [-v]` as a proper subcommand of the `pixie` CLI.
- The standalone `pixie-test` entry point still works for backward compatibility.

### 4. Test runner auto-resolves imports

- `_load_module()` now inserts the test file's parent **and** grandparent directories into `sys.path`.
- This means `from myapp import ...` inside test files works out-of-the-box (same as pytest).

### 5. Skill document (`SKILL.md`) rewrite

- `.pixie/` directory convention used throughout.
- Stage 1 (understand): expanded investigation checklist; MEMORY.md template documents only existing code, never agent-added code.
- Stage 3 (instrument): explicit rule — only wrap existing functions with `@observe`, never add new wrapper functions to the app.
- Stage 3: `enable_storage()` must be placed inside the app's startup function, not at module level. Includes ✅/❌ examples.
- Stage 4 (run tests): uses `pixie test`, not `pixie-test`.
- Stage 7 (investigate): 5-step investigation process with structured MEMORY.md sections including actual trace data, evaluator scores/reasoning, root cause analysis.

### 6. Spec and API reference updates

- `specs/agent-skill.md`: removed `<need specific instructions>` placeholders, added `.pixie/` convention, corrected command references.
- `references/pixie-api.md`: updated config table with new defaults and `PIXIE_ROOT` env var, changed `pixie-test` → `pixie test`.
- `README.md`: corrected `enable_storage()` placement example, updated commands and directory references.

## Files affected

| File                                                     | Change                                      |
| -------------------------------------------------------- | ------------------------------------------- |
| `pixie/config.py`                                        | Added `root` field, updated defaults        |
| `pixie/instrumentation/handlers.py`                      | Dir creation, async-safe `enable_storage()` |
| `pixie/evals/runner.py`                                  | `sys.path` auto-insertion                   |
| `pixie/cli/main.py`                                      | `pixie test` subcommand                     |
| `tests/pixie/test_config.py`                             | Updated assertions, new tests               |
| `.claude/skills/eval-driven-dev/SKILL.md`                | Full rewrite                                |
| `.claude/skills/eval-driven-dev/references/pixie-api.md` | Config table & command updates              |
| `specs/agent-skill.md`                                   | Removed placeholders, `.pixie/` convention  |
| `README.md`                                              | Corrected examples and commands             |

## Migration notes

- **Breaking default change**: The default observation DB path changed from `pixie_observations.db` to `.pixie/observations.db`. Existing users relying on the old path should either set `PIXIE_DB_PATH=pixie_observations.db` or move their DB file.
- **Breaking default change**: The default dataset directory changed from `pixie_datasets/` to `.pixie/datasets/`. Set `PIXIE_DATASET_DIR=pixie_datasets` to keep the old location.
- The `pixie-test` entry point still works but `pixie test` is now the recommended way to run tests.
