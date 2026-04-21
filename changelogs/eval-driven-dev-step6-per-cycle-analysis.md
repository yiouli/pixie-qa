# Eval-Driven-Dev Per-Cycle Step 6 Requirement

## What changed

- Updated the shipped `skills/eval-driven-dev/SKILL.md` to require Step 6 completion for each `pixie test` cycle before any more code edits or reruns.
- Updated `skills/eval-driven-dev/references/6-analyze-outcomes.md` with the same iteration rule and an explicit anti-pattern covering abandoned earlier result directories.
- Clarified the root [README.md](/home/yiouli/repo/pixie-qa/README.md) workflow summary so the rerun discipline is visible in the top-level project docs.

## Files affected

- `skills/eval-driven-dev/SKILL.md`
- `skills/eval-driven-dev/references/6-analyze-outcomes.md`
- `README.md`

## Migration notes

- No API changes.
- Skill users should expect the agent to finish Step 6 on each `pixie_qa/results/<test_id>` directory before starting another `pixie test` cycle.
