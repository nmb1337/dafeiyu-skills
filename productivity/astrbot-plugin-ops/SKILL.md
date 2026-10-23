---
name: astrbot-plugin-ops
description: "Use when installing or extending AstrBot plugins."
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [astrbot, plugin, napcat, qq, messaging, steam]
---

# AstrBot plugin operations (local instance)

Covers installing, configuring, extending and debugging AstrBot plugins on this machine, whose
whole reason for existing is pushing messages into QQ through NapCat.

## When to Use
- Installing a third-party AstrBot plugin, or extending one (extra message content, images, new notifications).
- Any task whose output must land in QQ — proactive pushes, scheduled notices, game/status monitoring.
- Debugging why a plugin does not load, does not push, or pushes to the wrong place.

## Instance layout
- Launcher instance root: `C:\Users\32672\.astrbot_launcher\instances\<uuid>\core` — resolve `<uuid>` with `ls -d "$HOME/.astrbot_launcher/instances/"*/core` instead of hardcoding it; it changes if the instance is recreated.
- Installed plugins: `<core>/data/plugins/<plugin_dir>` (each has `metadata.yaml` + `main.py`).
- Per-plugin config as JSON: `<core>/data/config/<plugin_name>_config.json`, generated from the plugin's `_conf_schema.json`.
- Plugin private data: `<core>/data/plugin_data/<plugin_name>/`.
- 表情包素材：meme_manager 把图包放在 `<core>/data/plugin_data/meme_manager/packs/<pack>/memes/<情绪>/`（官方包「DeepSeek 二创表情包」= 174 张、13 个情绪目录：affection/angry/confused/food/greeting/happy/money/portrait/sad/sleep/teasing/tech/work）。要在聊天里按概率补一张，直连 NapCat 的 OneBot WS 发 image 段（做法见技能 hermes-messaging-gateway）。
- Session/group registry DB: `<core>/data/data_v4.db` (WAL mode — always open read-only: `sqlite3.connect("file:<path>?mode=ro", uri=True)`).

## Live endpoints (verify before quoting an old one)
- AstrBot dashboard **and** OpenAPI share the `dashboard.port` from `cmd_config.json` (**6185** here). `6199` is the aiocqhttp (OneBot v11) reverse-WS endpoint NapCat's WS client dials (`platform[].ws_reverse_port`), not a second dashboard. The frequently-cited `:11451` base URL is dead on this machine.
- Push a message without going through a plugin: `POST http://127.0.0.1:6185/api/v1/im/messages` with `{"umo": "<umo>", "message": "<text>"}` and `Authorization: Bearer <IM key>`.
- NapCat: WebUI 6099, OneBot WS `ws://127.0.0.1:3001`, runs inside QQNT.

