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

`scripts/capture_qr_login.py` implements steps 1–3 in one runnable command.

## Pitfalls

- The confirmed payload's `user_id` is the **login identity**, not the inbound sender id that access
  policies compare against. Do not paste it into an allowlist and assume it matches.
- The result file contains the bot token. Delete the capture directory when the flow is done.
- Check the module before patching: another adapter may name the QR printer differently, or print only
  a URL through stdout. If no printer exists, tee stdout and extract the first `https://` line.
- A QR flow needs the `messaging` extra installed (it carries `qrcode` and `cryptography`); a
  `No module named 'qrcode'` failure is a missing dependency, not a broken adapter.
