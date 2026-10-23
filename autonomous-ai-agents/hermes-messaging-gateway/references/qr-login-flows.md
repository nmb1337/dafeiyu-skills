# QR login flows

For platforms whose auth is "scan a QR with the vendor's mobile app" (weixin/iLink, wecom AI bot,
whatsapp). The adapter already ships the flow — call it and give the user something scannable.
Do not reimplement the login or hand-write the credential file.

## Why not just run `hermes gateway setup`

The wizard is a TTY interactive prompt: it prints an ASCII QR that a chat surface cannot reproduce
faithfully, and the scan window is short. Drive the underlying function instead and deliver a PNG the
user can scan straight from the chat window.

## Recipe

1. Run the adapter's login coroutine with the runtime venv python, from the checkout root so
   `import gateway.*` resolves:
   `from gateway.platforms.weixin import qr_login` → `await qr_login(hermes_home, timeout_seconds=420)`.
2. Capture the URL without reimplementing the polling loop: monkeypatch the module's QR printer
   (weixin: `_print_qr`) so it records its URL argument. The printer receives the vendor's **liteapp
   URL**, which is the string that must actually be encoded — the bare hex token in the API response
   is not scannable.
3. Run it in the background, poll for the URL file, render the URL to a PNG with the `qrcode`
   package, and deliver it with `MEDIA:<path>`. The user scans from the chat.
4. Poll the background process. On `status=confirmed` the adapter saves the credentials itself
   (weixin: `save_weixin_account`) into `$HERMES_HOME/weixin/accounts/<account_id>.json`. Never write
   that file by hand.
5. The QR auto-refreshes on expiry (a few times) and prints a fresh URL through the same printer, so
   re-read the capture file rather than assuming the first URL is final.

`scripts/capture_qr_login.py` implements steps 1–3 in one runnable command. **它不在 checkout 里，而在技能目录**：`<skills>/autonomous-ai-agents/hermes-messaging-gateway/scripts/capture_qr_login.py`——从 checkout 根目录 `cd` 过去、用绝对路径调它，`import gateway.*` 才解析得到。

选解释器：要有 `aiohttp, qrcode, cryptography`（本机实测只有某个 `installs/*/environments/*/venv` 带齐；桥接用的 websockets venv 没 aiohttp）。给**哪个档案**登录就把 `HERMES_HOME` 指到那个档案根目录（如 `profiles/client1`），否则凭证会写进默认档案。

## Hands-off finish: creds → `.env` → restart

The scan usually lands after the agent's turn has ended, and a confirmed scan alone does **not** put
the bot online:

1. `save_weixin_account` writes only `$HERMES_HOME/weixin/accounts/<account_id>.json`
   (`token`, `base_url`, `user_id`). It never touches `.env` — that is the setup wizard's separate job
   (`_setup_weixin`), so a script-driven login leaves a credentialed but unserved profile.
2. Write the env pairs into **that profile's** `.env` (key-replace, keep comments, append what's
   missing): `WEIXIN_ACCOUNT_ID`, `WEIXIN_TOKEN`, `WEIXIN_BASE_URL`, `WEIXIN_CDN_BASE_URL`,
   `WEIXIN_ALLOW_ALL_USERS=false`, `WEIXIN_DM_POLICY=allowlist`, `WEIXIN_ALLOWED_USERS=<sender id>`.
3. Restart the gateway — under `multiplex_profiles` the served adapters are enumerated at startup, so
   a new profile credential is invisible until then. The restart must come from a process **outside**
   the gateway's own turn (a detached watcher is fine; a `hermes gateway restart` issued from inside a
   turn is refused by the guard).

Working shape: the QR script writes a small status JSON (`wait|scaned|confirmed|expired`); a second
background process polls it, and on `confirmed` reads the token from the account JSON (the status file
only needs the account id), writes `.env`, then restarts. Everything after the scan is then automatic —
the user only has to scan.

Keep the PNG at a **stable path** so an expiry refresh overwrites the same file: re-sending it is then
one command (to a QQ chat: OneBot `send_group_msg` with
`{"type":"image","data":{"file":"file:///C:/abs/qr.png"}}` — see SKILL.md's outbound-image bullet).

## Pitfalls

- The confirmed payload's `user_id` is the **login identity**, not the inbound sender id that access
  policies compare against. Do not paste it into an allowlist and assume it matches.
- The result file contains the bot token. Delete the capture directory when the flow is done.
- Check the module before patching: another adapter may name the QR printer differently, or print only
  a URL through stdout. If no printer exists, tee stdout and extract the first `https://` line.
- A QR flow needs the `messaging` extra installed (it carries `qrcode` and `cryptography`); a
  `No module named 'qrcode'` failure is a missing dependency, not a broken adapter.
