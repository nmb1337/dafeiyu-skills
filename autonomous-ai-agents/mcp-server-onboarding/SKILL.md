---
name: mcp-server-onboarding
description: "Use when adding or fixing an MCP server in Hermes."
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [mcp, hermes, tools, integration]
---

# Onboarding an MCP server into Hermes

## When to Use
- The user asks to "add a plugin / extension / make yourself smarter" with an external service.
- A capability that should exist is missing after a config change.
- A configured MCP server connects, but its tools error out.

## Procedure
1. **Catalog first.** `hermes mcp catalog` lists one-click entries; `hermes mcp install <name>`
   writes `mcp_servers.<name>` into config.yaml, probes the server, and prints the tool count.
   Several entries need no credentials at all (`context7` library docs, `deepwiki` repo Q&A) —
   install the free ones before asking the user for anything.
2. **Custom server.** HTTP: `hermes mcp add <name> --url <endpoint>`. Stdio:
   `hermes mcp add <name> --command npx --args -y <package>` (`--args` must be last;
   `--env KEY=VALUE` for tokens). Node/npx must exist for npx-based servers.
3. **Answer the interactive prompts in the same call.** `hermes mcp add` asks
   "Does this server require authentication? [Y/n]" and then "Enable all N tools? [Y/n/select]".
   In a non-TTY shell it silently waits until the timeout kills it, and a run killed at a prompt
   saves nothing — pipe the answers and cap the wait:
   `printf 'n\n\n' | timeout 180 hermes mcp add <name> --url <endpoint>`, then confirm with `hermes mcp list`.
4. **Auth: never relay a code or token.** Hermes' MCP OAuth needs a real terminal — from a
   non-interactive shell it fails with "non-interactive environment and no cached tokens". Open a
   terminal window on the user's own desktop so they complete the flow locally:
   `powershell -Command "Start-Process powershell -ArgumentList '-NoExit','-Command','hermes mcp login <name>'"`.
   The same rule covers any CLI device flow (e.g. `gh auth login` after
   `winget install --id GitHub.cli -e`): their browser, their code, nothing through chat.
5. **Verify for real, not by config inspection.** `hermes mcp test <name>` must print
   "Connected" plus discovered tool names; `hermes mcp list` must show `✓ enabled`. For a
   streamable-HTTP server, probe it without Hermes via `scripts/probe-mcp-http.py`
   (`initialize` → `notifications/initialized` → `tools/list` or one `tools/call`).
6. **Activate in the live session.** New servers load into NEW sessions only — the user sends
   `/reload-mcp` (gateway slash command) or `/new`. Editing config.yaml mid-conversation does not
   hot-reload an open session, so do not report the tools as usable before that step. You can still
   prove the wiring yourself without waiting on the user: run a one-shot child session that uses the
   tool (`hermes -z "use the <server> tool to <cheap deterministic read>"`) — a fresh session loads
   the new servers, so a real tool result there means only the *current* chat still needs
   `/reload-mcp`, and a failure is yours to fix before handing over.

## Pitfalls
- **A "connected" server can still be useless.** Transport health is not tool health: a bridge
  into a desktop app answers every call with a domain error (e.g. "No workspace folder is open")
  until its host app is in the right state. Always fire one real tool call before telling the user
  it works, and read the error text — it usually names the missing precondition.
- **Prove it with a stdio probe, not with config inspection.** `$HERMES_HOME/scripts/probe-mcp-stdio.py`
  (`--cmd <exe> --arg=... [--call TOOL --args-json '{...}']`) runs initialize → tools/list → one
  real tools/call against any stdio server and prints the required parameter names. Use `--arg=-y`
  style: bare `--arg -y` makes argparse eat the flag and fail.
- **Prompted installs cancel on an empty line.** Non-TTY: `printf 'y\n'` (enable/confirm all) when
  nothing needs auth; a blank line is read as a cancel (`Cancelled — server not saved.`,
  `Installation cancelled.`). The same prompt shape governs `hermes skills install` (`Confirm [y/N]`)
  and the install runs long enough to be promoted to a background process — pipe the answer anyway,
  then re-read the state (`hermes mcp list`, `hermes skills list --source hub`) instead of trusting
  the exit code of a piped command.
- **A missing native binding kills npm-based servers.** On a Node too new for the prebuilt binary
  (e.g. Node 26 + `better-sqlite3`) npm falls back to node-gyp, which needs MSVC Build Tools —
  `Error: Could not locate the bindings file` at call time, or a hard install failure. Fix by
  installing the package locally so bindings resolve, or (better here) replace it with a small
  stdlib Python server: `C:\Users\32672\Apps\mcp-local\{sqlite,ffmpeg}_server.py` are the
  working models (pure stdlib + mcp SDK, no compiler needed). Register one with
  `printf 'y\n' | hermes mcp add <name> --command <venv>\Scripts\python.exe --args <abs path to the .py>`,
  then `hermes mcp test <name>`.
- **Python MCP SDK v2 renamed FastMCP.** `from mcp.server.fastmcp import FastMCP` raises
  `ModuleNotFoundError` on `mcp>=2` (it is now `mcp.server.mcpserver.MCPServer`). Pin `mcp<2`
  (`uv pip install "mcp<2"`) in the venv that runs hand-written servers unless migrating the code.
- **Check the platform claim in the README.** `video-creator/ffmpeg-mcp` loads and lists tools on
  Windows but every call returns "Not Support Platform" (macOS-only); the fix was to write a local
  ffmpeg wrapper server instead of trusting the tool list.
- **Probing leaves live children that lock the install.** Every `hermes mcp test`/probe spawns the
  server as a process waiting on stdin; after you replace a server, `rm -rf <install>` fails with
  "Device or resource busy" until they are killed. Filter the kill on the process **name** as well as
  the command line: a command-line-only match (`*ffmpeg-mcp*`) also matches your own shell command
  line and kills the terminal running the cleanup.
- **A local bridge dies with its host app** (an IDE extension's HTTP server, a desktop app's
  socket). When tools suddenly fail, check the host process first, not the Hermes config.
- **Credentials go in `env:`/`headers:`** (or the server's own auth flow), never into the chat or
  into a shell command line you echo. Do not read a cached token out of a credential store to
  paste it into config.
- **Tools are named `mcp_<server>_<tool>`** — search for that prefix when checking whether a
  server actually registered.

## References
- `references/skills-hub.md` — the Skills Hub: browse/search/install commands, the non-TTY confirm
  trap, hub-skill layout, and the install-few + demo-one hygiene rule.

## Worked example
A VS Code bridge (`JuehangQin.vscode-mcp-server` → `http://localhost:3000/mcp`, 12 tools: file
read/write, line replace, diagnostics, symbols, integrated-terminal shell) is documented end to end
in the user-owned skill `vscode-control`, including its `defaultEnabled: false` trap, its need for an
open folder, and the fact that adding the server to Hermes still requires `/reload-mcp`.
