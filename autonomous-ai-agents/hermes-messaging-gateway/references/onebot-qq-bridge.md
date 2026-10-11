# Bridging OneBot / NapCat (or any bot framework) into Hermes

Use when the target messenger has no Hermes adapter and is already served by a bot framework
(AstrBot + NapCat is the common Chinese-community shape). Do not write a Hermes adapter: put a small
bridge in front of the api_server and let an existing profile answer.

## Topology

```
Messenger client (e.g. NapCat inside QQNT)
  ├─ WebSocket client -> existing bot framework (keep; it owns the account login)
  └─ HTTP client (反向 HTTP) -> bridge  POST http://127.0.0.1:<port>/qq     (add this)
bridge: OneBot event -> pick Hermes profile by sender -> POST api_server session chat
reply : existing framework's send API (or OneBot send_private_msg) -> back to the messenger
```

## Messenger side (NapCat example)

- Config: `<NapCat install>/config/onebot11_<bot_uin>.json` (`napcat.json`, `napcat_<uin>.json`
  alongside). `network.httpClients[]` = reverse-HTTP POST targets; `network.websocketServers[]` /
  `websocketClients[]` = WS. The plugin runs inside the messenger client process, so its WebUI port
  is held by that process, not by a standalone service. A config edit needs a client restart —
  verify the reload yourself instead of asking the user to test by hand: watch the bridge for any
  inbound event. Silence there proves only that *this* feed is dead, never why it is dead — do not
  conclude "the client never re-read the file". An enabled `httpClients[]` target has been observed
  delivering nothing at all (no message events, no heartbeat meta-events) while the client was online,
  logged in, and serving its other clients. When the bridge sees nothing, switch its ingestion to the
  client's WebSocket server (next section) rather than iterating on the HTTP path.
 - **Restart the client through its own launcher, not by starting the boot binary.** The launcher
 script (`launcher-user.bat`; `launcher.bat` self-elevates behind a UAC prompt) exports the
 `NAPCAT_*` env vars and rewrites `loadNapCat.js` before booting. Running `NapCatWinBootMain.exe`
 directly still starts the messenger client but attaches no plugin (no WebUI port, no OneBot) — the
 restart then looks like it failed for no reason. Start the `.bat` as a detached background process
 so it survives your shell.
 - Login: the boot log lists accounts that have a saved session and accepts `-q <uin>` for quick
 login. With no saved session for that account it falls back to QR and writes the image to
 `<NapCat install>/cache/qrcode.png` — send that PNG to the user and say to scan it with the BOT
 account's phone; scanning with their personal account silently reassigns the bot identity.
 - If the client survives `Stop-Process` / `taskkill /F` (same PID and start time after a reported
 success), do not loop kills — relaunch through the launcher once and re-check the WebUI port.
 - OneBot v11 events arrive as JSON with `post_type: message`, `message_type: private|group`,
  `user_id`, `message` (string or segment array — take the `text` segments and resolve the `image`
  segments as below). Ignore the bot's own `user_id` and `reportSelfMessage` echoes.

## Event feed: subscribe to the client's WebSocket server

The reverse-HTTP target is best-effort; the WebSocket server is the feed that actually carries events.
NapCat's `network.websocketServers[]` (default `127.0.0.1:3001`, `reportSelfMessage: true`) accepts
additional clients, so point the bridge at it — `websockets` already ships in the Hermes venv:

```python
from websockets.sync.client import connect
with connect("ws://127.0.0.1:3001", open_timeout=10, ping_interval=None, max_size=None) as ws:
    for raw in ws:            # iterate to receive; each frame is one OneBot JSON object
        ...
```

- Run the reader in a daemon thread started *before* the HTTP server, reconnect with a short backoff,
  and log every reconnect: a bridge that quietly stops reading after the messenger restarts still
  answers `/health` and looks healthy.
- Dedupe by `message_id` (a few minutes of ids is plenty) so both feeds can run at once without
  double-answering, and skip `user_id == self_id` — with `reportSelfMessage: true` the bot's own sends
  come back as message events.
- Keep the reverse-HTTP `POST` route as a second entry point into the same handler; it costs nothing
  and covers a client that only has the HTTP path configured.
