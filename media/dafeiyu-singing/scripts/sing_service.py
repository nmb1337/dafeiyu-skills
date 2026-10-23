#!/usr/bin/env python3
"""QQ 里说「唱首歌」/「唱《歌名》」→ 自动找歌、换大肥鱼嗓、把成品发回聊天。

被 qq-bridge.py 以子进程方式拉起（detached），跑完自己把文件上传到会话里。
流程：
    解析请求 → 找歌（本地曲库 / 消息里的链接 / B站搜索）→ sing.py 转换 → 上传成品
"""
from __future__ import annotations

import argparse
import glob
import importlib.util
import os
import re
import subprocess
import sys
import time

# 控制台是 GBK：歌名带 emoji 时 print 会崩（🥳 踩过），把本进程 stdio 锁成 utf-8。
for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

ROOT = r"C:\Users\32672\Apps\dafeiyu-sing"
SONGS = os.path.join(ROOT, "songs")
OUT = os.path.join(ROOT, "output")
BRIDGE = r"C:\Users\32672\AppData\Local\hermes\scripts\qq-bridge.py"
UVX = r"C:\Users\32672\AppData\Local\hermes\tools\uv-0.12.3-win32-x64\uvx.exe"
PY = os.path.join(ROOT, ".venv", "Scripts", "python.exe")
FFMPEG = r"C:\Users\32672\AppData\Local\hermes\tools\ffmpeg-9.0.1-win32-x64\bin\ffmpeg.exe"
FFMPEG_DIR = os.path.dirname(FFMPEG)
LOCK = os.path.join(ROOT, "work", "sing.lock")
PENDING = os.path.join(ROOT, "work", "sing_queue.txt")   # 忙时排队的点歌单，唱完自动接力（2026-10-15）

_URL = re.compile(r"https?://[^\s]+")
_QUOTED = re.compile(r"[《“\"「]([^》”\"」]{1,40})[》”\"」]")
_TRIGGER = re.compile(r"唱(?:首歌|首|一首|个歌|一个|一下|支|曲|情歌|老歌|快歌|慢歌|甜歌|伤感歌|英文歌|日语歌|粤语歌|儿歌|歌|这个|这首|这首歌)"
                      r"|翻唱(?:《|“|\"|「|这个|这首|一下)"
                      r"|来(?:一首|首歌|首)|给本?鱼唱")
# 抠歌名时只吞量词、不吞题材词：「唱情歌」要留下「情歌」当搜索词，别把它当量词吃掉
_CONSUME = re.compile(r"唱(?:首歌|首|一首|个歌|一个|一下|支|曲)?|翻唱(?:这个|这首|这首歌|一下)?|来(?:一首|首歌|首)|给本?鱼唱")


def log(*a) -> None:
    print(f"[{time.strftime('%H:%M:%S')}]", *a, flush=True)


def load_bridge():
    spec = importlib.util.spec_from_file_location("qq_bridge", BRIDGE)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["qq_bridge"] = mod
    spec.loader.exec_module(mod)
    return mod


def parse_request(text: str):
    """返回 (类型, 值)：('url', 链接) / ('name', 歌名) / ('random', '') / (None, None)

    「唱一首平凡之路」这种没书名号的也要认（之前只认《》里的 → 被当成随便来一首 ✗）。
    """
    text = (text or "").strip()
    m = _URL.search(text)
    if m:
        return "url", m.group(0)
    if not _TRIGGER.search(text):
        return None, None
    q = _QUOTED.search(text)
    if q:
        return "name", q.group(1).strip()
    hit = _CONSUME.search(text)
    rest = text[hit.end():] if hit else ""
    rest = re.sub(r"^[，,。.、!！?？:：\s]*(?:一首|个|首|下|点|的|歌|曲)*[，,。.、!！?？:：\s]*", "", rest)
    rest = rest.strip(" ，,。.、!！?？:：")
    if rest and not re.fullmatch(r"[吧呗啊呢呀哈嘛~～。!！?？]*", rest):
        return "name", rest
    # 「唱首歌」这种没点名的 → 从曲库里随便挑一首
    return "random", ""


_BUV = [None]


