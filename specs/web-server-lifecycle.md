# web server lifecyle

Currently, the server for web UX is started by `pixie start`, and it's stopped whenever the `pixie start` command is killed, and underneath, the server manages a server.lock file to prevent duplicated server running when `pixie start` is called while server is live.

However, this design is problematic when `pixie` is being used by a coding agent. Coding agent is having a hard time keeping a process running in the background, and if the agent run the process detached, there's a cleanup difficulty.

## Redesign server lifecycle management

To solve this, the `pixie start` command should start the web server in a separate, detached process; and a `pixie stop` command should be added for stopping the server.

During detached startup, the parent process must preserve a freshly written `server.lock` long enough for the child process to finish binding and answer `/api/status`. Treating that lock as stale before the status endpoint is reachable causes false startup timeouts: the child keeps serving, but `pixie start` reports failure and never opens the browser.

The server should add an additional endpoint for shutdown request - when a shutdown request is received, the server should disconnect all client, kill itself and cleanup. `pixie stop` command should simply fire the request to the existing server.

## `pixie start` on none init command

Additionally, any `pixie ...` command other than `pixie init` should automatically do the `pixie start` (without webui open) at the beginning when called.