## OpenAPI key, persona, restarts
- API keys are `abk_...` and stored **hashed** in `data_v4.db` table `api_keys` (`key_prefix` plus `key_hash = pbkdf2_hmac("sha256", raw, b"astrbot_api_key", 100_000).hex()`, `scopes` including `im`, `created_by`). The plaintext is unrecoverable: to re-key a consumer, INSERT a row with a freshly generated `abk_<secrets.token_urlsafe(32)>` (prefix = first 12 chars, same hash formula, `scopes` must include `im`) and write the raw value into that consumer's config. Validate without side effects via `GET /api/v1/im/bots` (im scope); `401 "Invalid API key"` means the stored key is stale, not that the header is wrong.
- Anything that hard-codes the base URL or key (the monitor's settings, the QQ bridge config) must be re-checked after an AstrBot restart: the dashboard port and key set can change, and the failure shows up late and indirectly as 401 or connection-refused.
- To stop AstrBot answering with its own LLM persona in groups, set `provider_settings.enable = false` in `<core>/data/cmd_config.json`; it applies on restart. AstrBot leaves `cmd_config.json.bak-<timestamp>` when it rewrites the file — diffing that against the current file is the quickest way to see exactly what changed.
- Restart the instance by hand with `<instance>/venv/Scripts/python.exe main.py` from `<core>`: the launcher does **not** respawn a killed instance, so killing it silently takes every QQ push down until you start it again.

## Finding plugins (market + GitHub)
- **Query with `gh`, not raw `curl`.** `api.github.com` rate-limits the shared host IP fast; the authenticated CLI is the reliable path: `gh search repos "astrbot <关键词>" --limit 5 --json fullName,stargazersCount,description`, and for a popularity slice `gh api "search/repositories?q=topic:astrbot-plugin&sort=stars&order=desc&per_page=40" --jq '.items[] | [.stargazers_count,.full_name,(.description // ""),.pushed_at] | @tsv'`. The topic covers ~400 repos; `gh search repos` handles Chinese keywords that break hand-built URLs.
- **The whole market fits in one table.** `gh api repos/konley/astrbot-plugin-source-backup/contents/plugin_source.md --jq .content` returns base64 of a ~930-row markdown table (名称 / 作者 / 版本 / Star / 描述 / 标签 / 更新) mirrored from the plugin source; decode in Python, parse the rows, filter on keyword sets (游戏/互动/表情包/签到/运势/解析/修仙…), sort by Star. Write the `.b64` to a **native** path under `$HERMES_HOME/cache/scratch/`: bash's `$TMPDIR` is an MSYS path that Python's `os.environ['TMPDIR']` does not resolve to. Ready-to-run: `python scripts/find_plugins.py 游戏 互动 --min-star 2` does the fetch, decode and filter in one go.
- **Screen before recommending.** Prefer command-triggered plugins. AstrBot's aiocqhttp adapter receives the same group/private events as the QQ bridge (`[napcat-qq(aiocqhttp)]` lines in `logs/astrbot.log`), so a plugin that replies opportunistically (auto-replies to images, comments on every message) double-answers alongside 大肥鱼 — only explicit-command plugins are safe to pin next to the bridge. Skip plugins that duplicate what the stack already owns (LLM persona/chat, memory, 点歌, 画图, live dashboard), and anything that fetches explicit sexual material. Treat 0★ repos as try-only: clone, read `main.py`, test in a scratch group before calling it working.
- A curated shortlist with fit notes lives in `references/plugin-candidates.md`; re-check `stargazers_count` and `pushed_at` with `gh api repos/<full_name>` before quoting it — activity matters more than the number.

## Installing a plugin
1. Find the plugin's repo (AstrBot plugins are `astrbot_plugin_*` repos on GitHub, or listed in the market).
2. `cd <core>/data/plugins && git clone --depth 1 <repo_url> <plugin_dir>`. `--depth 1` matters — some plugin repos are large.
3. AstrBot discovers anything under `data/plugins` on plugin reload or restart. No registry file needs editing.
4. **Reload without touching the WebUI**: the dashboard JWT is verified by signature only, so sign your own HS256 token with `dashboard.jwt_secret` from `cmd_config.json` (any non-empty `username`) and `POST /api/plugin/reload` `{"name": "<plugin_dir>"}` with `Authorization: Bearer <token>` on port 6185. Build the request with `urllib.request.build_opener(urllib.request.ProxyHandler({}))` — the box-wide `HTTP_PROXY=127.0.0.1:7890` otherwise swallows loopback calls. `GET /api/log-history` (same Bearer) returns recent logs, which is how you confirm a plugin loaded or a push fired.
5. Reuse the plugin's own README + `_conf_schema.json` as the spec; do not re-derive the feature set.

## Configuring a plugin programmatically
- Read `_conf_schema.json` first for exact keys, types and defaults, then write `<core>/data/config/<plugin_name>_config.json` directly. This beats driving the WebUI, and the plugin hot-reloads when the config is saved.
- A `template_list` schema maps to a JSON **list of objects** in the config file; `list` maps to a JSON list of strings.
- Leave values you do not have (API keys) empty and tell the user exactly which one is missing and where to get it — never invent a key.

## Discovering send targets (UMO)
- Do not make the user run the plugin's `sid` command. Read the registry:
  `select umo, auto_name, updated_at from umo_aliases order by updated_at desc` on `data_v4.db` returns every group/friend UMO the bot has ever seen, newest first, with the human-readable group name.
- This instance's platform prefix is **`napcat-qq`**: `napcat-qq:GroupMessage:<groupid>`, `napcat-qq:FriendMessage:<qq>`. Plugin READMEs that show a bare `napcat:` prefix are wrong here — always take the real prefix from a row in the DB.
- Some rows carry a per-user sub-scope (`GroupMessage:<userid>_<groupid>`); the plain `GroupMessage:<groupid>` form is the one that reaches the whole group.
- Present a shortlist of candidate groups and let the user pick; do not guess which group they meant.

## Extending what a plugin sends
- `MessageChain` is appendable and returns self: `MessageChain().message(text).url_image(url)` sends text plus a remote image in one message; `file_image(path)` for a local file, `base64_image(b64)` for bytes you fetched yourself. Patch the cloned plugin in place with the patch tool.
- Push text and image as one chain — two separate sends arrive as two messages.
- **Never let the adapter fetch a remote image at send time.** `url_image(<url>)` makes the platform download *inside* the send call; on a slow path (here a local relay, ~10 s for a Steam CDN cover) that call times out and **the whole chain — text included — is dropped**: the log shows only `推送消息到 <umo> 失败: ` with an **empty** exception string (`TimeoutError`), and the group receives nothing at all. Pre-fetch the image yourself (cache it by URL/appid; try a `trust_env=False` client first, then a proxy-enabled one) and attach `base64_image(b64)`, keeping `file_image(path)` as the fallback, so send time no longer depends on the network.
- **Wrap every push so an optional decoration can never eat the payload:** `try: await send(chain_with_image) except Exception: await send(MessageChain().message(text))`. When the text is the point, it must still land after the image fails.
- Diagnosing a push that "did nothing": read the plugin's own lines in `logs/astrbot.log` (`grep -a <plugin_name>`), then **discriminate by content** — if the text-only pushes log as INFO while the pushes carrying an image log `失败:`, the image path is the cause, not the plugin, the adapter connection or the session binding.

## Working rules for this user
- **Boundary that decides who writes the code**: the user's own project code goes to VS Code (open the project window, type the request into VS Code chat). AstrBot plugin internals are infrastructure, not one of the user's projects — installing and lightly patching them directly is expected and accepted.
- Reply in Chinese, short. Ask only for what cannot be discovered locally: credentials/API keys, and the target group when the DB shortlist does not settle it.
- State plainly which values you are waiting on, so the user can unblock in one message.
- **Two modes.** Casual chat: do what the owner asks — banter, roast whoever he points at, no process lectures. Serious work (code, systems, research, anything that lands in a config or a chat): read the docs/source first, change, self-test, then report with the actual output — never from memory, never a confident claim without evidence.
- **One outward persona for every channel.** It is 「蓝色大肥鱼」(the DeepSeek whale-girl nickname meme), defined in `$HERMES_HOME/SOUL.md` and mirrored in `profiles/<guest>/SOUL.md`; AstrBot's own persona stays disabled. Do not introduce a second personality in a plugin push or an AstrBot persona entry.
- Report shape: result first, evidence next (measured output / log line), process never.

## Pitfalls
- **Never `read_file` `<core>/data/plugins.json`**: it is the whole plugin-market cache (~2.4 MB, ~44k lines) and will eat the context window. Grep it for the plugin name or `download_url` instead; it is also not the list of installed plugins (that is the `data/plugins` directory itself).
- Grepping `~/Documents` or other broad trees times out at 180 s. Scope searches to the AstrBot instance dir or one project.
- **The live plugin config `data/config/<plugin>_config.json` carries a UTF-8 BOM** (its `_conf_schema.json` sibling does not): `json.load(open(path, encoding="utf-8"))` fails with `Unexpected UTF-8 BOM (decode using utf-8-sig)`. Read those files with `encoding="utf-8-sig"`; writing them back without a BOM is fine.
- A plugin installed by `git clone` gets overwritten by a later `git pull`/market update, taking local patches with it. Either fork it, or record every local patch so it can be re-applied.
- A plugin that appears installed but pushes nothing is usually missing its API key (`initialize()` bails with a 'key not configured' warning) or has no monitored target configured — check those two before debugging the network.
- **Reload terminates the plugin first, and it writes its in-memory data files back to disk on the way out.** Faking a state change by editing `<core>/data/plugin_data/<plugin>/*.json` before a reload therefore never works — the fake is overwritten milliseconds before the new instance reads it. To exercise the push path, temporarily paste a few lines into the plugin's `initialize()` that send one real message through `self.context.send_message(umo, chain)`, reload, read the log, then delete the lines and reload again.
- **OpenAPI `POST /api/v1/im/messages` cannot send an image by URL.** Its `image` message part requires an `attachment_id` of a previously uploaded attachment; only plugin-internal `MessageChain().message(t).url_image(url)` reaches QQ with a remote image.
- Hosts-level proxies bite: **Steam++ (Watt Toolkit) points `api.steampowered.com`, `store.steampowered.com` etc. in `hosts` at 127.0.0.1** and re-serves them from a local MITM with a self-signed cert. `curl https://api.steampowered.com/...` then fails on Windows schannel with `CRYPT_E_NO_REVOCATION_CHECK` unless you pass `-k`, and a Python client needs `httpx.AsyncClient(verify=False, trust_env=False)` — verify off for the cert, trust_env off so it hits the local proxy instead of 7890. Check `grep -i steam /c/Windows/System32/drivers/etc/hosts` before assuming a Steam endpoint is unreachable.
 - **“切换人格没反应” is usually not a persona bug — check these two before anything else.** (a) AstrBot
 binds the persona to the **conversation** (`conversations.persona_id`, read back by
 `resolve_event_conversation_persona_id`), so the picker on the persona page only changes the default
 for conversations created *after* the change — existing groups and DMs keep the persona they were
 bound to, which looks exactly like “I switched it and nothing happened”. Fix it per conversation in
 会话管理, or reset the conversation so it re-inherits the default. (b) The LLM master switch
 (`provider_settings.enable`) must be on: with it off no LLM-side feature runs, persona included — and
 on this machine it is off on purpose because the QQ bridge answers instead, so a persona change here
 is *expected* to do nothing. Also worth ruling out: the Agent runner reads
 `agent_runner.config.persona.persona_id` while plain chat reads the default persona, so changing the
 wrong one has no effect, and an empty `system_prompt` persona is indistinguishable from no persona.

## References
- `scripts/find_plugins.py` — fetch + filter the 930-row AstrBot plugin registry mirror (`python find_plugins.py 关键词… [--min-star N] [--limit N]`).
- `references/plugin-candidates.md` — 群聊玩法插件候选清单（AstrBot + 独立项目），按玩法分类，带适配注意和「不装」清单。
- `references/steam-monitor.md` — Steam game-status detection (SteamID, currently-playing appid, cover images), the installed `steam_monitor` plugin's config shape, and the steps to add another monitored account → QQ group.