def _bili_headers() -> dict:
    """B站匿名搜索要一个 buvid3/buvid4，没有它搜索接口只会回一页 HTML。"""
    import json as _json
    import urllib.request
    if _BUV[0] is None:
        b3 = b4 = ""
        try:
            req = urllib.request.Request("https://api.bilibili.com/x/frontend/finger/spi",
                                         headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = _json.load(resp).get("data") or {}
                b3, b4 = str(data.get("b_3") or ""), str(data.get("b_4") or "")
        except Exception as exc:
            log("拿 buvid 失败:", exc)
        _BUV[0] = (b3, b4)
    b3, b4 = _BUV[0]
    return {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120",
            "Referer": "https://www.bilibili.com/",
            "Cookie": f"buvid3={b3}; buvid4={b4}"}


_BAD_WORDS = ("伴奏", "纯音乐", "钢琴", "吉他谱", "教学", "教程", "铃声", "remix", "instrumental", "dj版")
_JUNK_WORDS = ("梗", "指南", "解说", "科普", "反应", "reaction", "评测", "盘点", "排行榜", "鬼畜", "搞笑",
               "怎么唱", "教学", "教程", "背景", "故事", "合集", "循环", "串烧", "b站", "up主")
_GOOD_WORDS = ("原唱", "官方", "mv", "完整版", "高音质", "无损", "音频", "歌曲", "正式版", "专辑")


def _score_result(title: str, secs: int, name: str) -> int:
    """给搜索结果打分：要的是"能拿来唱的那首歌"，不是解说/梗/伴奏。"""
    t = title.lower()
    score = 0
    score += 3 * sum(1 for w in _GOOD_WORDS if w in t)
    score -= 5 * sum(1 for w in _JUNK_WORDS if w in t)
    score -= 4 * sum(1 for w in _BAD_WORDS if w in t)
    if name and name in title:
        score += 4
    if 150 <= secs <= 400:          # 2:30~6:40 最像一首歌
        score += 3
    elif secs > 400:
        score -= 2                  # 太长的多半是合集
    return score


def search_bili(name: str) -> str:
    """按歌名（或题材，如「情歌」）去 B站搜一个能唱的音频视频，返回视频 URL（找不到返回 ""）。

    只给唱歌流水线用 —— 外人点歌也允许下载，但下载能力只存在这条流水线里。
    题材词（情歌/老歌/伤感…）没写清哪首时：靠打分随便挑一首最能唱的。
    """
    import json as _json
    import re as _re
    import urllib.parse
    import urllib.request
    _GENRE = ("情歌", "快歌", "慢歌", "老歌", "伤感", "甜歌", "摇滚", "民谣", "流行", "古风",
              "粤语", "英文歌", "日语歌", "儿歌", "电音", "说唱", "网络歌曲", "经典老歌")
    kws = [f"{name} 原唱", f"{name} 歌曲", f"{name} 音频"]
    if any(g in name for g in _GENRE) and len(name) <= 8:
        kws = [f"{name} 歌曲", f"{name} 原唱", f"{name} 好听", f"{name} 热门"]
    for kw in kws:
        url = ("https://api.bilibili.com/x/web-interface/search/type?search_type=video"
               f"&keyword={urllib.parse.quote(kw)}&page=1")
        try:
            req = urllib.request.Request(url, headers=_bili_headers())
            with urllib.request.urlopen(req, timeout=20) as resp:
                data = _json.load(resp)
        except Exception as exc:
            log("B站搜索失败:", type(exc).__name__, str(exc)[:80])
            continue
        results = ((data.get("data") or {}).get("result") or [])
        best, best_score = "", -99
        for r in results:
            title = _re.sub(r"<[^>]+>", "", str(r.get("title") or ""))
            try:
                mm, ss = str(r.get("duration") or "").split(":")[-2:]
                secs = int(mm) * 60 + int(ss)
            except Exception:
                continue
            if not (60 <= secs <= 600):
                continue
            bvid = str(r.get("bvid") or "")
            if not bvid:
                continue
            sc = _score_result(title, secs, name)
            if sc > best_score:
                best, best_score = f"https://www.bilibili.com/video/{bvid}", sc
                log(f"  候选 {sc:+d}: {title[:44]} | {secs//60}:{secs%60:02d}")
        if best and best_score >= 3:
            log(f"B站选中（{best_score:+d}）: {best}")
            return best
    return ""


def find_local(name: str) -> str:
    if not name:
        return ""
    cands = glob.glob(os.path.join(SONGS, "*"))
    for f in cands:
        if name and name in os.path.basename(f):
            return f
    return ""


def fetch_song(kind: str, value: str):
    """返回本地音频路径；找不到返回 ''。"""
    if kind == "url":
        out = os.path.join(SONGS, "%(title).60s.%(ext)s")
        log("下载链接里的歌…")
        t0 = time.time()
        r = subprocess.run([UVX, "yt-dlp", "-f", "bestaudio/best", "-x", "--audio-format", "mp3",
                            "--ffmpeg-location", FFMPEG_DIR,
                            "-o", out, value], capture_output=True, text=True,
                           encoding="utf-8", errors="replace",
                           env=_clean_env(), timeout=600)
        tail = (r.stderr or "").strip().splitlines()
        log("yt-dlp 返回", r.returncode, ("| " + tail[-1][:150]) if (r.returncode and tail) else "")
        files = sorted(glob.glob(os.path.join(SONGS, "*")), key=os.path.getmtime, reverse=True)
        if not files:
            return ""
        newest = files[0]
        if os.path.getmtime(newest) < t0 - 10:
            log("下载没产出新文件（老文件不算数）")
            return ""
        # 转换失败时 yt-dlp 会留下原始格式（m4a/aac…），demucs 读不了 —— 用 ffmpeg 硬转成 mp3
        if not newest.lower().endswith(".mp3"):
            mp3 = os.path.splitext(newest)[0] + ".mp3"
            log("非 mp3（" + os.path.splitext(newest)[1] + "）→ ffmpeg 硬转…")
            rr = subprocess.run([FFMPEG, "-y", "-i", newest, "-b:a", "320k", mp3],
                                capture_output=True, text=True, encoding="utf-8",
                                errors="replace", timeout=300)
            if os.path.isfile(mp3) and os.path.getsize(mp3) > 100000:
                try:
                    os.remove(newest)
                except OSError:
                    pass
                newest = mp3
            else:
                log("硬转失败：", (rr.stderr or "")[-150:])
        return newest
    if kind == "name":
        hit = find_local(value)
        if hit:
            log("曲库里已有:", os.path.basename(hit))
            return hit
        # 曲库没有 → 自己去 B站 搜一个（唱歌流水线内部能力；对外人也是只准用来唱歌）
        link = search_bili(value)
        if link:
            log("去下载:", link)
            return fetch_song("url", link)
        log(f"搜不到《{value}》")
        return ""
    # random
    cands = sorted(glob.glob(os.path.join(SONGS, "*")), key=os.path.getmtime, reverse=True)
    return cands[0] if cands else ""


def _clean_env():
    env = dict(os.environ)
    for k in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "http_proxy", "https_proxy"):
        env.pop(k, None)
    env["UV_DEFAULT_INDEX"] = "https://pypi.tuna.tsinghua.edu.cn/simple"
    env["PYTHONUTF8"] = "1"          # 子进程（sing.py 及其下游）全部 utf-8，防 GBK 崩
    env["PYTHONIOENCODING"] = "utf-8"
    return env


