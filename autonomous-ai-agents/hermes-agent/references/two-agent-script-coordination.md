# Two Hermes sessions co-editing the same files

When two Hermes sessions (e.g. a WeChat DM session and a QQ-bridge session) both hold
full tools on one host, they edit the same scripts and silently clobber each other:
last writer wins, and a `write_file` full rewrite drops the other side's fresh patch.
This happened for real (a session-side retry fix was lost to a full rewrite).

## The protocol that works (no daemon, plain files)

1. **Put the shared dir under git** — `git init` in the scripts dir, commit the current
   state immediately. History is the conflict record; `git diff/log` is how the other
   side sees what changed.
2. **Advisory file leases** — an `agentlock.py` in the shared dir
   (`acquire <path> --owner <name> --reason "..." --ttl 900`, `release <lock_id>`,
   `status`, `prune`). Leases are per-resource JSON files with a TTL; a conflicting
   acquire exits 1 and prints holder + reason + expiry. See the `agentlocks` project for
   the full-featured version of the same idea.
3. **Patch-only edits** — never `write_file` a file another agent just touched; always
   targeted `patch` replacements.
4. **Commit every change** with a message, then add one line to a shared rolling
   `PROGRESS.md` (newest first: time | who | file | what | impact).
5. **Write the rules into `AGENTS.md` in that dir** so any agent (Hermes, Codex,
   Claude Code) that opens it reads the same contract. Note Hermes only auto-injects
   `AGENTS.md` when the cwd *is* that directory — so also put a one-line pointer in
   persistent memory (memory is shared by all sessions of a profile), which guarantees
   every session loads it regardless of cwd.

## Talking to the other session directly

The other Hermes session is reachable through the api_server: find its id in
`$HERMES_HOME/qq_bridge_sessions.json` (or `/api/sessions`) and POST
`{"message": "..."}` to `http://127.0.0.1:8642/api/sessions/<sid>/chat` with the
`API_SERVER_KEY` bearer. Its reply comes back in the HTTP response — a clean
agent-to-agent channel. Label the note as coming from the other session, not the user,
and ask for a one-line confirmation so the turn stays short.

## Restart safety

Restarting a bridge/gateway kills in-flight turns, so the caller's reply is lost.
Before restarting: sample the target session's `message_count` twice ~10s apart; if it
is static the session is idle. If a reply does get lost, fetch the last assistant
message from `/api/sessions/<sid>/messages` and deliver it yourself.
