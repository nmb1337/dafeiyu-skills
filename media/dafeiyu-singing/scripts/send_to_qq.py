#!/usr/bin/env python3
"""把成品翻唱文件发到主人的 QQ 私聊（用户要求：成品走 QQ，不发微信）。

NapCat 优先用 OneBot 的 upload_private_file；不支持就退回 send_private_msg 的 file 段。
"""
from __future__ import annotations

import importlib.util
import os
import sys

BRIDGE = r"C:\Users\32672\AppData\Local\hermes\scripts\qq-bridge.py"
TARGET = "1568468"


def load_bridge():
    spec = importlib.util.spec_from_file_location("qq_bridge", BRIDGE)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["qq_bridge"] = mod
    spec.loader.exec_module(mod)
    return mod


def main() -> int:
    if len(sys.argv) < 2:
        print("用法: send_to_qq.py <文件路径> [显示名]")
        return 2
    path = os.path.abspath(sys.argv[1])
    name = sys.argv[2] if len(sys.argv) > 2 else os.path.basename(path)
    if not os.path.isfile(path):
        print("文件不存在:", path)
        return 3
    mb = os.path.getsize(path) / 1024 / 1024
    b = load_bridge()

    out = b.napcat_call("upload_private_file",
                        {"user_id": int(TARGET), "file": path, "name": name}, timeout=180)
    ok = isinstance(out, dict) and out.get("status") == "ok"
    print(f"  upload_private_file → {'✅ ok' if ok else str(out)[:160]}")

    if not ok:
        out2 = b.napcat_call("send_private_msg", {
            "user_id": int(TARGET),
            "message": [{"type": "file", "data": {"file": "file:///" + path.replace("\\", "/"), "name": name}}],
        }, timeout=180)
        ok = isinstance(out2, dict) and out2.get("status") == "ok"
        print(f"  退回 file 段 → {'✅ ok' if ok else str(out2)[:160]}")

    print(f"  文件: {name}（{mb:.1f} MB）→ QQ {TARGET}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
