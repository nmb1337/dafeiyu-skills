#!/usr/bin/env python3
"""Deliver a finished Hermes session turn to a OneBot/QQ target after the bridge gave up.

A bridge's HTTP client can time out on a minutes-long turn while the server-side turn keeps running;
this waits for the answer and posts it instead of losing it.

Usage
-----
  python forward_session_reply.py <session_id> <target> [--preamble TEXT] [--timeout-min N]

<target> is a full umo (`napcat-qq:GroupMessage:123456`, `napcat-qq:FriendMessage:654321`) or the
shorthand `group:123456` / `private:654321` (the bot id then comes from config).

Config: send credentials and bot id from `$HERMES_HOME/qq_bridge.json` (`astrbot_base_url`,
`astrbot_api_key`, `astrbot_bot_id`, `reply_max_chars`), falling back to `ASTRBOT_BASE_URL` /
`ASTRBOT_API_KEY` / `BOT_UIN`; the Hermes key from `API_SERVER_KEY` in `$HERMES_HOME/.env` or the
environment. Credentials are never printed.

Exit codes: 0 delivered, 1 delivered with send errors, 2 bad usage, 3 finished with no answer text,
4 gave up (still running / no progress).
"""
from __future__ import annotations

import json
import os
import sys
import time
import urllib.request

HERMES_HOME = os.environ.get("HERMES_HOME") or os.path.join(os.path.expanduser("~"), "AppData", "Local", "hermes")
API = os.environ.get("HERMES_API") or "http://127.0.0.1:8642"


def env_file_value(name: str, path: str) -> str:
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            for line in fh:
                if line.startswith(name + "="):
                    return line.split("=", 1)[1].strip().strip('"').strip("'")
    except OSError:
        pass
    return ""


def send_config() -> dict:
    cfg = {"astrbot_base_url": os.environ.get("ASTRBOT_BASE_URL", ""),
           "astrbot_api_key": os.environ.get("ASTRBOT_API_KEY", ""),
           "astrbot_bot_id": os.environ.get("BOT_UIN", ""),
           "reply_max_chars": 1500}
    try:
        with open(os.path.join(HERMES_HOME, "qq_bridge.json"), encoding="utf-8") as fh:
            for key, value in json.load(fh).items():
                if key in cfg and value:
                    cfg[key] = value
    except (OSError, ValueError):
        pass
    return cfg


def get(url: str, headers: dict):
    with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=30) as resp:
        return json.loads(resp.read().decode())


def last_assistant_text(sid: str, headers: dict) -> str:
    data = get(f"{API}/api/sessions/{sid}/messages", headers)
    for msg in reversed(data.get("data") or data.get("messages") or []):
        if msg.get("role") != "assistant":
            continue
        content = msg.get("content")
        if isinstance(content, list):
            content = "\n".join(str(p.get("text") or "") for p in content if isinstance(p, dict))
        text = str(content or "").strip()
        if text:
            return text
    return ""


def deliver(cfg: dict, umo: str, text: str) -> bool:
    base = str(cfg["astrbot_base_url"]).rstrip("/")
    limit = int(cfg.get("reply_max_chars") or 1500)
    ok = True
    for i in range(0, len(text), limit):
        chunk = text[i:i + limit]
        body = json.dumps({"umo": umo, "message": chunk}).encode()
        req = urllib.request.Request(f"{base}/api/v1/im/messages", data=body, method="POST",
                                     headers={"content-type": "application/json",
                                              "authorization": f"Bearer {cfg['astrbot_api_key']}"})
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                print(f"[send] {resp.status} {chunk[:60]!r}", flush=True)
        except Exception as exc:                        # report, keep sending the rest
            ok = False
            print(f"[error] send failed: {exc}", flush=True)
        time.sleep(0.5)
    return ok


def main() -> int:
    argv = sys.argv[1:]
    if len(argv) < 2 or argv[0].startswith("--"):
        print(__doc__)
        return 2
    sid, target = argv[0], argv[1]
    preamble = argv[argv.index("--preamble") + 1] if "--preamble" in argv else ""
    timeout_min = float(argv[argv.index("--timeout-min") + 1]) if "--timeout-min" in argv else 45.0

    cfg = send_config()
    if target.startswith("group:"):
        umo = f"{cfg['astrbot_bot_id']}:GroupMessage:{target.split(':', 1)[1]}"
    elif target.startswith(("private:", "friend:")):
        umo = f"{cfg['astrbot_bot_id']}:FriendMessage:{target.split(':', 1)[1]}"
    else:
        umo = target

    key = os.environ.get("API_SERVER_KEY") or env_file_value(
        "API_SERVER_KEY", os.path.join(HERMES_HOME, ".env"))
    if not key:
        print("[fatal] API_SERVER_KEY not found (environment or $HERMES_HOME/.env)", flush=True)
        return 2
    headers = {"authorization": f"Bearer {key}"}

    deadline = time.time() + timeout_min * 60
    prev_text, prev_count, stable, idle = "", None, 0, 0
    while time.time() < deadline:
        try:
            sess = get(f"{API}/api/sessions/{sid}", headers)
            sess = sess.get("session") or sess
            text = last_assistant_text(sid, headers)
        except Exception as exc:                        # transient poll failure
            print(f"[warn] poll failed: {exc}", flush=True)
            time.sleep(20)
            continue
        count = sess.get("message_count")
        print(f"[poll] msgs={count} ended={sess.get('ended_at')} answer={bool(text)}", flush=True)
        # ended_at stays null on api_server sessions: a stable non-empty answer means "finished"
        stable = stable + 1 if (text and text == prev_text) else 0
        idle = idle + 1 if count == prev_count else 0
        prev_text, prev_count = text, count
        if text and (sess.get("ended_at") or stable >= 2):
            payload = (preamble + text) if preamble else text
            return 0 if deliver(cfg, umo, payload) else 1
        if idle >= 6:
            print("[warn] no progress for ~3 min; giving up", flush=True)
            return 4
        time.sleep(30)
    print("[warn] still running when the deadline passed; giving up", flush=True)
    return 4


if __name__ == "__main__":
    sys.exit(main())
