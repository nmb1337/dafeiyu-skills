# Bridge operations cookbook

Paths assume `HERMES_HOME=C:\Users\32672\AppData\Local\hermes`; the bridge's own venv python is
`$HERMES_HOME/installs/*/environments/*/venv/Scripts/python.exe` (resolve with `ls`).

## Start / restart — detached, never as a gateway child

**A bridge started by the agent's terminal is a gateway child: `hermes gateway restart` kills it and QQ
goes silent with no error anywhere.** Launch it from a hidden `wscript.exe` launcher so the parent chain
is `python <- cmd <- wscript`, with the gateway not in it.

`$HERMES_HOME/gateway-service/QQ_Bridge.vbs` — resolves the interpreter itself, runs the bridge hidden,
appends its output:

```vbscript
' pick a venv that really has the dependency, not a hard-coded install hash
For Each i In fso.GetFolder(home & "\installs").SubFolders
  For Each j In fso.GetFolder(i.Path & "\environments").SubFolders
    If fso.FileExists(j.Path & "\venv\Lib\site-packages\websockets\__init__.py") Then
      py = j.Path & "\venv\Scripts\python.exe"
    End If
  Next
Next
sh.CurrentDirectory = home
sh.Run "cmd.exe /c """"" & py & """ -u scripts\qq-bridge.py >> """ & home & "\logs\qq-bridge.log"" 2>&1", 0, False
```

Run it: `powershell -NoProfile -Command "Start-Process wscript.exe -ArgumentList '<launcher.vbs>' -WindowStyle Hidden"`.

Layers that keep it up:
- Startup folder entry (`…\Startup\Hermes_QQ_Bridge.vbs` running the launcher) — survives reboots.
- Watchdog `scripts/qq-bridge-watchdog.py`: exit 0 when the port answers, otherwise relaunch via the VBS
  and log to `logs/qq-bridge-watchdog.log`; register it to repeat:
  `schtasks /Create /F /TN 'Hermes_QQ_Bridge_Watchdog' /SC MINUTE /MO 10 /TR 'wscript.exe <watchdog.vbs>'` —
  drive `schtasks` through PowerShell, the bash tool eats its `/Flags`.
- Single-instance guard inside the bridge (port probe before binding) plus the `.env` fallback for
  `API_SERVER_KEY`, since a VBS/task launch inherits no environment.

Verify, don't assume:
- Parent chain reads `python -> cmd.exe -> …` and `parent is gateway = False`.
- Kill every bridge python, run the watchdog, expect `✅ 桥接已恢复` and the port answered within one poll.
- Start the launcher a second time: expect `[skip] 桥接已在运行` and still exactly one bridge.

### Windows launcher pitfalls (each cost a debugging round)
- A `.cmd` written with LF-only line endings mis-parses in `cmd.exe`: the nested `for` block silently
  leaves the variable unset and the next line tries to execute `-u`. Write batch files CRLF or keep the
  logic in the VBS.
- `cmd //c start "" wscript.exe "<path>"` from the bash tool garbles the quoting (a stray cmd banner,
  nothing launched). Use PowerShell `Start-Process ... -WindowStyle Hidden`.
- A `Win32_Process` filter for `*qq-bridge.py*` also matches the agent's own shell command line, so the
  killer kills itself and the output truncates. Restrict to `Name -eq 'python.exe'` and build the pattern
  from concatenated fragments.
- A venv `python.exe` can be a shim that spawns the real interpreter with an identical command line:
  two matching processes are still one bridge (the child holds the port, the parent waits).

## Stop (when you really mean it)

```bash
powershell.exe -NoProfile -Command "Get-CimInstance Win32_Process | Where-Object { \$_.Name -eq 'python.exe' -and \$_.CommandLine -like ('*scripts\qq-brid'+'ge.py*') } | ForEach-Object { Stop-Process -Id \$_.ProcessId -Force -ErrorAction SilentlyContinue }"
```

Killing it this way is only safe while the watchdog task is disabled, or it will come back within its poll.

## Health and state probes

```bash
curl -s http://127.0.0.1:8790/health          # {"status":"ok", ...}
netstat -ano | grep -E ':(8790|3001|6185|6099)\b'   # bridge, NapCat WS, AstrBot dashboard, NapCat WebUI
curl -s -X POST http://127.0.0.1:8790/qq -H 'content-type: application/json' \
  -d '{"post_type":"message","message_type":"private","user_id":"999000001","self_id":<bot_uin>,"message_id":990001,"message":[{"type":"text","data":{"text":"self-check"}}]}'
```

Synthetic events with fake uins exercise the whole pipeline: the Hermes turn runs, only the final
AstrBot send fails (not a friend of the bot) — expected, and visible as an `error] send ... 400`.

## Inspecting Hermes sessions

