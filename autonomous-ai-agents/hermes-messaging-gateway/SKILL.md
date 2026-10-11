---
name: hermes-messaging-gateway
description: "Use when wiring up or debugging a Hermes gateway platform."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [hermes, gateway, messaging, platforms, weixin, wechat, wecom, telegram, discord, slack, whatsapp, qr-login, troubleshooting]
    related_skills: [hermes-agent]
---

# Hermes Messaging Gateway

Connecting, configuring, and troubleshooting the gateway adapters that let Hermes talk to
messaging services (weixin, wecom, telegram, discord, slack, whatsapp, qqbot, signal, matrix, ...).
The bundled `hermes-agent` skill routes messaging questions to the docs pages; this skill carries the
operational procedure and the startup gates that actually block a platform from being served.

## When to Use

- The user wants to connect, enable, or re-enable a messaging platform on the Hermes gateway
  (WeChat/weixin, WeCom, Telegram, Discord, Slack, WhatsApp, QQ, Signal, Matrix, ...).
- A platform shows as enabled in `config.yaml` but no adapter starts, or the gateway refuses to boot.
- A QR-scan login is needed and the user cannot scan a terminal rendering.
- Messages arrive but are denied, or `hermes send` cannot resolve a target.

Not for writing a new platform adapter or plugin from scratch — that is Hermes development; see the
bundled `hermes-agent` skill and the contributor guide.

## Procedure

**1. Identify the platform's credential shape before touching anything.**
The docs page (`/docs/user-guide/messaging/<platform>`) explains the concept; the source is the truth
for env names, defaults, and gates:

- `gateway/platforms/<platform>.py` — adapter, required deps, QR login function, access policies.
- `gateway/config_env.py` — `_Cred(...)` entries map env var → config field. The first positional is
  the required group: a tuple of names means *any one of them* satisfies the requirement, so an
  either-or credential (token **or** account id) is expressed as `(("A", "B"),)`.
- `gateway/run.py::_platform_has_bot_credential` — what the gateway itself counts as "has a
  credential". This, not the docs, decides whether your platform starts.

**2. Install the adapter dependencies.**
Most non-trivial adapters live in the `messaging` extra (`aiohttp`, `qrcode`, `cryptography`,
`python-telegram-bot`, `discord.py`, `slack-bolt`). Run it with the RUNTIME venv python from the
checkout root — see `references/runtime-layout.md` for resolving that path:

```bash
cd "$HERMES_HOME/hermes-agent" && \
  "$HERMES_HOME/installs/<install-id>/environments/<env-hash>/venv/Scripts/python.exe" \
  -c "import pm; pm.sync_venv(['messaging'], explicit=True)"
```

A missing adapter dependency surfaces late and confusingly: a QR flow dying with
`ModuleNotFoundError: No module named 'qrcode'` is this step, not a bug in the adapter. `pm.sync_venv`
rebuilds the venv under a **new** env hash and repoints `facts.json`; every later command must use
the new venv path.

**3. Get credentials.** Bot-token platforms: the user pastes the token from the provider console. QR
platforms: drive the adapter's own login function and hand the user a scannable PNG — recipe in
`references/qr-login-flows.md`, runnable as `scripts/capture_qr_login.py`.

**4. Write the credential env vars into `$HERMES_HOME/.env`.** Account ids and policies in the open;
secrets belong in `.env` and must never be echoed into chat. See the `.env` pitfall below for how to
edit that file.

**5. Enable the platform.** `platforms.<name>.enabled: true` must exist in `config.yaml` (the setup
wizard writes it). Use `hermes config set` — never hand-edit `config.yaml`; a stray indent corrupts
the file and breaks the live gateway.