- Log every non-message meta event with its `self_id`, and suppress `meta_event_type == "heartbeat"`
  so the log stays readable.

### Diagnose the messenger side from inside it

Before blaming the bridge, connect to that WS endpoint and call OneBot actions — one short script
answers "is the account online, and is it the account I think it is?":

```python
def call(ws, action, **params):      # send {"action","params","echo"}; read until echo matches
    ...
call(ws, "get_status")       # {"online": true, "good": true}
call(ws, "get_login_info")   # {"user_id": <uin>, "nickname": ...}  <- catches a reassigned account
call(ws, "get_group_list")   # real group ids/names: pick a target, count the bot's rooms
```

The WS endpoint answering and `get_login_info` naming the expected bot uin rules out the whole
messenger side in one step; the uin it returns is what the @-mention gate must compare against.

## Hermes side (api_server)

- Enable: `API_SERVER_KEY=<random>` appended to `$HERMES_HOME/.env` (terminal edit; the file is
  write-protected from `write_file`). Nothing else is required — the adapter is credential-gated.
- Auth every call with `Authorization: Bearer $API_SERVER_KEY`.
- Routes worth knowing: `POST /v1/chat/completions`, `POST /v1/responses`, `GET|POST /api/sessions`,
  `POST /api/sessions/{id}/chat`, `POST /api/sessions/{id}/chat/stream`, `PATCH /api/sessions/{id}`,
  `GET /api/sessions/{id}/messages`, `GET /v1/models`, `GET /v1/capabilities`, `GET /v1/toolsets`.
- Session continuity per sender: create one session (`POST /api/sessions`) per sender id and reuse it
  with `/api/sessions/{id}/chat`; persist the id map to a JSON file so a bridge restart keeps threads.
- Response shapes (verified): `POST /api/sessions` →
  `{"object":"hermes.session","session":{"id":"api_<...>"}}`, and
  `POST /api/sessions/{id}/chat` →
  `{"object":"hermes.session.chat.completion","session_id":"...","message":{"role":"assistant","content":"..."}}`.
  Take the id from `session.id` and the reply from `message.content` — a parser that looks for them at
  the top level finds nothing and reads as an agent failure when the call actually succeeded.
- Secondary profiles under `gateway.multiplex_profiles: true` live at `/p/<profile>/...` and need the
  same `API_SERVER_KEY` in their own `.env`. Give a tier less power with
  `hermes -p <name> config set platform_toolsets.api_server '["web"]'` (verified read-back) — the
  ingress toolset is chosen by `_get_platform_tools(config, "api_server")`.
- **A narrowed toolset does NOT narrow MCP.** MCP tools are injected into every platform toolset, and
  `hermes profile create --clone` copies `mcp_servers` from the source, so a "search-only" tier keeps
  whatever MCP servers the owner runs — including a local VS Code/filesystem/shell server. Remove them
  (`hermes -p <tier> mcp remove <name> ...`) and confirm with `hermes -p <tier> mcp list`; probe the
  tier with a prompt that asks for a tool it should not have and read its refusal.
- Profile CLI: `hermes -p <profile> <cmd>`; the generated wrapper `~/.local/bin/<profile>.bat` is
  literally that line. `hermes -p <p> tools list` works, while `hermes -p <p> tools list --summary`
  is parsed by the outer parser and errors — pass the flag before `-p`, or use
  `hermes tools list --platform <p>`.

## Images (vision over the bridge)

- **The session chat route is multimodal, even though a helper in the same file looks text-only.**
  `message` may be a content-part array:
  `[{"type":"text","text":…}, {"type":"image_url","image_url":{"url":"data:image/png;base64,…"}}]`.
  `_session_chat_user_message` → `_normalize_multimodal_content` accepts `http(s)` and
  `data:image/...` part URLs, and the profile's normal chat model reads them natively — no separate
  vision model and no OCR step. A different helper (`_normalize_chat_content`) does exist in that file
  and silently drops non-text parts; do not conclude from it that images are unsupported.
