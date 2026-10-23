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

## 实操全流程（2026-10-17 实测，给新文件夹发任务）
- **新文件夹先过信任**：横幅「管理」→ 工作区信任页 →「信任」（点击或 Ctrl+Enter）→ 页面变「你信任此文件夹」；
  信任对话框是编辑器区内浮层，**会盖住右下聊天输入框**——先关掉它（右上角 ✕，截图坐标约 (1054,111)）再点聊天框。
- **坐标约定（已实测）**：`coordinate=` 传**窗口截图像素（1:1）**，驱动自动加窗口原点（本次窗口原点=(462,111)）；
  SOM 的 element bounds 是“桌面原生坐标”，减法得截图坐标。**忽略结果里“乘 1.39”的英文提示**（误导，实际 1:1）。
- **发消息三步**（后两步必须前台，后台键鼠对 Chrome_WidgetWin_1 无效）：
  1. 前台点击聊天输入框（截图坐标 ~(1010,677)，1200x800 窗口）；
  2. 剪贴板粘贴：先 `Set-Clipboard -Value ([IO.File]::ReadAllText(<utf8文件>))`，再前台 `ctrl+v`（直接打中文风险大）；
  3. 点击发送：输入框右下角**蓝色圆形 ↑**，约截图 (1168,718)——那里图标密集，先放大截图确认再点（点在 Balance/麦克风旁边的空白会毫无反应）。
- **权限先检查**：输入框下方一行的权限标签（Manual/Assisted/**Allow all**）——新工作区默认可能是
  「Manual permissions」，agent 每步都会等批准；点该标签切到「Allow all」（菜单里选），正在等待的 run 会自动继续。
- **判断 agent 是否在干活**：`%APPDATA%\Code\logs\<最新会话>\agenthost.log` 看 `Tool started/completed`；
  持续有完成记录 = 跑得欢。

## cua-driver quirks on VS Code (GUI fallback)
- `click` delivers fine in background mode; `type`/`key` are dropped by window class `Chrome_WidgetWin_1` → retry once with `delivery_mode="foreground"` (SendInput).
- `coordinate=[x,y]` is in **capture-image pixels**, not native desktop units (the driver adds the window origin). Prefer `element=N`; derive pixels from the capture when unavoidable.