**6. Restart the gateway, then read the log.** Adapters are constructed at startup, so a newly
enabled platform requires a gateway restart. **The gateway cannot restart itself:** a
`hermes gateway restart|stop|uninstall` issued from a terminal inside the gateway process is refused
by a guard (SIGTERM would kill the command before it finished), so either ask the user to send
`/restart` in chat (the gateway slash command that drains and restarts gracefully) or run it from a
shell outside the gateway. Stage every config change first, then restart once. A change that only adds
tools (a new MCP server) does not need the full restart for an open chat — `/reload-mcp` re-scans MCP
servers into live sessions, `/reload-skills` does the same for skills. After it is back, read
`$HERMES_HOME/logs/gateway.log` — it names the exact reason a platform was skipped or refused.

**7. Verify all three levels.** "✓ <platform> connected" alone is not success:

| Level | What proves it |
|---|---|
| Adapter up | `✓ <platform> connected` in `gateway.log` |
| Gateway counts it | `Gateway running with N platform(s)` |
| Real round trip | An inbound message produces a reply |

For the third level the user must send the first message. `hermes send` cannot resolve a target until
the platform's channel directory has discovered one **from an inbound message** — a cold channel
directory makes `hermes send --to <platform>:<id>` fail with "Could not resolve". Ask the user to
message the bot, then read the log for the inbound line.

## External ingress: bridging a messenger Hermes has no adapter for

Hermes ships adapters for its own list; for anything else (a personal-account messenger driven by
OneBot/NapCat, a custom bot framework) do NOT write an adapter — put a small bridge in front of the
**OpenAI-compatible api_server**, which Hermes already serves.

- **Enabling it is credential-only**: `API_SERVER_KEY` in `$HERMES_HOME/.env` turns the platform on
  (`gateway/config_env.py::_api_server`); there is no `platforms.api_server.enabled` key to set.
  Defaults `127.0.0.1:8642` (`API_SERVER_PORT`, `API_SERVER_HOST`, `API_SERVER_MODEL_NAME`).
- Auth is `Authorization: Bearer $API_SERVER_KEY`; sessions are first-class
  (`POST /api/sessions`, `POST /api/sessions/{id}/chat`, `/v1/chat/completions`, `/v1/runs`).
- Under `multiplex_profiles: true` a secondary profile is served at `/p/<profile>/...`, and **that
  profile needs the same `API_SERVER_KEY` in its own `.env`** or the mirror refuses it.
- Per-sender capability tiers: `hermes profile create <name> --clone` (carries model creds; leaves
  messaging tokens behind), then `hermes -p <name> config set platform_toolsets.api_server '["web"]'`
  to give that tier search-and-chat only. Route by sender id in the bridge. **Also strip the cloned
  MCP servers** (`hermes -p <name> mcp remove <name> …`): MCP tools are injected into every platform
  toolset, so a narrowed toolset alone still leaves a tier able to call a local shell/file MCP server.
- Recipe, endpoint list and config shapes: `references/onebot-qq-bridge.md`.
- Group support belongs in the bridge, not in Hermes: only messages that @-mention the bot reach the
  agent, and each (group, member) pair keeps its own session so a guest never inherits the owner's
  tools. Feed the agent the text **and** image segments (next bullet); reply with the group umo
  (`<bot-id>:GroupMessage:<group_id>`).
- **A picture already posted in the group is invisible unless the bridge fetches it back.** The @-gate
  drops every non-mentioned message, so an image the user posted a few seconds earlier never reaches the
  agent, and a later `reply` segment carries only the target `id`, never the picture — the user sees
  themselves pointing at a picture while the agent gets "0张图". Fix it in the bridge, not by hand:
  resolve `reply` segments with a one-shot `get_msg` call over the WS server and append the quoted
  message's images, labelled so the agent can tell them from the current message's own attachments.
  Do **not** bulk-download group history to compensate: the user's instruction here is "forward each
  one, don't scrape the last N messages" — history pulls are noisy and hit CDN links whose `rkey`
  expires within minutes.
