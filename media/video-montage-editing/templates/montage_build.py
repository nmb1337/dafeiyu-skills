# -*- coding: utf-8 -*-
"""卡点 montage 构建模板：改 SHOTS 表 + 顶部常量即可跑。
运行：<sing venv>/Scripts/python.exe montage_build.py（需要 numpy）
输出：OUT（.mp4）+ 打印 ffprobe 质检。

SHOTS 表字段：
  i/o   : 源视频入/出点（秒）
  sp    : 播放速度（0.42 = 慢镜, 1.3 = 提速）
  zoom  : zoompan z 表达式（以输出帧 on 计；"1.0" = 不缩放）
  shake : True = 手持抖动（crop 位移衰减）
  rgb   : True = RGB 分离（rgbashift）
  grade : ffmpeg 滤镜串（eq/vignette/hue 等）
  flash : ("white"|"black", 秒) 或 None —— 镜头开头的闪白/黑场
  tpad  : 定格补帧秒数（结尾冻结）
  text  : [(文本, 字号, t0, t1, y比例)]
  fin   : 额外滤镜（如 fade=t=out:st=..:d=..:color=black）
  vol   : 游戏原声音量（慢镜 0.5，正常 0.85，定格 0）
"""
import os
import subprocess
import wave

import numpy as np

FFBIN = r"C:\Users\32672\AppData\Local\hermes\tools\ffmpeg-9.0.1-win32-x64\bin"
FF = os.path.join(FFBIN, "ffmpeg.exe")
FP = os.path.join(FFBIN, "ffprobe.exe")
SRC = r"C:/path/to/source.mp4"
SONG = r"C:/Users/32672/Apps/dafeiyu-sing/songs/歌名.mp3"
WD = r"C:/Users/32672/AppData/Local/hermes/cache/scratch"
BGM_WAV = os.path.join(WD, "bgm.wav")
SFX_WAV = os.path.join(WD, "sfx_bed.wav")
OUT = os.path.join(WD, "montage_out.mp4")
FONT = r"C:\Windows\Fonts\msyhbd.ttc"
FONT_ESC = "C\\:/Windows/Fonts/" + os.path.basename(FONT)
MUSIC_START = 0.0      # 从歌曲的节拍边界切
TOTAL = 16.0           # 成片目标长度
SR = 48000
rng = np.random.default_rng(7)

# --- 示例：击杀落在 4.092s（= 目标小节重拍），结尾最后 1 秒白闪→淡黑 ---
SHOTS = [
    dict(i=0.60, o=2.04, sp=0.55, zoom="1+0.035*on/60", shake=False, rgb=False,
         grade="eq=contrast=1.12:brightness=-0.05:saturation=0.85,vignette=PI/4",
         flash=("black", 0.30), tpad=0, vol=0.50,
         text=[("烟 中 猎 杀", 80, 0.45, 2.30, 0.60)], fin=None),
    dict(i=2.04, o=3.30, sp=1.30, zoom="1.06", shake=False, rgb=False,
         grade="eq=contrast=1.06:saturation=1.10", flash=("white", 0.05),
         tpad=0, vol=0.85, text=[], fin=None),
    dict(i=3.30, o=3.93, sp=1.2475, zoom="1.08", shake=False, rgb=False,
         grade="eq=contrast=1.07:saturation=1.12", flash=("white", 0.05),
         tpad=0, vol=0.85, text=[], fin=None),
    dict(i=4.92, o=5.78, sp=0.42, zoom="1+0.088*on/60", shake=True, rgb=True,
         grade="eq=contrast=1.16:saturation=1.22:brightness=0.01", flash=("white", 0.12),
         tpad=0, vol=0.50, text=[("一 枪 送 走", 86, 0.55, 2.00, 0.58)], fin=None),
    dict(i=8.90, o=9.015, sp=0.50, zoom="1+0.006*on/60", shake=False, rgb=False,
         grade="hue=s=0,eq=contrast=1.22:brightness=-0.06,vignette=PI/3.2",
         flash=None, tpad=2.001, vol=0.0,
         text=[("G G", 112, 0.40, 2.23, 0.40), ("大肥鱼剪辑", 34, 0.40, 2.23, 0.90)], fin=None),
    dict(i=8.90, o=9.015, sp=0.50, zoom="1+0.012*on/60", shake=False, rgb=False,
         grade="hue=s=0,eq=contrast=1.22:brightness=-0.06,vignette=PI/3.2",
         flash=("white", 0.12), tpad=0.770, vol=0.0,
         text=[("G G", 112, 0.00, 1.00, 0.40), ("大肥鱼剪辑", 34, 0.00, 1.00, 0.90)],
         fin="fade=t=out:st=0.25:d=0.75:color=black"),
]


def dur(s):
    return (s["o"] - s["i"]) / s["sp"] + s["tpad"]


def drawtext(txt, size, t0, t1, yf):
    return ("drawtext=fontfile='%s':text='%s':fontsize=%d:fontcolor=white:"
            "borderw=5:bordercolor=black@0.55:shadowx=3:shadowy=3:shadowcolor=black@0.45:"
            "x=(w-text_w)/2:y=h*%.2f:enable='between(t\\,%s\\,%s)'"
            % (FONT_ESC, txt, size, yf, round(t0, 2), round(t1, 2)))


def env(n, k):
    return np.exp(-np.arange(n) / SR * k)


