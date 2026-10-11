#!/usr/bin/env python3
"""Ad-hoc NapCat/OneBot queries straight off the bridge's event WS.

Run with the interpreter the BRIDGE uses (it is the one with `websockets`):

    <installs/*/environments/*/venv>/Scripts/python.exe napcat_query.py groups
    ... napcat_query.py history <group_id> [count]
    ... napcat_query.py member <group_id> <user_id>

Notes
-----
* The socket also pushes live events to every client: skip any frame whose
  `echo` is not ours; never treat pushed events as action responses.
* `proxy=None` on the WS connect (the loopback proxy trap; see the skill).
* `retcode 1200 (EventChecker Failed)` on `member` = that user is not in the
  group (or the bot is not, or the ids are wrong).
"""
from __future__ import annotations

import json
import sys
import time

from websockets.sync.client import connect

URL = "ws://127.0.0.1:3001"


def _connect():
    try:
        return connect(URL, proxy=None, open_timeout=10)
    except TypeError:  # older websockets without the proxy kwarg
        return connect(URL, open_timeout=10)


def call(ws, action, params, timeout=25):
    echo = "napcat-query-%s-%d" % (action, int(time.time() * 1000) % 1000000)
    ws.send(json.dumps({"action": action, "params": params, "echo": echo}))
    deadline = time.time() + timeout
    while True:
        remain = deadline - time.time()
        if remain <= 0:
            return {"error": "timeout waiting for " + action}
        try:
            raw = ws.recv(timeout=remain)
        except Exception as exc:
            return {"error": "recv: %r" % (exc,)}
        try:
            msg = json.loads(raw)
        except Exception:
            continue
        if isinstance(msg, dict) and msg.get("echo") == echo:
            return msg


def cmd_groups(ws):
    r = call(ws, "get_group_list", {})
    for g in (r.get("data") or []):
        print("%s  %s/%s  %s" % (g.get("group_id"), g.get("member_count"),
                                 g.get("max_member_count"), g.get("group_name")))


def cmd_history(ws, gid, count=20):
    r = call(ws, "get_group_msg_history", {"group_id": int(gid), "count": int(count)})
    msgs = ((r or {}).get("data") or {}).get("messages") or []
    for m in msgs:
        ts = m.get("time")
        tstr = time.strftime("%m-%d %H:%M", time.localtime(ts)) if isinstance(ts, (int, float)) else str(ts)
        snd = m.get("sender") or {}
        name = snd.get("card") or snd.get("nickname") or ""
        parts = []
        for s in (m.get("message") if isinstance(m.get("message"), list) else []):
            t = s.get("type")
            d = s.get("data") or {}
            if t == "text":
                parts.append(str(d.get("text")))
            elif t == "image":
                parts.append("[图]")
            elif t == "record":
                parts.append("[语音]")
            elif t == "at":
                parts.append("@%s" % d.get("qq"))
            else:
                parts.append("[%s]" % t)
        print(tstr, snd.get("user_id"), name, "|", " ".join(parts))


def cmd_member(ws, gid, uin):
    r = call(ws, "get_group_member_info", {"group_id": int(gid), "user_id": int(uin), "no_cache": True})
    d = (r or {}).get("data") or {}
    print("retcode=%s role=%s nick=%s" % (r.get("retcode"), d.get("role"),
                                           d.get("card") or d.get("nickname")))


def main():
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        return 2
    with _connect() as ws:
        if args[0] == "groups":
            cmd_groups(ws)
        elif args[0] == "history" and len(args) >= 2:
            cmd_history(ws, args[1], args[2] if len(args) > 2 else 20)
        elif args[0] == "member" and len(args) >= 3:
            cmd_member(ws, args[1], args[2])
        else:
            print(__doc__)
            return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