- **Sniff image bytes, don't trust the file name.** QQ stickers arrive as animated GIFs behind a `.png`
  file name, and CDN URLs carry no extension at all, so a name-based MIME guess ships an `image/gif`
  payload labelled `image/jpeg`. Read the magic bytes (GIF87a/GIF89a, `\x89PNG`, JPEG, RIFF/WEBP, BM)
  and fall back to the name only when nothing matches. Stickers (`sub_type: 1`) give no other hint:
  `summary` is always `[动画表情]` and `file_size` says nothing about the content. Verify the whole
  chain by POSTing the resulting data URL to the profile's own `/v1/chat/completions` and confirming the
  model describes the picture.
- **Tag every forwarded message with its origin.** Per-(group, member) sessions stop two people's
  *transcripts* from merging, but a bridge that forwards bare text still leaves the agent unable to tell
  *who* is speaking or *where*: every group and every member looks identical, so replies read as though
  they continue whatever was said last. Prepend one line to the message's text part, e.g.
  `(来源：QQ群 <gid>「群名」；发送者 <uin>「昵称」)`, taking the nickname from the event's
  `sender.card or sender.nickname` and the group name from a cached gid→name map (seed it from the bot
  framework's own DB — AstrBot keeps it in `umo_aliases.auto_name` — with a `get_group_info` action as
  fallback). Persist both maps in a small JSON next to the session map; never re-query per message.
- **Restarting the bridge kills the reply in flight.** The bridge is blocked waiting on the agent's
  answer while the agent works, so a restart issued during a turn loses that turn's reply (and the
  notify-on-complete hook will not help from inside a one-shot turn). Stage the change, then have a
  detached helper sleep past the expected turn length, re-read the listening pid from
  `netstat -ano | grep <port>`, kill it and `exec` the bridge again — see
  `scripts/restart-qq-bridge.sh`. Afterwards confirm there is exactly **one** bridge instance: the listen
  port plus one WS event appearing exactly once in the log. A Hermes-persisted background job that starts
  the bridge itself (visible as a `bash -lic … python … > logs/<bridge>.log` tree parented by the gateway)
  races the restart script and its `>` redirect **truncates** the shared log — two writers, one losing
  history, and the loser's bridge dies on the bind without leaving a traceback.
- **The same message arriving two or three times means your reply never landed, not that the user is
  spamming.** The bridge has already answered the bot framework by the time it tries to deliver, so a
  failed send leaves no trace in the agent's own transcript and the user simply sees silence. Check the
  bridge log for `[error] send to <umo> failed: HTTP Error 502` — the bot framework's OpenAPI answers
  502 while it is restarting, and it restarts on its own. Say in one line that the earlier answers were
  lost, then re-send; never quietly treat the repeat as a fresh question.
- **`$HERMES_HOME/scripts` is git-managed and uses advisory write leases.** More than one Hermes
  session touches `qq-bridge.py`, so before editing it take a lock:
  `python agentlock.py acquire scripts/qq-bridge.py --owner <who> --reason "..." --ttl 900`. If it is
  already held, run `status` to see who/why and wait for expiry rather than editing. Edit with targeted
  `patch` replacements only — rewriting the file wholesale silently drops another session's change
  (retry-on-failed-session-creation was lost this way once). Finish with `git commit`, a new line at the
  top of `PROGRESS.md`, and `agentlock.py release <lock_id>`. Full text: `scripts/AGENTS.md`.
- **Images ride the same path — the session chat route is multimodal.** `POST /api/sessions/{id}/chat`
  accepts `message` as a string *or* as a content-part array (`{"type":"text",…}` plus
  `{"type":"image_url","image_url":{"url":"data:image/…;base64,…"}}`, ≤5 MB), and the profile's own
  model reads the image natively — no vision provider to configure, no OCR step. A bridge that
  forwards only text silently drops every picture the user sends. Resolution chain for OneBot `image`
  segments (local path → CDN url → `get_image` action) and the synthetic-image test: 
  `references/onebot-qq-bridge.md`.
