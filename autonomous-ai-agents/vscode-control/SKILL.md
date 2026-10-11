---
name: vscode-control
description: "Use when opening or driving VS Code on Windows."
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [vscode, windows, mcp, desktop-automation]
---

# Driving VS Code (Windows host, user 32672)

## When to Use
- The user asks to open a project/folder in VS Code, or to "give VS Code a task".
- The user asks to see, switch, or open an old VS Code chat session.
- You need VS Code's own view of a repo: diagnostics, symbol outline, integrated terminal.

## Launch & open projects
- `code` CLI lives at `C:\Users\32672\AppData\Local\Programs\Microsoft VS Code\bin` — prepend it to PATH in every terminal call.
- Open a project: `code "C:/path/to/project"`. Reuse the current window: `code --reuse-window "C:/path"`. Extra empty window: `code -n`.
- `code` returns before the window is mapped — verify with `powershell -Command "Get-Process Code | Where-Object {$_.MainWindowTitle -ne ''} | Select Id,MainWindowTitle"`; title reads `[folder] - Visual Studio Code`.
- A freshly launched window usually does NOT come to the front (Windows foreground lock). To front it: PowerShell `keybd_event(0x12,0,0,0)` + release (ALT tap), then `ShowWindow(h,9)`, `BringWindowToTop(h)`, `SwitchToThisWindow(h,true)`, `SetWindowPos(h,0,0,0,0,0,0x43)`; confirm `GetForegroundWindow() == h`.
- Freshly opened folders are in **Restricted Mode** (agent/Copilot features limited). The banner's `管理` button opens the trust editor, then click `信任` (or Ctrl+Enter). Verify by the panel text `你信任此文件夹`.

## Chat sessions (important)
- The chat panel's `会话` list is EMPTY while a folder is open. Old chats (e.g. `部署项目到远程Win11`) appear ONLY in an **empty window** (no folder open). To view/switch old chats: close the folder first, or open a fresh `code -n`.
- The `会话` filter menu lists session types (本地/Copilot/Claude/Codex/Copilot CLI/云) + status — it is not a workspace scope filter.
- Chat sessions live in `%APPDATA%\Code\User\globalStorage\state.vscdb` under key `chat.ChatSessionStore.index`; empty-window transcripts in `...\globalStorage\emptyWindowChatSessions\*.jsonl`; agent sessions in `...\globalStorage\github.copilot-chat\session-store.db`.

## MCP bridge — the reliable way to give VS Code tasks
- Extension `JuehangQin.vscode-mcp-server`: `code --install-extension JuehangQin.vscode-mcp-server`.
- Serves streamable HTTP on `http://localhost:3000/mcp`; the status-bar item `MCP Server: Off|<port>` toggles it. `vscode-mcp-server.defaultEnabled` defaults to **false** — set it true (plus `port`: 3000, `host`: 127.0.0.1) in `%APPDATA%\Code\User\settings.json` so it auto-starts.
- Register once: `hermes mcp add vscode --url http://localhost:3000/mcp` — interactive; answer `n` to "require authentication", then accept the tool list. Config lands in config.yaml under `mcp_servers`.
- 12 tools: list_files_code, read_file_code, create_file_code, replace_lines_code, move/rename/copy_file_code, get_diagnostics_code, search_symbols_code, get_symbol_definition_code, get_document_symbols_code, execute_shell_command_code.
- **Needs a folder open in VS Code**; otherwise every call returns "No workspace folder is open". The extension supports one workspace only.
- Newly added servers load into NEW sessions only: send `/reload-mcp` (gateway slash command) or `/new`.
- Verify without Hermes: POST JSON-RPC to the endpoint (initialize → notifications/initialized → tools/call) and read the SSE `data:` line; `hermes mcp test vscode` also works.

## Giving the VS Code agent a task (new Copilot experience)
- The chat panel is the "new Copilot experience": a Copilot CLI (agent harness) session backed by the user's BYOK model (DeepSeek via Vizards.deepseek-v4-for-copilot, wired through a loopback proxy).
- Type the prompt into the chat input: click the input (`coordinate=[~1000,700]` in window px), `type` with `delivery_mode="foreground"`, then click the send arrow at `[~1170,718]` (typing + Return alone did NOT submit).
- Permissions: the row under the input shows the level (`Manual permissions` / `Assisted permissions` / `Allow all`). Clicking the label (~`[1060,754]`) opens the picker; `Allow all` = runs tools without asking. Pending confirmation cards are separate and still need their own 「在此会话中允许」 click.
- **Diagnose silence with the logs, not the UI**: `%APPDATA%\Code\logs\<session>\agenthost.log` (agent host: `sendMessage called`, `Tool started/completed`, `Aborting session...`, `Session idle`) and `...\window1\exthost\Vizards.deepseek-v4-for-copilot\DeepSeek.log` (model calls incl. token counts). A first send can be aborted seconds later (observed: agent-host File Watcher IPC crashed, exit 3221225477) — resending works and needs no user action.
- The new harness does not record these turns in `chat.ChatSessionStore.index` / `session-store.db`; session state lives in `globalStorage\agent-host.db`.

## cua-driver quirks on VS Code (GUI fallback)
- `click` delivers fine in background mode; `type`/`key` are dropped by window class `Chrome_WidgetWin_1` → retry once with `delivery_mode="foreground"` (SendInput).
- `coordinate=[x,y]` is in **capture-image pixels**, not native desktop units (the driver adds the window origin). Prefer `element=N`; derive pixels from the capture when unavoidable.