def boom(d=0.9, f=52.0):
    n = int(d * SR)
    tt = np.arange(n) / SR
    return (np.sin(2 * np.pi * f * tt) * env(n, 4.5) + rng.standard_normal(n) * env(n, 55) * 0.35) * 0.9


def build_sfx(cue_times):
    mix = np.zeros((int((TOTAL + 0.1) * SR), 2))
    for at in cue_times:
        s = boom()
        i0 = int(at * SR)
        n = min(len(s), len(mix) - i0)
        if n > 0:
            mix[i0:i0 + n] += (s[:n] * 0.9)[:, None]
    mix = mix / (np.abs(mix).max() or 1) * 0.85
    with wave.open(SFX_WAV, "wb") as f:
        f.setnchannels(2)
        f.setsampwidth(2)
        f.setframerate(SR)
        f.writeframes((mix.clip(-1, 1) * 32767).astype("<i2").tobytes())


def extract_bgm():
    r = subprocess.run([FF, "-y", "-ss", "%.2f" % MUSIC_START, "-t", "%.2f" % TOTAL,
                        "-i", SONG, "-vn", "-ac", "2", "-ar", str(SR), BGM_WAV],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode:
        raise SystemExit((r.stderr or "")[-1200:])


def main():
    t = 0.0
    for k, s in enumerate(SHOTS):
        print("S%d %7.3f -> %7.3f (%.3fs)" % (k + 1, t, t + dur(s), dur(s)))
        t += dur(s)
    print("总长 %.3fs（目标 %.2fs）" % (t, TOTAL))
    kill_t = sum(dur(s) for s in SHOTS[:3])   # 按设计改：钱镜头起始时刻
    print("钱镜头切入 = %.3fs" % kill_t)

    build_sfx([kill_t, kill_t + 5.614, kill_t + 8.677, 15.0])
    extract_bgm()

    parts = []
    for idx, s in enumerate(SHOTS):
        ch = [f"[0:v]trim=start={s['i']}:end={s['o']},setpts=(PTS-STARTPTS)/{s['sp']}"]
        ch.append("minterpolate=fps=60:mi_mode=mci:mc_mode=aobmc:vsbmc=1" if s["sp"] < 0.9 else "fps=60")
        if s["zoom"] != "1.0":
            ch.append("zoompan=z='%s':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=1:s=1280x960:fps=60" % s["zoom"])
        if s["shake"]:
            ch.append("crop=1200:900:x='(in_w-1200)/2+12*sin(80*t)*exp(-5*t)':y='(in_h-900)/2+10*cos(95*t)*exp(-5*t)'")
            ch.append("scale=1280:960:flags=lanczos")
        ch.append(s["grade"])
        if s["rgb"]:
            ch.append("rgbashift=rh=3:bh=-3:gv=1")
        if s["tpad"]:
            ch.append("tpad=stop_mode=clone:stop_duration=%g" % s["tpad"])
        for (txt, size, t0, t1, yf) in s["text"]:
            ch.append(drawtext(txt, size, t0, t1, yf))
        if s["flash"]:
            typ, d = s["flash"]
            ch.append("fade=t=in:st=0:d=%g:color=%s" % (d, typ))
        if s.get("fin"):
            ch.append(s["fin"])
        ch.append("setsar=1,format=yuv420p")
        parts.append(",".join(ch) + f"[v{idx}]")

        ac = [f"[0:a]atrim=start={s['i']}:end={s['o']},asetpts=PTS-STARTPTS"]
        sp = s["sp"]
        ac.append("atempo=%g" % sp if sp >= 0.5 else "atempo=0.5,atempo=%g" % (sp / 0.5))
        if s["tpad"]:
            ac.append("apad=pad_dur=%g" % s["tpad"])
        ac.append("volume=%g" % s["vol"])
        ac.append("aresample=48000,aformat=sample_fmts=fltp:channel_layouts=stereo")
        parts.append(",".join(ac) + f"[a{idx}]")

    n = len(SHOTS)
    vp = "".join(f"[v{i}][a{i}]" for i in range(n))
    fc = ";".join(parts) + (
        f";{vp}concat=n={n}:v=1:a=1[vc][ac]"
        "; [vc]format=yuv420p[vout]"
        "; [ac]volume=1.0[ga]"
        "; [1:a]volume=0.58,afade=t=out:st=%.1f:d=0.7[bg]" % (TOTAL - 0.7)
        + "; [2:a]volume=0.80[fx]"
        "; [ga][bg][fx]amix=inputs=3:duration=first:normalize=0,alimiter=limit=0.84:level=false[aout]")

    cmd = [FF, "-y", "-i", SRC, "-i", BGM_WAV, "-i", SFX_WAV,
           "-filter_complex", fc, "-map", "[vout]", "-map", "[aout]",
           "-r", "60", "-c:v", "libx264", "-preset", "slow", "-crf", "14",
           "-profile:v", "high", "-level", "4.2", "-pix_fmt", "yuv420p",
           "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
           "-movflags", "+faststart", OUT]
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode:
        print((r.stderr or "")[-4000:])
        return 1
    print("成品:", OUT, "%.1f MB" % (os.path.getsize(OUT) / 1048576))
    pr = subprocess.run([FP, "-v", "error", "-count_packets", "-show_entries",
                         "stream=codec_type,width,height,r_frame_rate,nb_read_packets,bit_rate:format=duration,bit_rate",
                         "-of", "default=nw=1", OUT], capture_output=True, text=True)
    print(pr.stdout)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