- **Cap the payload yourself**: the pipeline skips data URLs over 5 MB
  (`_MEDIA_DATA_URL_MAX_BYTES`), so check the byte length and log the skip — an oversized image is
  otherwise a silent drop.
- **Resolve a OneBot `image` segment in this order** (first hit wins):
  1. `data.file` that is an existing filesystem path — read it. Strip `file://` through
     `urllib.parse.urlparse` + `urllib.request.url2pathname` first, and on Windows drop the leading
     slash (`/C:/…` → `C:/…`), or the existence check fails on a path that is perfectly valid.
  2. `data.url` starting with `http` — download it with a browser-ish `User-Agent` (the CDN refuses
     the default one) and a short timeout.
  3. Neither worked — call the OneBot action `get_image` with `{"file": <data.file or data.file_id>}`
     over the same WS endpoint and use the `file` / `url` it hands back.
  Then base64 it into a `data:` URL, mime from the extension (`.jpg/.png/.gif/.webp/.bmp`).
- A one-shot action call is enough for step 3 (open WS, send `{"action","params","echo"}`, read
  frames until `echo` matches, close) — no need to share the reader connection.
- **An image with no text is still a turn.** Send a placeholder text part
  (`"(对方发来图片，没有文字，请看图回应)"`); the route rejects content with no visible payload, and a
  bridge that returns early on an empty text string drops every pure-image message.
- **Verify with a synthetic image event instead of waiting for the user**: generate a local PNG whose
  literal text is the answer (e.g. `IMG-8842`) plus one distinctive shape, post a synthetic private
  event whose `message` is `[{"type":"image","data":{"file":"<abs path>","file_id":"x.png"}}, …text]`,
  and read the reply preview on the bridge's send line — the model must name both the shape and the
  text.
  - **ASCII-only text in the test image.** PIL's default font renders CJK as boxes, and the model then
    truthfully reports "a box glyph" — which reads exactly like a vision failure and sends you hunting
    a bug that does not exist.
- Probe the parsing logic without the server: load the bridge file with
  `importlib.util.spec_from_file_location` and call the event-content / image helpers directly (module
  import reads config but starts neither the HTTP server nor the WS reader).

## Bot-framework send side (AstrBot)

- **Resolve the send port from the framework's own config, never from a URL saved in an older
  session or copied from a sibling service.** The IM API is mounted on the framework's dashboard app,
  so its port *is* `dashboard.port` in `<launcher>/instances/<uuid>/core/data/cmd_config.json`
  (default 6185). Three ports are easy to confuse: dashboard/API (6185), the OneBot platform port
  `platform[].ws_reverse_port` (6199), and the messenger plugin's own WebUI (6099).
- Send: `POST http://127.0.0.1:<dashboard.port>/api/v1/im/messages` with
  `Authorization: Bearer <abk_… key>` and `{"umo":"<platform-instance-id>:FriendMessage:<qq>"` or
  `"<platform-instance-id>:GroupMessage:<group_id>", "message":"…"}`; success is HTTP 200
  `{"status":"ok"}`.
- **Read the failure, don't guess it**: 401 `{"status":"error","message":"Invalid API key"}` means
  the endpoint was reached and the key is dead; 404 means that port is not the API app; connection
  refused means nothing is listening there (wrong port, or the process is down).
- **Keys are persisted hashed only** — `<instance>/core/data/data_v4.db`, table `api_keys`
  (`key_hash`, `key_prefix`, `scopes` JSON, `revoked_at`). The plaintext exists only at creation, so a
  key that no longer matches cannot be recovered: mint a replacement row with
  `raw = "abk_" + secrets.token_urlsafe(32)`,
  `key_hash = pbkdf2_hmac("sha256", raw.encode(), b"astrbot_api_key", 100_000).hex()`,
  `key_prefix = raw[:12]`, `scopes` e.g. `["im","bot","chat"]`. Then write the plaintext into every
  consumer's config immediately — it is unrecoverable afterwards.
- **Validate a key without sending anything**: `GET /api/v1/im/bots` requires the `im` scope and
  returns `{"status":"ok","data":{"bot_ids":[…]}}`; a 200 proves the key *and* that the messenger
  side is connected. Routes also worth knowing: `/api/v1/chat/sessions`, `/api/v1/configs`,
  plus the legacy `/api/v1/im/message` alias of the send route.