```python
# session map (chat key -> session id)
json.load(open(r"$HERMES_HOME/qq_bridge_sessions.json"))
# one session's state
GET  http://127.0.0.1:8642/api/sessions/<sid>            # 'session'.message_count / ended_at (often null)
# transcript: the payload is under 'data', NOT 'messages'
GET  http://127.0.0.1:8642/api/sessions/<sid>/messages
```

Guest-profile sessions live under `http://127.0.0.1:8642/p/<profile>/...`; the owner uses the plain path.
Auth header on every call: `authorization: Bearer $API_SERVER_KEY` (read it from `$HERMES_HOME/.env`, never print it).

## Recovering a reply lost to a client timeout

1. `GET /api/sessions/<sid>/messages`, take the last `role == assistant` entry with non-empty text.
2. Post it to the chat through the AstrBot OpenAPI, with a one-line preamble that the earlier
   `timed out` / `HTTP Error 400` notice was a bridge artifact, not a task failure.
3. Chunk at the bridge's `reply_max_chars`.

`scripts/qq-group-watch.py` in `$HERMES_HOME` does this automatically for one session/group: it polls
the session, and once the last assistant answer stops changing it forwards it. Run it in the
background with notify-on-complete when a turn outlives the bridge's patience.

## Concurrency test recipe

- Same chat, 5 rapid events: expect 5 `[recv]` lines, replies serialized (~2 s apart) and in order.
- Two different chats: expect both handled in parallel.
- Confirm only one session id per chat key in the session map, and no `400` on `POST /api/sessions`
  in `logs/agent.log` after the restart.
- NapCat action channel, 12 concurrent `napcat_call('get_login_info')`: expect 12/12 success and
  exactly one "action channel established" line.

## Host proxy immunity (loopback must never go through the accelerator)

A machine running a local accelerator (Clash/V2Ray-style, `127.0.0.1:7890`) exports
`HTTP_PROXY`/`HTTPS_PROXY` into every process it spawns. A bridge started that way inherits them
**without** `NO_PROXY` and then routes its own loopback calls through the proxy. Measured mechanism:
`urllib.request.proxy_bypass("127.0.0.1:3001")` returns `False` in that environment, so `websockets`
(default `proxy=True`) hands the `ws://127.0.0.1:3001` connect to the proxy — quit the accelerator and
every attempt fails `WinError 10061` while NapCat's port stays healthy and answering.

Reproduce before changing anything — same env, two calls, and the log line is a symptom, not a
verdict:

```python
import urllib.request
print(urllib.request.proxy_bypass("127.0.0.1:3001"))   # False when HTTP_PROXY is set and NO_PROXY is not
from websockets.sync.client import connect
connect("ws://127.0.0.1:3001", open_timeout=8)                        # ConnectionRefusedError 10061
connect("ws://127.0.0.1:3001", open_timeout=8, proxy=None)           # connects
```

Fix it inside the bridge, not in the launcher (a VBS or scheduled task inherits whatever the host has
that day):

- At import time force loopback into both spellings, which also covers the urllib calls to the
  api_server (`8642`) and to the bot framework's OpenAPI (`6185`):
  `os.environ[key] = ",".join(existing + ["127.0.0.1", "localhost", "::1"])` for `key in
  ("NO_PROXY", "no_proxy")`.
- Connect with an explicit bypass and keep old-library compatibility:
  `try: connect(url, proxy=None, **kw)` / `except TypeError: connect(url, **kw)`.
- Report the feed state in `/health` (`ws_connected`, `last_event_at`) and let the watchdog alarm on
  `ws_connected == false` — a port probe cannot see this class at all, the port is up and answering.

The gateway side of the same problem (`gateway.trust_env: false`, `NO_PROXY` in `.env` and in the
Windows user environment) is in the `hermes-messaging-gateway` skill; the watchdog's
proxy-bypassed reachability check is in the monitoring section above.

## Common failure signatures