def upload(b, umo: str, path: str) -> bool:
    parts = str(umo).split(":")
    kind, target = (parts[1] if len(parts) > 2 else ""), parts[-1]
    name = os.path.basename(path)
    if kind == "GroupMessage" and target.isdigit():
        out = b.napcat_call("upload_group_file",
                            {"group_id": int(target), "file": path, "name": name}, timeout=300)
    elif kind == "FriendMessage" and target.isdigit():
        out = b.napcat_call("upload_private_file",
                            {"user_id": int(target), "file": path, "name": name}, timeout=300)
    else:
        return False
    return isinstance(out, dict) and out.get("status") == "ok"


def say(b, umo: str, text: str) -> None:
    """回合里说话：优先语音（走桥接自己的发送链），失败就发文字。"""
    try:
        if text and len(text) <= 90:
            audio = b._make_voice(text)
            if audio and b.send_voice(umo, audio):
                return
        b.send_qq(umo, text)
    except Exception as exc:
        log("说话失败:", exc)


def pretty_title(raw: str) -> str:
    """文件名 → 说话时用的短歌名。

    曲库里的文件名常带频道前缀（【平凡之路注定不平凡！高考加油！】朴树《平凡之路》百万豪装录音棚大声听），
    直接念出来又长又蠢；优先取《》里的，其次取最像歌名的一段，再截断。
    """
    t = os.path.splitext(os.path.basename(raw or ""))[0]
    m = re.search(r"[《“\"「]([^》”\"」]{1,20})[》”\"」]", t)
    if m:
        return m.group(1).strip()
    t = re.sub(r"^[\[【(（][^】\])）]{1,30}[】\])）]\s*", "", t)     # 去掉开头的中括号前缀
    t = re.sub(r"(无损音质|百万豪装|录音棚|大声听|高音质|完整版|官方|MV|1080P|4K)", " ", t)
    t = re.sub(r"[\[\]【】()（）]", " ", t)
    t = re.sub(r"\s+", " ", t).strip(" -_·")
    return (t or "这首歌")[:20]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("umo")
    ap.add_argument("text")
    ap.add_argument("--name", default="")
    a = ap.parse_args()

    # 干净环境跑：本机 shell 的代理指向自建中转，中转挂了会把 B站搜索也掐死
    for k in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "http_proxy", "https_proxy", "all_proxy"):
        os.environ.pop(k, None)

    os.makedirs(os.path.join(ROOT, "work"), exist_ok=True)
    os.makedirs(OUT, exist_ok=True)
    # 一次只跑一首（在跑就别叠）；锁太老 = 上次任务被掐死了，清掉继续
    # （2026-10-15 踩过：任务被 kill 后残留锁 → 之后所有点歌都被「已在跑」静默跳过）
    if os.path.exists(LOCK):
        age = time.time() - os.path.getmtime(LOCK)
        if age < 1800:
            # 忙，但不吞单：记进待唱队列，唱完自动接力（2026-10-15）
            try:
                with open(PENDING, "a", encoding="utf-8") as fh:
                    fh.write((a.umo + "\t" + a.text).replace("\n", " ") + "\n")
                b0 = load_bridge()
                b0.send_qq(a.umo, "本鱼嗓子正忙着唱上一首呢，这首给你排上了，唱完就来～", force_text=True)
            except Exception as exc:
                log("排队失败:", exc)
            log("已有任务在跑 → 已排队，不吞单")
            return 1
        log(f"清掉过期锁（残留 {int(age)}s，上次任务可能被掐死）")
    with open(LOCK, "w", encoding="utf-8") as fh:
        fh.write(str(time.time()))

    b = load_bridge()
    umo, text = a.umo, a.text
    try:
        kind, value = parse_request(text)
        if not kind:
            return 2
        log(f"点歌请求 kind={kind} value={value!r} → {umo}")

        song = fetch_song(kind, value)
        if not song:
            say(b, umo, "这首歌本鱼没找着，你发个链接或者文件给本鱼，本鱼立马唱。")
            return 3
        title = pretty_title(song)
        say(b, umo, f"收到，这就用本鱼的嗓唱《{title}》，几分钟…")
        log("开唱:", song)

        out_name = a.name or ("dafeiyu_" + str(abs(hash(title)) % 100000))
        r = subprocess.run([PY, os.path.join(ROOT, "sing.py"), "--song", song, "--name", out_name],
                           capture_output=True, text=True,
                           encoding="utf-8", errors="replace",
                           cwd=ROOT, env=_clean_env(), timeout=3600)
        log("sing.py 返回", r.returncode, (r.stdout or "")[-300:], (r.stderr or "")[-300:])
        mp3 = os.path.join(OUT, out_name + ".mp3")
        if not os.path.isfile(mp3):
            say(b, umo, "唱到一半翻车了，本鱼回头看看日志。")
            return 4
        ok = upload(b, umo, mp3)
        log("上传:", ok, mp3)
        # 语音版双发（主人 2026-10-16 定：每首歌唱完「语音条 + 文件」都发；NapCat 自动转 silk）
        try:
            if b.send_voice(umo, mp3):
                log("语音版已发:", mp3)
            else:
                log("语音版发送失败（文件已在，不影响）")
        except Exception as exc:
            log("语音版发送异常:", str(exc)[:120])
        say(b, umo, "唱好了，听听这个味儿行不行。" if ok else "唱好了，但文件传不上去，本鱼再想办法。")
        return 0 if ok else 5
    finally:
        try:
            os.remove(LOCK)
        except OSError:
            pass
        # 待唱队列接力：忙时排进来的单子，唱完自动接着唱（2026-10-15）
        try:
            if os.path.exists(PENDING):
                lines = [l for l in open(PENDING, encoding="utf-8").read().splitlines() if l.strip()]
                if lines:
                    head, rest = lines[0], lines[1:]
                    with open(PENDING, "w", encoding="utf-8") as fh:
                        fh.write("\n".join(rest) + ("\n" if rest else ""))
                    parts = head.split("\t", 1)
                    if len(parts) == 2 and parts[0] and parts[1]:
                        subprocess.Popen([sys.executable, os.path.abspath(__file__), parts[0], parts[1]],
                                         cwd=ROOT,
                                         creationflags=(subprocess.CREATE_NO_WINDOW | subprocess.DETACHED_PROCESS))
                        log("队列接力 →", parts[1][:40])
        except Exception as exc:
            log("接力失败:", exc)


if __name__ == "__main__":
    raise SystemExit(main())