- **Restarting the framework does not invalidate keys, but every consumer holds its own copy of
  URL+key** (a monitor's settings row, the bridge's config JSON). A stale pair fails 401 or refused
  with no other symptom, so re-point every consumer after a port/key change and finish by sending one
  real message and requiring HTTP 200.
- The OneBot WS endpoint NapCat's websocket client dials is the framework's *platform* port
  (`platform[].ws_reverse_port`, 6199 here) — neither the dashboard/API port nor the messenger
  plugin's WebUI. Keep the send API; **disable the framework's own auto-reply/persona**, or
  both it and the bridge answer the same incoming message. In AstrBot that knob is
  `<launcher>/instances/<uuid>/core/data/cmd_config.json` → `provider_settings.enable: false` (the
  send API keeps working — it needs only the platform connection plus the IM key). That file is UTF-8
  **with BOM**: read it with `encoding="utf-8-sig"` or `json.load` dies on `Unexpected UTF-8 BOM`.
  The framework reads it at startup, so it needs its own restart; back the file up before editing.
  AstrBot also drops a `<file>.bak-<timestamp>` beside it on every write — diff the two afterwards to
  confirm only your change landed (a BOM or a whole-file rewrite is the usual accident).
- **The launcher does not respawn a framework process that dies**, so a stopped AstrBot leaves every
  notification pointing at it silently going nowhere. Start it as a detached background process:
  `<instance>/venv/Scripts/python.exe main.py` with cwd `<instance>/core`; the dashboard/API port then
  comes from `cmd_config.json` and NapCat reconnects on its own. Verify the two ports plus `im/bots`.
- Never read `<instance>/core/data/plugins.json` (a multi-MB plugin-market cache) and never trust a
  grep hit inside it: plugin repo names containing digit runs make it a port-string false-positive
  magnet. Grep the small config files instead.

## Long turns: minutes-long tasks behind a bridge

A forwarded "implement / 照抄 this plugin" request is not a chat turn — it runs dozens of tool calls and
takes minutes. Price the bridge for that, or the turn is lost in a way that looks like failure.

- Give the api_server call a timeout in the tens of minutes (`request_timeout_s: 1800`), not the few
  minutes a chat turn suggests. Start an ack timer (~25 s) that posts one short "收到，我在处理，做完把结果
  发出来" to the same chat, and cancel it when the reply arrives — without an ack the user reads normal
  long work as "no reply" and starts debugging in the wrong place.
- **Never let a client-side timeout write its exception into the user's chat.** A blanket
  `except Exception` around the api_server call turns a slow turn into `Hermes 这边出错了：timed out`
  posted in a live group, in front of everyone. On timeout post nothing (or one fixed, human line) and
  go recover the answer.
- **A client timeout does not stop the turn.** Verified: after the bridge's request timed out the
  session kept growing (message and tool-call counters rose for another minute) before logging
  `Turn ended: reason=text_response`. The answer is therefore recoverable: poll `GET /api/sessions/{id}`
  and `GET /api/sessions/{id}/messages`, take the last non-empty `assistant` message, and send it to
  the original umo with a one-line "前一条是桥接超时误报" preamble.
- **`ended_at` stays `null` on api_server sessions even after the turn finishes**, so a watcher that
  waits for it never fires and the user waits forever. Signal completion on the answer text instead:
  the same non-empty last-assistant text on two consecutive polls (~1 min) means finished. Add a hard
  deadline plus a "no progress for N polls" exit, and kill any previous watcher before starting another
  — two watchers on one session double-post the answer.
- `GET /api/sessions/{id}/messages` returns `{"object":…,"session_id":…,"data":[<messages>],
  "pagination":{…}}` — the array is under `data`. `message_count` in the session record lags the
  transcript, so read the transcript for the answer instead of trusting the counter.
- Run the recovery detached (`scripts/forward_session_reply.py <session_id> <umo> --preamble "…"`, with
  notify-on-exit) so the answer reaches the room even if the bridge stays dead.