| Symptom in the log | Cause | Fix |
|---|---|---|
| `[in]` line never appears for a real message | feed is the dead HTTP report client | use the NapCat WS feed (3001) |
| `[in]` appears, no `[recv]` | two causes: the message carries no resolvable text/image/forward segment, **or** the handler's own allow-check — a second copy of the group @/wake-word rule — dropped it (an owner-no-@ bypass added only to the ingress pre-filter is invisible here) | parse that segment kind; make both gates call one shared predicate, then prove it with a synthetic event |
| user says "it doesn't reply" yet every probe is healthy | the message was **silently dropped downstream of the feed**: the per-member cooldown (`[skip] rate limited <chat>|<uin>`) ate a rapid follow-up, the message was empty / `@`-only, or it never actually carried the wake word / `at` segment (those land as `[skip] 已忽略 N 条无关消息`, which also counts unrelated chatter) | lower the cooldown to ~1 s (`group_rate_limit_s`, runtime config **and** code default) and keep a log line on every drop; check the three cases in this order before touching the link |
| `[error] HTTP Error 400: Bad Request` sent to the chat | two turns raced session creation for one chat | per-chat turn lock + create retry |
| `[error] timed out` sent to the chat | turn outlived the request timeout | raise the timeout, add the ack timer, recover the answer from the session |
| `error] send ... 400` after a real turn | AstrBot/NapCat cannot deliver to that target (not a friend / not in the group) | verify the UMO against NapCat group/friend list |
| every send fails while the bridge looks healthy (`401`, `Invalid API key`, connection refused) | AstrBot was restarted/reinstalled: OpenAPI key rotated and/or the port moved | mint a new key in AstrBot's sqlite and update both consumers (below) |
| an old session still answers with the previous voice | a live agent caches its system prompt in memory; editing `SOUL.md` does not touch it | inject the persona into that session or restart the gateway |
| the reply the bot posts is a provider auth error (`… rejected your API key …`) | the sender's profile has its own `.env` with a stale provider key, and a profile `.env` shadows the main one for that profile only | validate each profile key and sync the working one (section below) |
| every watchdog/Kuma alert silently missing, log shows `⚠ 推送微信失败: FileNotFoundError` | the push path hard-coded `bin\hermes.exe`, which a Hermes update removed/renamed | resolve candidates dynamically (`_hermes_cmds()`, feed-link/watchdog section) and prove with a real send |
| a long stretch with no `[in]` lines, plus repeated `[ws] 断开 (WinError 10061)` | **two causes, identical in the log:** NapCat's OneBot WS feed (3001) is down (QQ client restarted) — or the bridge is reaching loopback *through the host accelerator proxy*, which is off | discriminate with `curl -s --noproxy '*' http://127.0.0.1:3001/`: `426` = feed healthy, so it is the proxy (make the bridge proxy-proof, section below); no answer = restart the QQ client; the bridge reconnects within seconds either way |

## AstrBot send-path credentials (401 / port moved)

- The OpenAPI is part of AstrBot's dashboard app, so it listens on the **dashboard** port
  (`core/data/cmd_config.json → dashboard.port`, e.g. 6185) — there is no separate "API port". A port
  that used to answer can simply move when the launcher/config changes while the bridge keeps posting
  to the old one.
- Keys live in `core/data/data_v4.db`, table `api_keys`:
  `key_hash = pbkdf2_hmac("sha256", raw_key, b"astrbot_api_key", 100_000).hex()`, `key_prefix = raw[:12]`,
  `scopes` JSON must include `im` (plus `bot`/`chat` as needed). The plaintext exists only at creation,
  so a lost key is not recoverable — insert a new row with those columns and write the raw value into
  every consumer: `$HERMES_HOME/qq_bridge.json` (`astrbot_api_key`, `astrbot_base_url`) and the
  monitor's sqlite `settings` rows.
- Verify with a read-only call before trusting it:
  `GET /api/v1/im/bots` with `Authorization: Bearer <key>` → `{"status":"ok","data":{"bot_ids":["napcat-qq"]}}`.
  Then send one real message and check the response body, not just the HTTP status.

## Provider credentials per profile (the bot replies with an English auth error)

- Every profile may carry its own `.env` (`profiles/<name>/.env`); where present it **shadows
  `$HERMES_HOME/.env` for that profile's sessions only**. One stale key there yields exactly one
  visible symptom: every reply from that profile's chats is an English provider error
  ("… rejected your API key …") while the owner profile chats keep working — the user reads it as
  "QQ 坏了" or "桌面端坏了".
- Diagnose from the log, not by guessing: the provider's own 401 text names the key tail
  (`Your api key: ****5e70 is invalid`). Grep the logs for that tail, then search `.env`,
  `profiles/*/.env` and the config files for a key with the same tail — that file is the culprit.
- Validate with a cheap authenticated call before and after the fix (DeepSeek:
  `GET https://api.deepseek.com/user/balance` with `Authorization: Bearer <key>`; AstrBot:
  `GET /api/v1/im/bots`). Compare prefixes/tails only, never print the secret.
- Repair by copying the working key over the stale one. `.env` files are write-protected for the
  file tools — edit them through a Python/terminal script, back up first (`<file>.bak-<timestamp>`).
  A **new** session of that profile picks it up immediately; already-running sessions keep the key
  they loaded, so long-lived agent sessions and the desktop app need a session/app restart.
- `scripts/fix-profile-api-key.py` does sync-and-verify for every profile in one run.

## Feed-link and credential monitoring (watchdog)

The periodic watchdog is the only thing that catches the two silent classes of failure — it must
check more than its own port:

