#!/usr/bin/env python3
"""Capture a QR-login URL from a Hermes gateway adapter and render it as a scannable PNG.

Run with the Hermes RUNTIME venv python, from the hermes-agent checkout root, so that
`import gateway.*` resolves:

    cd "$HERMES_HOME/hermes-agent"
    "$VENV_PY" scripts/capture_qr_login.py <out_dir> [adapter_module] [login_fn] [timeout_s]

Defaults target the Weixin/iLink adapter (`gateway.platforms.weixin:qr_login`).

Outputs into <out_dir>:
    qr_url.txt           the URL to encode / open (also printed as QR_URL)
    login_qr.png         the rendered QR image -- deliver this to the user
    login_result.json    credential payload once confirmed (CONTAINS THE TOKEN)

The adapter saves the credentials itself; this script never prints them. Delete the output directory
when the flow is finished -- login_result.json holds the bot token.
"""

from __future__ import annotations

import asyncio
import importlib
import json
import os
import sys
from pathlib import Path


def _render(out_dir: Path, url: str) -> None:
    if not url:
        return
    (out_dir / "qr_url.txt").write_text(url, encoding="utf-8")
    png = out_dir / "login_qr.png"
    try:
        import qrcode

        qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_M, box_size=10, border=3)
        qr.add_data(url)
        qr.make(fit=True)
        qr.make_image(fill_color="black", back_color="white").save(str(png))
        print(f"QR_PNG {png}", flush=True)
    except Exception as exc:  # noqa: BLE001
        print(f"QR render failed ({exc}) -- open the URL below instead", flush=True)
    print(f"QR_URL {url}", flush=True)


def main() -> int:
    args = sys.argv[1:]
    out_dir = Path(args[0] if args else ".").resolve()
    adapter_mod = args[1] if len(args) > 1 else "gateway.platforms.weixin"
    login_fn_name = args[2] if len(args) > 2 else "qr_login"
    timeout_s = int(args[3]) if len(args) > 3 else 420

    out_dir.mkdir(parents=True, exist_ok=True)
    hermes_home = os.environ.get("HERMES_HOME") or str(Path.home() / ".hermes")

    mod = importlib.import_module(adapter_mod)

    original = getattr(mod, "_print_qr", None)
    if original is None:
        print(
            f"{adapter_mod} exposes no _print_qr; watch stdout for the URL and encode it yourself",
            flush=True,
        )
    else:

        def patched(*a, **kw):  # noqa: ANN002, ANN003
            # The vendor URL is the scannable string; the bare hex token in the API response is not.
            for value in list(a) + list(kw.values()):
                if isinstance(value, str) and value.startswith("http"):
                    _render(out_dir, value)
                    return
            _render(out_dir, next((v for v in a if isinstance(v, str)), ""))

        mod._print_qr = patched

    login_fn = getattr(mod, login_fn_name)
    creds = asyncio.run(login_fn(hermes_home, timeout_seconds=timeout_s))

    (out_dir / "login_result.json").write_text(
        json.dumps(creds or {}, ensure_ascii=False), encoding="utf-8"
    )
    print(f"LOGIN_OK {bool(creds)}", flush=True)
    if creds:
        print(f"account_id: {creds.get('account_id')}", flush=True)
    print("delete login_result.json when done -- it holds the credential", flush=True)
    return 0 if creds else 1


if __name__ == "__main__":
    raise SystemExit(main())