- **Feed the bridge from the bot client's WebSocket server, not its reverse-HTTP client.** A
  reverse-HTTP (`httpClients[]`) target can sit enabled in the client's config and deliver nothing at
  all — no events, not even heartbeats — while that client is demonstrably online for its other
  clients. Subscribe to `websocketServers[]` instead (e.g. `ws://127.0.0.1:3001`), keep the HTTP route
  as a second entry point into the same handler, dedupe by `message_id`, and skip
  `user_id == self_id` because the WS server usually reports the bot's own sends back
  (`reportSelfMessage: true`).
- **Prove the messenger side from inside it before blaming the bridge.** Connect to that WS endpoint
  and call OneBot actions: `get_status`, `get_login_info`, `get_group_list`. `get_login_info` is the
  check that catches an account silently reassigned by a QR scan with the wrong phone, and its uin is
  the value the @-mention gate must compare against. Details in `references/onebot-qq-bridge.md`.
- The bot framework's send API lives on its *dashboard* port (read it from that framework's config)
  and its key is stored hashed in the framework's DB, so it cannot be recovered or read back. After
  any framework restart or key change, re-point every consumer that stored a URL+key pair and finish
  by sending one real message and requiring HTTP 200 — a stale pair is silent otherwise.
- **Sending a picture out of the bot is a separate path from text.** The bridge sends text only, and AstrBot's OpenAPI `image` part demands an `attachment_id` of an uploaded attachment, so neither can post a local file. What works is calling the bot client's own OneBot WebSocket (e.g. `ws://127.0.0.1:3001`) with `send_group_msg` and an image segment `{"type":"image","data":{"file":"file:///C:/abs/path.png"}}`; it answers with a matching `echo` and `retcode: 0`. Hermes's bundled python has no websocket library — run it with the bot framework's venv python (AstrBot's ships `websockets`).
- **A `502 Bad Gateway` from the framework's send API means the reply never reached the chat**, and it is easily mistaken for the user ignoring you: the bridge logs `[error] send to ... failed` while the agent believes it answered. If a user repeats the same question, check the bridge log for send failures before re-answering, then test the send path with one real message.
- **Price the bridge for minutes-long turns, not chat turns.** A task forwarded from a messenger runs
  dozens of tool calls, so the api_server call needs a timeout in the tens of minutes; post one short
  "收到，我在处理，做完把结果发出来" if the turn is still running after ~25 s (and cancel that timer when
  the reply lands). Never let the call's `except` branch post its raw exception into the user's chat:
  a client-side `timed out` lands in a live group. A timeout does not stop the server-side turn, so
  recover the finished answer from the session transcript and send that instead. Recipe, completion
  signal and `scripts/forward_session_reply.py`: `references/onebot-qq-bridge.md`.
- **One turn at a time per chat.** Two messages arriving together for a chat that has no session yet
  both call `POST /api/sessions`; the host answers one `201` and one `400` (duplicate), and the loser's
  error branch posts that raw 400 into the user's chat. Serialize the whole turn behind one lock per
  chat key, and retry session creation once with a unique title suffix before giving up. Fingerprint in
  the host's access log: two `POST /api/sessions` in the same second, `201` + `400`.

## Pitfalls

- **`dm_policy`/`group_policy: open` aborts gateway startup** unless `GATEWAY_ALLOW_ALL_USERS=true`
  (or the platform's own `<PLATFORM>_ALLOW_ALL_USERS`). The gateway refuses to boot entirely, so it
  reads like a broken install. Prefer `allowlist` plus the user's own id: `open` exposes a personal
  agent to anyone who finds the bot, which is exactly what this gate exists to prevent.
- **`multiplex_profiles: true` requires the platform's TOKEN env var, not just an account id.** Under
  multiplex the startup check reads `platform_config.token`, populated only from the token env var.
  An id-only config is skipped silently:
  `Skipping <platform> on default profile: no bot credential in this profile's secrets.` Check
  `multiplex_profiles` in `config.yaml` before concluding an id-only setup should work.
- **A host-wide proxy in the process environment makes the gateway mute whenever that proxy is off.**
  On a machine running a local accelerator (Clash/V2Ray-style, e.g. `127.0.0.1:7890`) the gateway
  inherits `HTTP_PROXY`/`HTTPS_PROXY`, so every adapter — and the model call itself — dies the moment
  the user quits the accelerator: chats get no reply and a one-shot `hermes -z "ping"` prints nothing
  at all, with no error in the gateway log. Reproduce before changing anything: run
  `HTTP_PROXY=http://127.0.0.1:7999 HTTPS_PROXY=http://127.0.0.1:7999 hermes -z "ping"` (dead port) —
  empty output confirms it while `NO_PROXY=127.0.0.1,localhost,<provider-host>` added to the same
  command answers normally. Fix in two independent layers, then restart the gateway: set
  `gateway.trust_env: false` (`hermes config set gateway.trust_env false`; `config.yaml` documents
  this exact case — a scheduled task picking up a local proxy that isn't running) so the platform
  adapters ignore the proxy env, and write `NO_PROXY` **and** lowercase `no_proxy`
  (`127.0.0.1,localhost,::1,<provider-host>`) into `$HERMES_HOME/.env` **plus** set it as a user-level
  Windows environment variable so the desktop app and later processes inherit it. Keep the list
  minimal — loopback plus the LLM host — so the traffic that genuinely needs the proxy (web search,
  GitHub) still uses it; confirm the direct route works for the platform's own hosts first
  (weixin's `qyapi.weixin.qq.com` answers 200 in ~0.2 s with `--noproxy '*'`) before flipping
  `trust_env` off, or the fix trades a proxy dependency for an adapter that cannot connect.
- **`.env` and other credential files are write-protected from `patch`/`write_file`.** Edit them
  through the terminal — a Python read/replace that asserts the anchor string occurs exactly once —
  then verify with a grep that masks the value. Do not let `write_file` rewrite a secrets file from a
  read that may have been redacted.
- **Access-policy allowlist ids are inbound-sender ids, not login-identity ids.** A QR login returns
  the account's own `user_id`; the value the policy filter compares is the inbound message's
  `from_user_id`. When the allowlist silently denies, grep the gateway log for the deny line — it
  prints the real sender id — and add that instead of guessing.
- **Print only the keys you need from an unfamiliar config file.** These configs embed whole
  UI/theme sections, so a recursive dump of one burns thousands of characters of CSS tokens before you
  reach the field you wanted; and a large `*.json` sitting beside the config is usually a cache, not
  config (AstrBot's `data/plugins.json` is a multi-MB plugin-market catalogue — its digit-laden repo
  names also make it a port-string false-positive magnet). Check a file's size first, then extract
  named keys.
- **Never print a credential.** Read it from disk programmatically, write it into `.env`, and report
  only that it is set. Delete any scratch capture file that received a login result — it holds the
  token.

**Say the group-message limitation up front.** QR-login bot identities (personal WeChat `...@im.bot`
via iLink) generally receive no ordinary group events, so group policies have nothing to act on.
Volunteer this before the user spends an evening debugging a working DM setup. Leave group policy at
its `disabled` default.

## Support files

- `references/qr-login-flows.md` — turning a terminal QR login into a scannable image in chat.
- `references/runtime-layout.md` — where the venv, `facts.json`, logs and `.env` live; which
  interpreter to use for Hermes' own packages.
- `references/onebot-qq-bridge.md` — bridging OneBot/NapCat (or another bot framework) into Hermes
  through the api_server, with per-sender profile tiers.
- `scripts/capture_qr_login.py` — capture a QR-login URL from an adapter and render it to PNG.
- `scripts/forward_session_reply.py` — wait out a long session turn and deliver its final answer to a
  QQ target after the bridge's own request already gave up.
