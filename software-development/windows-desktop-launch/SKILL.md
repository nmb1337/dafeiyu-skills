---
name: windows-desktop-launch
description: "Use when opening a Windows app or project window."
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [windows, vscode, launch, desktop, project-window, code-cli]
---

# Launching Desktop Apps & Project Windows (Windows host)

Hermes opens windows for the user; it does not write the code. This skill governs that class of
task: get the right app or project folder on screen, verify it, and leave the user in control.

## When to Use
- The user asks you to open an application, a project folder, or a project window on this Windows host.
- The user asks which projects they previously opened in an editor.
- A task needs the local coding stack (editor, extensions) identified without launching any window.

## Standing workflow (user preference)
- Existing project → open **that project's own window**: `code -n "<path>"` for a fresh window, `code "<path>"` to reuse the last one.
- New project → wait for the user's explicit go-ahead before creating anything, then open a new window/folder.
- After opening, report the path/window you opened so the user can confirm it on screen.
- Do not start editing files in this flow unless the user asks for edits.
- Do not open windows unprompted: a GUI appearing on the user's desktop is intrusive. Open when asked, or ask first when the destination is ambiguous.

## VS Code
- CLI lives at `%LOCALAPPDATA%\Programs\Microsoft VS Code\bin\code`. In this bash/MSYS terminal, prepend `/c/Users/<user>/AppData/Local/Programs/Microsoft VS Code/bin` to PATH, then call `code ...`.
- Focus-safe probe: `code --version`. A benign stderr line like `crashpad ... CreateFile ... (0x2)` is normal — the version still prints, ignore it.
- Already running? `tasklist | grep -i code.exe`.
- Installed extensions reveal the user's coding stack (Copilot Chat, BYOK model extensions): `code --list-extensions`, or the directories under `%APPDATA%\Code\User\globalStorage\`.
- A folder opened for the first time comes up in **受限模式 / Restricted Mode**: extensions are disabled (the banner states how many), so the chat/agent panel is crippled until the folder is trusted. Trust it when the user wants that window usable: click the banner's **管理** (Manage) → the **工作区信任** editor opens → click **信任** (Ctrl+Enter). Verified success: that editor's heading flips to 「你信任此文件夹」, the banner clears, and the status bar gains the git branch; extensions may still want a window reload.
- A Desktop `.lnk` for a project resolves to the real working dir, which is often NOT the repo path: `(New-Object -ComObject WScript.Shell).CreateShortcut('<lnk>')` → `.TargetPath` / `.Arguments` / `.WorkingDirectory`.

