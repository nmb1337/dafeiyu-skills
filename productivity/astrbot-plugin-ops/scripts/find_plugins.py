#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Search the AstrBot plugin registry mirror (931 rows) for candidates.

Usage:
  python find_plugins.py [keyword ...] [--min-star N] [--limit N]

Fetches konley/astrbot-plugin-source-backup/plugin_source.md through the
authenticated gh CLI, decodes the base64 markdown table and filters rows.
Keywords are matched against name + description + tags (case-insensitive).
"""
import base64
import subprocess
import sys

REG = "repos/konley/astrbot-plugin-source-backup/contents/plugin_source.md"
GH_CANDIDATES = ["gh", r"C:\Program Files\GitHub CLI\gh.exe"]


def gh_api(path):
    last = None
    for exe in GH_CANDIDATES:
        try:
            out = subprocess.run([exe, "api", path, "--jq", ".content"],
                                 capture_output=True, text=True, timeout=120)
            if out.returncode == 0 and out.stdout.strip():
                return out.stdout.strip()
            last = (out.stderr or "").strip()
        except FileNotFoundError as exc:
            last = str(exc)
    raise SystemExit("gh api failed: " + (last or "unknown"))


def main(argv):
    kw, min_star, limit = [], 0, 40
    i = 0
    while i < len(argv):
        if argv[i] == "--min-star":
            min_star = int(argv[i + 1]); i += 2; continue
        if argv[i] == "--limit":
            limit = int(argv[i + 1]); i += 2; continue
        kw.append(argv[i]); i += 1

    md = base64.b64decode(gh_api(REG)).decode("utf-8", "replace")
    rows = []
    for line in md.splitlines():
        s = line.strip()
        if not s.startswith("|") or s.startswith("|---"):
            continue
        parts = [p.strip() for p in s.strip("|").split("|")]
        if len(parts) < 6 or parts[0] == "名称":
            continue
        try:
            star = int(parts[3])
        except ValueError:
            star = -1
        rows.append((star, parts[0], parts[1], parts[4], parts[5]))

    def match(r):
        blob = (r[1] + r[3] + r[4]).lower()
        return r[0] >= min_star and (not kw or any(k.lower() in blob for k in kw))

    hits = sorted([r for r in rows if match(r)], key=lambda r: -r[0])
    for star, name, author, desc, tags in hits[:limit]:
        print(f"{star:>4}* {name} | {desc[:90]} | tags: {tags[:40]}")
    print(f"-- {len(hits)} match(es), {len(rows)} rows in registry", file=sys.stderr)


if __name__ == "__main__":
    main(sys.argv[1:])
