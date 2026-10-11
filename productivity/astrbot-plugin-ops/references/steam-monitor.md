# Steam game status → QQ push

Companion to the AstrBot plugin workflow. The user's goal shape: on game start, push the
game name as text plus the game's cover image to a QQ group.

## Local facts (this machine)
- Steam client: `C:\Program Files (x86)\Steam`.
- Accounts: `config/loginusers.vdf` lists every remembered account as
  `<steamid64> { AccountName, PersonaName, AutoLogin, Timestamp }`. The auto-login account is
  also in the registry: `reg query "HKCU\Software\Valve\Steam" /v AutoLoginUser`.
- **Currently-playing appid, no API key needed**: registry
  `HKCU\Software\Valve\Steam` → `RunningAppID` (DWORD). `0` = not in a game.
  `LastGameNameUsed` holds the *persona*, not the game — do not use it for game detection.
- Appid → name offline: `steamapps/appmanifest_<appid>.acf` and `steamapps/libraryfolders.vdf`.
- Cover image: `https://cdn.cloudflare.steamstatic.com/steam/apps/<appid>/header.jpg`
  (verified 200 for appid 730). `library_hero.jpg` is bigger and flashier; `header.jpg` is the safe default.

## Two detection routes — pick deliberately and say which
- **Steam Web API** (`ISteamUser/GetPlayerSummaries`, free key from `steamcommunity.com/dev/apikey`):
  works no matter which device the user plays on, but `gameextrainfo`/`gameid` come back only if the
  profile's game details are public. Needs the 17-digit steamid64 per account.
- **Local registry + appmanifest**: no key, no privacy dependency, but only detects games launched on
  this machine. The user does play here, so this is a legitimate fallback when they will not create a key.

## The plugin in use
- `astrbot_plugin_steam_monitor` (GitHub `singularity2000/astrbot_plugin_steam_monitor`) is the reference
  implementation: per-monitor-group polling of online/game state, achievements and playtime, pushing
  "{persona} 开始玩 {game} 了". Installed under `data/plugins/` of the local instance.
- Its `_conf_schema.json` keys: `steam_api_key`, `status_poll_interval` (default 180 s),
  `achievement_poll_interval`, `status_notification`, `online_offline_notification`,
  `achievements_notification`, `playtime_notification`, `private_mode`/`private_name`, and
  `monitored_targets` — a `template_list` of `{note, sessions[], steam_ids[], settings{}}`.
- Local patch: when the outgoing status message is a game *start*, attach the cover **from a local
  cache, never as a URL** — `url_image("https://cdn.cloudflare.steamstatic.com/steam/apps/<gameid>/header.jpg")`
  hands the download to NapCat *inside* the send, and on this machine's relay path that took ~10 s and
  timed out the send: the log line was just `推送消息到 <umo> 失败: ` with an empty exception and the
  group got nothing, text included (the text-only "退出了游戏" push from the same poll logged INFO and
  arrived, which is what pins the image as the cause). Fix inside the plugin: a `_cached_header_image(app_id)`
  helper that downloads once into temp (`httpx.AsyncClient(timeout=12, trust_env=False)` first, then a
  proxy-enabled client; cache by appid) and attaches `base64_image(...)`, plus a text-only retry around
  the send (`except: send(MessageChain().message(final_msg))`). Keep the patch recorded — a plugin update
  wipes it (stash a copy of the patched `main.py` outside the instance dir).
- **Its HTTP client must be built as `httpx.AsyncClient(timeout=20, verify=False, trust_env=False)`** (three call sites: `__init__` plus two rebuilds inside `_make_request`). Out of the box the plugin uses `httpx.AsyncClient(timeout=20)`, which on this machine fails twice over: system `HTTP_PROXY=127.0.0.1:7890` sends the request through the proxy, and Steam++'s self-signed local re-serving fails certificate verification. With those two flags the Steam Web API and the store API both answer normally (verified: `GetPlayerSummaries` returned the profile and `store.steampowered.com/api/appdetails?appids=730` returned CS2).
- First poll after startup records the baseline and pushes nothing; a test needs a real state change
  (or the plugin's own `steam test status` command). Faking it via `last_states.json` does **not** work — see the reload pitfall in SKILL.md.

## Adding another monitored account → group
The user asks in the shape 「<steamid64> 玩游戏就发到 QQ 群 <gid>，和我之前一样」. Each monitored target is an
independent entry; a group with no entry never hears anything, so "nothing arrives in group X" usually means a
missing/mistyped entry, not a broken monitor.
1. Append to `monitored_targets` in `<core>/data/config/astrbot_plugin_steam_monitor_config.json` (read with
   `utf-8-sig` — it carries a BOM): `{note: "<human label>", sessions: ["napcat-qq:GroupMessage:<gid>"],
   steam_ids: ["<steamid64>"], settings: {status_notification: true, everything else off}}` — mirror the existing
   target's settings (and its sessions *prefix*, taken from a real `umo_aliases` row) unless told otherwise.
2. Verify the two easy-to-miss preconditions *before* telling the user it works:
   - **account profile public**: `GetPlayerSummaries` for that steamid64 must return
     `communityvisibilitystate == 3`; a private profile never yields `gameextrainfo`, so the push would
     silently never fire.
   - **the bot account is actually in the target group**: NapCat `get_group_list` (each entry has
     `member_count`) — a UMO for a group the bot is not in can never be pushed to.
3. Restart the AstrBot instance (a killed instance is not respawned by the launcher) and confirm the new
   steamid appears in `plugin_data/astrbot_plugin_steam_monitor/last_states.json` after a poll tick.