## Finding projects the user already opened in VS Code
All under `%APPDATA%\Code\User\`:
- `globalStorage/state.vscdb` (SQLite): `SELECT value FROM ItemTable WHERE key='history.recentlyOpenedPathsList'` returns JSON of recent folders/workspaces (`folderUri` / `workspace`). Open it read-only so a running VS Code is undisturbed: `sqlite3.connect(f"file:{path}?mode=ro", uri=True)`.
- `globalStorage/storage.json` → `windowsState.openedWindows[]` and `lastActiveWindow`; entries carry `folder` / `workspace` / `backupPath`.
- `User/workspaceStorage/*/workspace.json` → one directory per opened `.code-workspace`.
- `globalStorage/github.copilot-chat/session-store.db` (SQLite `sessions` table: `cwd`,
  `repository`, `summary`) → maps a chat session to its repo, and
  `globalStorage/github.copilot-chat/memory-tool/memories/*.md` holds the project notes the chat
  agent wrote itself (install path, start/stop commands, deploy location) — often the fastest way
  to learn what an unfamiliar project is and where its working copy lives.
- `globalStorage/emptyWindowChatSessions/*.jsonl` → chat sessions created with **no folder open**
  (`customTitle` is the user-visible name). These are NOT listed under a project folder window's
  session list, so never promise the user will find them there — say where the session actually
  lives and offer to open it from that window.
- Chat **history** is enumerated from `chat.ChatSessionStore.index` in the state DB (title,
  `lastMessageDate`, `isEmpty`) — cheaper and more complete than clicking through the UI.
- The Chat view's **会话 / Sessions panel DOES list past chats**, but only while **no folder is
  open**: with a folder open that list stays empty and a search in it returns 0 rows, which reads
  as "my chats are gone". The working route to show or reopen a past chat: get an empty window
  (`code -n`, or 文件 → 关闭文件夹) → the chats appear under 会话 → click one. Its filter menu lists
  session types (本地/Copilot/Claude/Codex/Copilot CLI/云) × states (已完成/正在进行/需要输入/失败); it is
  not a workspace scope control, so never cite those filters as evidence about folders.
- The "new Copilot experience" agent-harness store is `globalStorage/agent-host.db` (`sessions_v2`,
  `session_chats`) — read it when a chat in that panel appears to do nothing.
- `chat.currentLanguageModel.panel` in the state DB is the chat panel's model, which is independent
  of the main agent model — read it instead of assuming.

Pitfall: the recent-paths key can be missing entirely (fresh install or cleared state). Empty
history is **not** evidence the user has no projects — ask for the path or name and open that;
never tell the user their projects do not exist.

## Fronting the window — a window behind others reads as "nothing happened"
The user is usually on a messaging platform and cannot see this machine, so an opened window must
be raised and verified on screen, not just launched.
- `(New-Object -ComObject WScript.Shell).AppActivate($pid)` can return **True** while nothing moves,
  and `SetForegroundWindow` from a process that is not already foreground is refused by Windows.
  Neither return value is proof of anything.
- Verified sequence: synthetic ALT press/release (unlocks the foreground rule) →
  `AttachThreadInput(current, foreground-thread)` → `ShowWindow(SW_RESTORE)` → `BringWindowToTop` →
  `SwitchToThisWindow` → `SetWindowPos(SWP_SHOWWINDOW|SWP_NOSIZE|SWP_NOMOVE)` → `SetForegroundWindow`.
- Run `scripts/front-window.ps1 -ProcessId <pid>` (or `-TitleLike <substring>`), then confirm with
  `GetForegroundWindow() == target hwnd` — not with the call's return value.
- Find the window first: `Get-Process Code | Where-Object {$_.MainWindowTitle -ne ''} | Select-Object Id, MainWindowTitle | Format-List`.
  The title carries the opened folder (`<folder> - Visual Studio Code`), which is the cheap proof of
  what actually got opened.
- Capture to show the user: `scripts/screenshot.ps1 -Out <path>`, delivered as `MEDIA:<abs path>`.
  Two captures with identical `md5sum` mean the screen truly did not change — retrying the same
  input is then pointless; change rung instead.

## When GUI automation is genuinely needed (computer_use)
- Targeting one specific window needs **both** `pid` and `window_id`: a `capture` with only `pid`
  comes back 0×0 with "capture targeting requires both pid and window_id". Call `list_windows`
  first (it returns `app_name` / `pid` / `window_id` / `title` / `z_index`) and pass the pair;
  matching by window title alone is fragile when several windows share a pid.
- A `mode="som"` capture of an Electron/Chromium app can return **only window chrome** on the first
  call; the next capture returns the full UIA tree. The untruncated tree is dumped to JSON under
  `$HERMES_HOME/cache/computer_use/` — `read_file`/`search_files` that file for labels past the
  inline cap instead of burning another capture.
- `coordinate=` is in **screenshot pixel space**; the wrapper scales it to native desktop
  coordinates. Passing native/window coordinates therefore double-scales the click outside the
  window (a requested x=1452 was posted at x=1992). Prefer `element=` indices from the last
  capture; derive coordinates from the capture image only.
- Background clicks into Chromium/Electron return `effect: "unverifiable"` — take a fresh capture
  and read it before considering any retry.
- VS Code's window class `Chrome_WidgetWin_1` **drops background text input**: `type` fails with
  `code: "background_unavailable"` and only lands with `delivery_mode: "foreground"`.
- The same class silently swallows some **background clicks**: a click on a native dialog button
  returned `ok: true` / `effect: "unverifiable"` and did nothing, while re-issuing the SAME click
  with `delivery_mode: "foreground"` applied it. A fresh capture that shows no change is the cue to
  climb to foreground once — not to click again in the background.
- Verify a dialog action by the dialog's own text (the trust editor's heading changed to
  「你信任此文件夹」), never by the action's `ok` / return value.
- **Verify an in-app "restart / relaunch" click by process identity, not by its banner.** Compare the
  target process's PID and start time before and after
  (`Get-CimInstance Win32_Process | Select ProcessId,Name,CreationDate`): a new PID with a fresh
  CreationDate is the proof; the app's own "restarting…" toast screenshot is not. The managing app
  itself may keep running while the child it manages is the thing that restarted — check the child.
- **Launching a desktop app with no CLI: go through its shortcut** —
  `cmd.exe /c start "" "C:\Path\App.lnk"`; resolve the target first
  (`(New-Object -ComObject WScript.Shell).CreateShortcut('<lnk>')` → `.TargetPath`) when you need to
  know what it will run or which process name to expect, then locate its window via `list_windows`
  or `Get-Process <name> | Select Id,MainWindowTitle` before driving it.
- When the CLI genuinely cannot reach the target, do not imply it is impossible: check the app's
  own state files first — most "GUI-only" steps (reopening a past chat, selecting a session) have a
  state-file route or an empty-window route.

## Handing a task to the app's own AI panel (e.g. VS Code chat)
The user may ask you to deliver a prompt to the editor's own agent ("发消息给 VS Code，让它改代码").
That is a GUI write plus a submit, and the submit is the part that fails silently.
1. Open the panel by clicking the title-bar **切换聊天** button by `element` index (from a `capture`).
   `Ctrl+Alt+I` did not open it — the driver maps alt→option; do not rely on that shortcut.
2. Click the input's **placeholder text line** to focus it. Clicking the row's left edge instead
   opens the mode picker (交互式 / 计划 / Autopilot) and the text you then type lands nowhere —
   `escape` out of the menu and retype.
3. `type` the prompt with `delivery_mode="foreground"`, on ONE line: a newline in the input submits
   early, so join points with 。 or ；.
4. Submit by clicking the **send arrow** at the input's bottom-right. A foreground `return` did not
   submit.
5. **Verify dispatch before reporting the task as started.** A user bubble in the transcript is not
   proof: re-read the stores above (`chat.ChatSessionStore.index`, `session-store.db` turns,
   `agent-host.db`). If none gains a row for your message, the request never left the UI — tell the
   user that, name the in-app step that unblocks it (dismiss the panel's onboarding popup, check the
   assistant's sign-in/status, press Enter themselves), and do not claim the app is working on it.
6. **In-app approval/permission prompts stay the user's to click.** Say which permission mode the
   panel is in instead of promising unattended progress.

## Support files
- `scripts/front-window.ps1` — unlock the foreground rule and raise a window by PID or title.
- `scripts/screenshot.ps1` — virtual-screen capture to PNG, prints the path for `MEDIA:`.

## Pitfalls
- Never name a PowerShell parameter `$Pid`/`$PID` — it collides with the read-only automatic
  variable and the script dies on invocation.
- Chinese window titles and console text come back mangled through bash→PowerShell capture
  (codepage). That is display-only: parse the underlying value, do not try to "fix" the encoding.
- Do not launch the app again to "check" whether it is open — query the process list; duplicate
  windows are easy to leave on the user's desktop.
- When the user offers a cause ("restricted mode is why you cannot see X"), test it against the
  app's own state/UI and report what you actually observed. Do the fix if it is worth doing anyway,
  but never confirm an unverified theory — it sends the user chasing the wrong thing.

## General rules
- Prefer CLI plus state files over screenshots; escalate to GUI automation only for steps that have no CLI.
- Native Windows tools (node, git, `code`) need forward-slash native paths (`C:/Users/...`); MSYS `/c/...` paths are not translated for them, while bash builtins accept either.
- Long-running GUI launches return immediately; verify the window by asking the user or by re-reading the app's state files, not by assuming success.
- This user asks for visual proof and writes in Chinese: answer short and in Chinese, and attach a
  window screenshot (`scripts/screenshot.ps1` → `MEDIA:<abs path>`) with any claim about what is on
  screen. Separate what you verified from what you could not.
