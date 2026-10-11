#!/usr/bin/env python3
"""大肥鱼翻唱流水线（本地、离线）。

流程：
    song.mp3
      ├─ demucs 分离 ─→ vocals.wav（要唱的那条）+ no_vocals.wav（伴奏）
      ├─ Seed-VC 歌声转换：vocals.wav + 大肥鱼参考音 → 大肥鱼唱的人声
      └─ ffmpeg 混音（换掉原唱、保留伴奏）→ 成品 mp3

用法：
    python sing.py --song "C:/path/song.mp3" [--no-vocals path] [--semi-tones N] [--name out]
    python sing.py --source-vocal vocals.wav --reference ref1.wav   # 已经有干声时直接转

关键：Seed-VC 是零样本的，不用训练；参考音就是本鱼平时说话那几段（1~30 秒）。
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys

ROOT = r"C:\Users\32672\Apps\dafeiyu-sing"
SEEDVC = os.path.join(ROOT, "seed-vc-main")
PY = os.path.join(ROOT, ".venv", "Scripts", "python.exe")
GSV_PY = r"C:\Users\32672\Apps\GPT-SoVITS\.venv\Scripts\python.exe"   # demucs 装在这里
FFMPEG = r"C:\Users\32672\AppData\Local\hermes\tools\ffmpeg-9.0.1-win32-x64\bin\ffmpeg.exe"
DEFAULT_REF = r"C:\Users\32672\Apps\GPT-SoVITS\refs\dafeiyu_voice.wav"   # 和说话(TTS)用同一段参考音！
# 踩过的坑：之前用的是自己从干净人声里另切的 20 秒（中位 243Hz / B3），比 TTS 那段（297Hz / D4）低，
# Seed-VC 的 auto-f0-adjust 会把歌声往参考音的音区拽 → 唱出来比原唱低 6.6 个半音，
# 听起来"和说话的嗓不是一个人"，而且和伴奏不在一个调上。换成同一段参考后，输出与原唱只差 -0.5 个半音。
WORK = os.path.join(ROOT, "work")
OUT = os.path.join(ROOT, "output")


def run(cmd, **kw):
    print("  $", " ".join(str(c) for c in cmd[:6]), "..." if len(cmd) > 6 else "")
    return subprocess.run(cmd, capture_output=True, text=True, **kw)


def separate(song: str, tag: str) -> tuple[str, str]:
    """demucs 分出人声与伴奏。返回 (vocals, no_vocals)。

    demucs 的输出路径是 <outdir>/htdemucs/<歌曲文件名（不含扩展名）>/{vocals,no_vocals}.wav，
    没有 --name 这个参数（写成 --name 会被当成模型名报 "is neither a single pre-trained model"）。
    注意：demucs 是在 cwd=work/ 下跑的，--song 传相对路径会找不到文件 → 这里统一转绝对路径。
    """
    song = os.path.abspath(song)
    outroot = os.path.join(WORK, "separated")
    stem = os.path.splitext(os.path.basename(song))[0]
    outdir = os.path.join(outroot, "htdemucs", stem)
    vocal = os.path.join(outdir, "vocals.wav")
    if not os.path.isfile(vocal):
        print("[1/3] 分离人声/伴奏（demucs）…")
        r = run([GSV_PY, "-m", "demucs", "--two-stems=vocals", "-n", "htdemucs",
                 "-o", outroot, song], cwd=WORK)
        if r.returncode != 0:
            print("  demucs 失败：", (r.stderr or "")[-500:])
    return (vocal, os.path.join(outdir, "no_vocals.wav"))


def convert(vocal: str, reference: str, tag: str, semi_tones: int, steps: int, fp16: bool) -> str:
    """Seed-VC 歌声转换 → work/conv/<tag>/vc.wav"""
    outdir = os.path.join(WORK, "conv", tag)
    os.makedirs(outdir, exist_ok=True)
    print("[2/3] 换音色（Seed-VC，零样本）…")
    cmd = [PY, os.path.join(SEEDVC, "inference.py"),
           "--source", vocal, "--target", reference, "--output", outdir,
           "--diffusion-steps", str(steps), "--inference-cfg-rate", "0.7",
           "--f0-condition", "True", "--auto-f0-adjust", "True",
           "--semi-tone-shift", str(semi_tones), "--fp16", "True" if fp16 else "False"]
    env = dict(os.environ)
    env["HF_ENDPOINT"] = "https://hf-mirror.com"          # 模型从国内镜像拉
    # hf-mirror / 国内站点直连更快；本机 shell 里挂着加速器中转，绕过去反而会 TLS 断
    for k in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "http_proxy", "https_proxy", "GIT_PROXY_COMMAND"):
        env.pop(k, None)
    env["NO_PROXY"] = env.get("NO_PROXY", "") + ",hf-mirror.com,huggingface.co,127.0.0.1,localhost"
    r = subprocess.run(cmd, cwd=SEEDVC, capture_output=True, text=True, env=env)
    if r.returncode != 0:
        print("  Seed-VC 失败：", (r.stderr or "")[-600:])
        return ""
    files = [f for f in os.listdir(outdir) if f.lower().endswith((".wav", ".flac"))]
    if not files:
        print("  没发现输出文件；stdout 尾部：", (r.stdout or "")[-300:])
        return ""
    files.sort(key=lambda f: os.path.getmtime(os.path.join(outdir, f)), reverse=True)
    return os.path.join(outdir, files[0])


def mix(vocal: str, no_vocals: str, out_name: str) -> str:
    """把换好的人声和伴奏合起来，导出 mp3。"""
    os.makedirs(OUT, exist_ok=True)
    dst = os.path.join(OUT, out_name + ".mp3")
    print("[3/3] 混音导出 …")
    if no_vocals and os.path.isfile(no_vocals):
        cmd = [FFMPEG, "-y", "-i", vocal, "-i", no_vocals,
               "-filter_complex", "[0:a]volume=1.0[v];[1:a]volume=0.85[m];[v][m]amix=inputs=2:duration=longest:dropout_transition=0",
               "-b:a", "192k", dst]
    else:
        cmd = [FFMPEG, "-y", "-i", vocal, "-b:a", "192k", dst]
    r = run(cmd)
    if r.returncode != 0:
        print("  ffmpeg 失败：", (r.stderr or "")[-300:])
        return ""
    return dst


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--song", help="整首歌（自动分离人声/伴奏）")
    ap.add_argument("--source-vocal", help="已经是干声，直接转换")
    ap.add_argument("--no-vocals", help="伴奏文件（配合 --source-vocal）")
    ap.add_argument("--reference", default=DEFAULT_REF, help="大肥鱼参考音（1~30 秒）")
    ap.add_argument("--semi-tones", type=int, default=0)
    ap.add_argument("--steps", type=int, default=30)
    ap.add_argument("--cpu", action="store_true", help="强制不用 fp16")
    ap.add_argument("--name", default="dafeiyu_sing")
    a = ap.parse_args()

    os.makedirs(WORK, exist_ok=True)
    if a.song:
        tag = os.path.splitext(os.path.basename(a.song))[0]
        vocal, nv = separate(a.song, tag)
    elif a.source_vocal:
        tag = os.path.splitext(os.path.basename(a.source_vocal))[0]
        vocal, nv = a.source_vocal, a.no_vocals
    else:
        print("要用 --song 或 --source-vocal 指定输入")
        return 2

    if not vocal or not os.path.isfile(vocal):
        print("找不到人声文件：", vocal)
        return 3
    conv = convert(vocal, a.reference, tag, a.semi_tones, a.steps, not a.cpu)
    if not conv:
        return 4
    out = mix(conv, nv, a.name)
    print("成品：", out)
    return 0 if out else 5


if __name__ == "__main__":
    raise SystemExit(main())
