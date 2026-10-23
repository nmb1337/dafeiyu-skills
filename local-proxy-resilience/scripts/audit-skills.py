#!/usr/bin/env python3
"""技能体检：YAML 头 / 脚本语法 / 本地路径引用 / 相对引用。只读，不改文件。

用法: python audit-skills.py [skills_dir]   (默认 $HERMES_HOME/skills)
预期误报：引到 $HERMES_HOME/scripts/* 或 Hermes 仓库（共享/开发树）的引用、被空格截断的
路径正则命中（如 C:\\Program），以及 bundle 技能自身示例里的 run_tests.sh。
"""
from __future__ import annotations

import glob
import json
import os
import re
import subprocess
import sys

ROOT = sys.argv[1] if len(sys.argv) > 1 else r"C:\Users\32672\AppData\Local\hermes\skills"
PY = sys.executable
NODE = r"C:\Users\32672\AppData\Local\hermes\tools\node-26.7.0-win32-x64\node.exe"
BASH = r"C:\Users\32672\AppData\Local\hermes\tools\git-2.53.0+3-win32-x64\usr\bin\bash.exe"
if not os.path.exists(BASH):
    BASH = "bash"

issues: list[tuple[str, str]] = []
stats = {"skills": 0, "py": 0, "sh": 0, "js": 0, "md": 0}


def rel(p: str) -> str:
    return os.path.relpath(p, ROOT)


# ---- 1) SKILL.md 的 YAML 头 ----
for md in glob.glob(os.path.join(ROOT, "**", "SKILL.md"), recursive=True):
    stats["skills"] += 1
    t = open(md, encoding="utf-8", errors="replace").read()
    m = re.match(r"^---\s*\n(.*?)\n---", t, re.S)
    if not m:
        issues.append((rel(md), "缺 YAML 头"))
    else:
        fm = m.group(1)
        if not re.search(r"^name:\s*\S", fm, re.M):
            issues.append((rel(md), "YAML 头缺 name"))
        if not re.search(r"^description:\s*\S", fm, re.M):
            issues.append((rel(md), "YAML 头缺 description"))

# ---- 2) 脚本语法 ----
for f in glob.glob(os.path.join(ROOT, "**", "*.py"), recursive=True):
    stats["py"] += 1
    r = subprocess.run([PY, "-m", "py_compile", f], capture_output=True)
    if r.returncode:
        issues.append((rel(f), "Python 语法错误: " + r.stderr.decode("utf-8", "replace")[:160]))
for f in glob.glob(os.path.join(ROOT, "**", "*.sh"), recursive=True):
    stats["sh"] += 1
    r = subprocess.run([BASH, "-n", f], capture_output=True)
    if r.returncode:
        issues.append((rel(f), "sh 语法错误: " + r.stderr.decode("utf-8", "replace")[:160]))
for f in glob.glob(os.path.join(ROOT, "**", "*.js"), recursive=True) + glob.glob(os.path.join(ROOT, "**", "*.mjs"), recursive=True):
    stats["js"] += 1
    if os.path.exists(NODE):
        r = subprocess.run([NODE, "--check", f], capture_output=True)
        if r.returncode:
            issues.append((rel(f), "js 语法错误: " + r.stderr.decode("utf-8", "replace")[:160]))
for f in glob.glob(os.path.join(ROOT, "**", "*.json"), recursive=True):
    try:
        json.load(open(f, encoding="utf-8"))
    except Exception as e:  # noqa: BLE001
        issues.append((rel(f), f"JSON 解析失败: {str(e)[:100]}"))

# ---- 3) .md 里的本地路径引用是否存在 ----
win_pat = re.compile(r"[A-Za-z]:\\[^\s`\"')]\uFF0C\u3002\uFF1B]+")
msys_pat = re.compile(r"/c/Users/[^\s`\"')]\uFF0C\u3002\uFF1B]+")
skipped_words = ("<", ">", "\u2026", "...", "xxx", "XXX", "XX", "YOUR", "your", "\u53EF\u6539", "\u4F8B\u5B50", r"\path")
missing: dict[str, list[str]] = {}
for md in glob.glob(os.path.join(ROOT, "**", "*.md"), recursive=True):
    stats["md"] += 1
    txt = open(md, encoding="utf-8", errors="replace").read()
    for raw in win_pat.findall(txt) + msys_pat.findall(txt):
        if any(w in raw for w in skipped_words):
            continue
        p = raw.rstrip("`.,;:\u3001\u3002 ")
        p = p.split("`")[0].strip()
        if "*" in p or "?" in p or "{" in p:   # \u901A\u914D/\u6A21\u677F
            continue
        probe = p.replace("/c/Users/", "C:/Users/").replace("/c/", "C:/")
        probe = probe.replace("/", os.sep) if len(probe) > 2 and probe[1] == ":" else probe
        try:
            ok = os.path.exists(probe)
        except Exception:  # noqa: BLE001
            ok = True
        if not ok:
            missing.setdefault(rel(md), []).append(p)

# ---- 4) SKILL.md 里引用的同目录文件是否存在 ----
for md in glob.glob(os.path.join(ROOT, "**", "SKILL.md"), recursive=True):
    base = os.path.dirname(md)
    t = open(md, encoding="utf-8", errors="replace").read()
    for m in re.finditer(r"`((?:references|scripts|templates|assets)/[^`\s]+)`", t):
        ref = m.group(1).split("#")[0].strip()
        if any(x in ref for x in ("*", "<", "\u2026", "xxx")):
            continue
        if not os.path.exists(os.path.join(base, ref.replace("/", os.sep))):
            issues.append((rel(md), f"\u5F15\u7528\u7684\u6587\u4EF6\u4E0D\u5B58\u5728: {ref}"))

# ---- 输出 ----
print(f"\u626B\u63CF: {stats['skills']} \u4E2A\u6280\u80FD | {stats['md']} md | {stats['py']} py | {stats['sh']} sh | {stats['js']} js")
print()
print(f"== \u786C\u4F24\uFF08\u8BED\u6CD5/\u7ED3\u6784/\u5F15\u7528\uFF09{len(issues)} \u6761 ==")
for f, msg in issues[:60]:
    print(f"  \u2717 {f} :: {msg}")
if len(issues) > 60:
    print(f"  ...\u53E6\u6709 {len(issues)-60} \u6761")
print()
print(f"== \u672C\u5730\u8DEF\u5F84\u5931\u6548\uFF08{sum(len(v) for v in missing.values())} \u6761\uFF0C\u6D89\u53CA {len(missing)} \u4E2A\u6587\u4EF6\uFF09==")
for f, ps in list(missing.items())[:40]:
    for p in ps[:3]:
        print(f"  \u26A0 {f} :: {p}")