## Bridge hygiene

- Keep the bridge's own config (listen port, owner ids, guest profile name, api_server URL,
  send credentials) in a separate mode-0600 JSON file; read secrets from disk at startup and never
  log them. Seed credentials from the existing service's settings DB rather than asking the user to
  paste them again.
- Require the api_server key at startup and exit non-zero with a named error if it is missing — a
  bridge that silently 401s looks like a messenger outage.
- Acknowledge the HTTP POST to the messenger immediately (200) and process the event on a worker
  thread; messenger clients time out and retry otherwise.
- Test with synthetic OneBot events — `POST {"post_type":"message","message_type":"private|group",
  "user_id":…,"group_id":…,"message":[…]}` to the bridge port. The bridge ACKs 200 before working, so
  the HTTP response proves nothing: read the bridge log for the routing decision and the send result.
- Groups: before Hermes sees anything, drop every group message that does not @-mention the bot —
  `message` is a segment array, so look for a segment `{"type":"at"}` whose `data.qq` equals the bot
  uin, and accept `[CQ:at,qq=<uin>]` in `raw_message` for the string form. Forward the text and image
  segments (see `## Images`) and reply with the `GroupMessage:<group_id>` umo. Answering everything burns the owner's
  tokens and annoys the room.
- **Give each (group, member) pair its own session** (key `<group>|<uin>` in the session map). One
  shared group session lets a guest's message ride the owner's full-tool session — exactly the
  privilege split the per-sender profiles exist to enforce.
- NapCat's `httpClients[]` has no message-type filter, so no messenger-side change is needed for
  groups — but a silent group path is NOT proof the @-mention gate failed. From the user's side a dead
  feed and an unmatched gate both read as "I sent a message and nothing happened"; triage in this
  order: (1) inject a synthetic event straight into the bridge (proves handler + gate + send path),
  (2) confirm live events arrive at all, (3) only then inspect the gate.
- Log one line per inbound event — timestamp, `message_type`, sender, group id, `self_id`,
  at-targets, **the segment-type list** (`segs=["at","image","text"]`), text preview — including the
  events the gate rejects. Without it a silent early return (no @, empty text, self message) and a dead
  feed are indistinguishable, and the user's report cannot be answered from evidence; the segment list
  is the one field that separates "the user typed nothing" from "the payload is a segment type the
  bridge does not handle".
- **Handle `forward` / `node` segments (合并转发 / 聊天记录).** `data.id` → OneBot action
  `get_forward_msg` → walk each node's `message` (or `content`) array, appending its `text` and
  resolving its `image` segments into the same content parts, capped to the first ~40 nodes. Users
  forward screenshots and chat records as often as they attach single pictures; without this the whole
  payload is dropped and the agent, seeing no text and no image, tells them they never sent anything.
- **Never return early on an event that carried no text and whose images did not resolve.** That is an
  invisible failure: no reply, no log line, and the mentioned agent has no idea it was addressed. Log
  the dropped event with its segment types — with `segs=["at","image"]` in the log the unresolvable
  image is a diagnosis instead of a mystery.
- **Check a synthetic event by grepping the log for its marker, never by tailing.** Real traffic keeps
  interleaving with the test (the room talks, other users DM the bot), so a `tail -n` window can hide
  exactly the line you are looking for and an event that was handled reads as one that never arrived.
- Verify the group send path without spamming a real room: post a synthetic group event carrying a
  **bogus group id**. Correct behaviour is `[send] -> …:GroupMessage:<bogus>` followed by the
  framework reporting a send failure (`ActionFailed … retcode=1200 … sendMsg … result 110` = not a
  member) — that failure proves the umo type was accepted and the bot simply is not in that group.
  Ask the user to @ the bot in a real group as the last live check instead of posting there yourself.
- **Another Hermes session may be editing the bridge file in the same window.** The session that serves
  the messenger is itself an agent working the same file (it added per-message origin tagging while its
  user chatted), so a patch computed from an older read silently reverts that work. Re-read the file
  and its mtime before patching, keep the syntax check before any restart, and merge: both changes are
  meant to coexist in one process.
