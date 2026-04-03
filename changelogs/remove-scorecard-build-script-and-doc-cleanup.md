# Remove Scorecard Build Script And Docs Cleanup

## What Changed

- Removed the obsolete frontend script `build:scorecard`.
- Switched frontend default build target from `scorecard` to `webui`.
- Updated frontend npm scripts so `npm run build` compiles only the Web UI artifact.
- Updated documentation to describe a results-first Web UI and clarify that scorecards are legacy-view only.

## Files Affected

- `frontend/package.json`
- `frontend/vite.config.ts`
- `frontend/README.md`
- `README.md`
- `docs/package.md`

## Migration Notes

- Use `npm run build` to produce `pixie/assets/webui.html`.
- Legacy scorecard build is no longer exposed as an npm script. For manual debugging only, run `VITE_BUILD_TARGET=scorecard vite build` from `frontend/`.
