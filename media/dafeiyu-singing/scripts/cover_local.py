# -*- coding: utf-8 -*-
"""本地视频/音频 → 大肥鱼嗓翻唱 → 发 QQ 群（含回读验证）。

用法（用「桥接 venv」跑，脚本要 import qq-bridge 模块拿 napcat_call）：
    "<bridge venv>/Scripts/python.exe" cover_local.py "<输入文件>" <输出名> [群号]

要点：
- 输入是 mp4/m4a 也 OK：先 ffmpeg 抽 44.1k wav，绝不直接喂 demucs（no channel 坑）。
- demucs 先 GPU、超时或没产物再换 CPU；产物在 work/separated/htdemucs/<wav名>/{vocals,no_vocals}.wav。
- sing.py 见 vocals.wav 已存在会跳过 demucs，直进 Seed-VC+混音。
- 交付后回读群历史核对 [文件+语音]；收尾语音丢了就自己补。
- 从聊天收到的是歌曲且值得进曲库时，顺手 ffmpeg -b:a 320k 存一份进 songs/（文件名带歌名）方便以后点歌命中。
- 系统控制台是 GBK：本脚本 print 保持 ASCII/短句即可（项目内已 reconfigure utf-8）。
"""
import subprocess, os, sys, time, importlib.util

SRC = sys.argv[1]
OUTNAME = sys.argv[2] if len(sys.argv) > 2 else "dafeiyu_cover"
GROUP = int(sys.argv[3]) if len(sys.argv) > 3 else 1093496287

ROOT = r"C:\Users\32672\Apps\dafeiyu-sing"
GSV = r"C:\Users\32672\Apps\GPT-SoVITS\.venv\Scripts\python.exe"
VENV = os.path.join(ROOT, r".venv\Scripts\python.exe")
FFMPEG = r"C:\Users\32672\AppData\Local\hermes\tools\ffmpeg-9.0.1-win32-x64\bin\ffmpeg.exe"
BRIDGE = r"C:\Users\32672\AppData\Local\hermes\scripts\qq-bridge.py"
WAV = os.path.join(ROOT, "work", "cover_local_src.wav")
OUT = os.path.join(ROOT, "output", OUTNAME + ".mp3")
SEP = os.path.join(ROOT, "work", "separated")
UMO = "napcat-qq:GroupMessage:%d" % GROUP


def run(cmd, **kw):
    print("$", " ".join(str(c) for c in cmd)[:210], flush=True)
    return subprocess.run(cmd, **kw)


print("== [0/5] extract audio ==", flush=True)
run([FFMPEG, "-y", "-i", SRC, "-vn", "-ac", "2", "-ar", "44100", "-c:a", "pcm_s16le", WAV])
print("wav:", os.path.getsize(WAV), flush=True)

print("== [1/5] demucs (gpu, cpu fallback) ==", flush=True)

def demucs(dev, tmo):
    cmd = [GSV, "-m", "demucs", "--two-stems=vocals", "-n", "htdemucs", "-o", SEP]
    if dev:
        cmd += ["-d", dev]
    cmd.append(WAV)
    try:
        return run(cmd, cwd=ROOT, timeout=tmo).returncode
    except subprocess.TimeoutExpired:
        return "TIMEOUT"

base = os.path.splitext(os.path.basename(WAV))[0]
vocals = os.path.join(SEP, "htdemucs", base, "vocals.wav")
rc = demucs(None, 420)
if not os.path.exists(vocals) and rc != 0:
    print("!! gpu demucs rc=", rc, "-> cpu retry", flush=True)
    rc = demucs("cpu", 1500)
print("demucs rc:", rc, "| vocals:", os.path.exists(vocals), flush=True)
if not os.path.exists(vocals):
    print("DEMUCS FAILED", flush=True)
    sys.exit(3)

print("== [2/5] sing.py ==", flush=True)
r = run([VENV, os.path.join(ROOT, "sing.py"), "--song", WAV, "--name", OUTNAME], cwd=ROOT, timeout=1800)
print("sing rc:", r.returncode, "| out:", os.path.exists(OUT), flush=True)
if not os.path.exists(OUT):
    print("SING FAILED", flush=True)
    sys.exit(4)

print("== [3/5] upload ==", flush=True)
spec = importlib.util.spec_from_file_location("qqbridge", BRIDGE)
bib = importlib.util.module_from_spec(spec)
sys.modules["qq_bridge"] = bib
spec.loader.exec_module(bib)
u = bib.napcat_call("upload_group_file", {"group_id": GROUP, "file": OUT, "name": os.path.basename(OUT)}, timeout=300)
print("upload:", str(u)[:140], flush=True)

print("== [4/5] closing voice ==", flush=True)
try:
    a = bib._make_voice("唱好啦——刚出锅，趁热听～")
    ok = bool(a) and bib.send_voice(UMO, a)
    if not ok:
        bib.send_qq(UMO, "唱好啦——刚出锅，趁热听～", force_text=True)
    print("say ok:", ok, flush=True)
except Exception as e:
    print("say fail (ignored):", e, flush=True)

print("== [5/5] readback ==", flush=True)
time.sleep(5)
try:
    h = bib.napcat_call("get_group_msg_history", {"group_id": GROUP, "count": 5}, timeout=60)
    for m in (h.get("data") or {}).get("messages") or []:
        segs = [s.get("type") for s in (m.get("message") or [])]
        print("  HIST", (m.get("sender") or {}).get("nickname", "?"), segs, flush=True)
except Exception as e:
    print("readback failed:", e, flush=True)
print("COVER DONE", flush=True)