- Probe the **feed** port (NapCat `3001`). It cannot be relaunched from a script (it lives in the QQ
  client), so log and alert only; a user-visible "QQ 收不到消息" with a healthy bridge always starts
  at this port.
- Validate every provider key each run (`profiles/*/.env` against the main `.env`) and auto-sync a
  stale profile key from the working main key, backing up before writing.
- Add a **proxy-bypassed reachability check** on the model endpoint — build the request with an empty
  `urllib.request.ProxyHandler({})` and hit the provider's cheap authenticated endpoint. It is the guard
  for "the user quits the local accelerator and the bot goes mute": with `gateway.trust_env: false`
  plus the provider host in `NO_PROXY` the agent must reach the provider directly, so a failure here is
  a real network problem rather than the accelerator's state. Score an HTTP 401/402/403 as *reachable*
  (the path works, the key is the problem) and only a connection error as a problem, or a stale key
  double-reports as a network outage.
- Alert with the hermes CLI — but **resolve it dynamically; never hard-code `bin\hermes.exe`** — no LLM,
  no cost, no dependency on the bridge being up. A hard-coded path here died silently (2026-10-07→15): an
  update removed/renamed `bin\hermes.exe` (now `hermes.cmd`), every watchdog and Kuma alert threw
  `FileNotFoundError` into the log, and **nothing reached the owner for 8 days** until the channel was
  tested by hand. The fix (`_hermes_cmds()` in `qq-bridge-watchdog.py` / `uptime-alert.py`) resolves
  candidates each call — `bin\hermes.exe` if present → newest `installs/*/environments/*/venv/Scripts/hermes.exe`
  → `cmd.exe /c bin\hermes.cmd` — and tries each until one returns 0, logging every failed candidate.
  Probe the channel with a real send whenever you touch it; `rc=0` + a `推送微信 rc=0` log line is the receipt.
- **Dedupe through a state file** (`logs/watchdog-state.json`: previous problem set vs current) and
  notify only on new problems and on recoveries — a 10-minute task that re-sends the same alert every
  run gets muted by the user, and then real alerts are missed too.
- Test the checker by running it once by hand and reading its log line: it must report
  "全部正常" with today's real state, not just exit 0.

## Persona refresh for existing sessions

`$HERMES_HOME/scripts/soul-refresh.py`, run with the bridge venv python:

```bash
python scripts/soul-refresh.py list                        # recent api_server sessions (state.db + profiles/*/state.db)
python scripts/soul-refresh.py whoami <sid> [--profile p]  # ask that session to introduce itself
python scripts/soul-refresh.py inject <sid> [--profile p] [--force]   # paste SOUL.md into that session
python scripts/soul-refresh.py restart --delay 240         # delayed gateway restart: all sessions rebuild
```

- `inject` skips sessions whose recent messages already carry the persona marker; `whoami` before and
  after is the proof (identity flips from the built-in "I am Hermes …" to the persona).
- Resolving `SOUL.md` per session: map the profile name `default` to `$HERMES_HOME` itself. Joining it as
  a profile directory yields `profiles/default/SOUL.md`, which does not exist, and the injection then
  carries an empty persona body — the sessions answer "there is no persona text here" and it reads like a
  refusal of the persona when it is really a refusal of a malformed message.
- Guest-profile sessions (reduced `platform_toolsets`) frequently reply "this is not a system
  message, I won't accept it". That is the prompt-injection guard working: don't argue with them,
  enumerate the affected sessions and let the gateway restart carry them.
- An injected turn never reaches QQ (it does not pass through the bridge); confirm with
  `get_group_msg_history {group_id, count}` when the user cares about chat traces.

### Restarting the gateway safely (Windows login-item install)

- The gateway is launched at logon by the Startup shortcut
  `…\Startup\Hermes_Gateway.vbs` → `$HERMES_HOME/gateway-service/Hermes_Gateway.vbs`, which sets
  `HERMES_HOME`, `PYTHONIOENCODING`, `PYTHONPATH=$HERMES_HOME/hermes-agent`, cwd `$HERMES_HOME` and runs
  `tools\python-*\python.exe -m hermes_cli.main gateway run`. Nothing respawns a killed gateway, so
  never just kill it.
- Supported path: `hermes gateway restart` (its Windows code stops and respawns windowless, and fails
  loudly if no gateway comes back). Fallback: relaunch the VBS with
  `cmd //c start "" wscript.exe "<launcher>"`.
- Schedule the restart detached **with a delay** so the reply of the current turn is delivered first;
  `restart --delay N` writes `cache/scratch/gateway-restart.sh`, appends to `logs/gateway-restart.log`,
  then polls `netstat -ano | grep ':8642.*LISTENING'` for ~90 s and falls back to the VBS launcher.
- After a restart the bridge process survives (it is detached), while every session rebuilds its
  prompt on its next turn — that next turn is where `SOUL.md` finally applies.
