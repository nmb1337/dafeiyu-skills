#!/usr/bin/env python3
"""对比「语音回复的嗓」和「唱歌的嗓」到底差在哪 —— 用说话人嵌入算相似度，别靠耳朵猜。

比四个东西：
  A 语音(TTS)参考音      C:\\...\\GPT-SoVITS\\refs\\dafeiyu_voice.wav
  B 唱歌(SVC)参考音      \\refs\\dafeiyu_ref20s.wav
  C 语音输出样本         一段缓存的 QQ 语音
  D 唱歌输出人声         work/conv/<歌>/vc_vocals_*.wav
"""
from __future__ import annotations

import glob
import os
import sys

ROOT = r"C:\Users\32672\Apps\dafeiyu-sing"
A = r"C:\Users\32672\Apps\GPT-SoVITS\refs\dafeiyu_voice.wav"
B = os.path.join(ROOT, "refs", "dafeiyu_ref20s.wav")
FF = r"C:\Users\32672\AppData\Local\hermes\tools\ffmpeg-9.0.1-win32-x64\bin\ffmpeg.exe"


def to_wav16k(src: str, tag: str, ss: int = 0) -> str:
    import subprocess
    dst = os.path.join(ROOT, "work", f"_cmp_{tag}.wav")
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    cmd = [FF, "-y", "-loglevel", "error"]
    if ss:
        cmd += ["-ss", str(ss)]
    cmd += ["-t", "25", "-i", src, "-ac", "1", "-ar", "16000", dst]
    subprocess.run(cmd, check=False)
    return dst if os.path.isfile(dst) else ""


def sim(a, b) -> float:
    import numpy as np
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-9))


def main() -> int:
    from resemblyzer import VoiceEncoder, preprocess_wav
    enc = VoiceEncoder("cpu")

    def emb(path: str):
        if not path or not os.path.isfile(path):
            print("  缺文件:", path)
            return None
        wav = preprocess_wav(path)
        if len(wav) < 16000:
            print("  太短:", path)
            return None
        return enc.embed_utterance(wav)

    voiced = sorted(glob.glob(os.path.join(r"C:\Users\32672\AppData\Local\hermes\cache\qq-voice", "*.mp3")),
                    key=os.path.getsize, reverse=True)[:1]
    C = to_wav16k(voiced[0], "tts") if voiced else ""
    convs = sorted(glob.glob(os.path.join(ROOT, "work", "conv", "*", "vc_vocals_*.wav")),
                   key=os.path.getmtime, reverse=True)
    D = convs[0] if convs else ""

    print("  A 语音参考:", A)
    print("  B 唱歌参考:", B)
    print("  C 语音输出:", os.path.basename(voiced[0]) if voiced else "-")
    print("  D 唱歌输出:", os.path.basename(D) if D else "-")

    e = {"A": emb(to_wav16k(A, "A") or A), "B": emb(B),
         "C": emb(C), "D": emb(to_wav16k(D, "D", ss=70) if D else "")}
    for k, v in e.items():
        print(f"  {k} 嵌入: {'ok' if v is not None else '失败'}")
    pairs = [("A", "B", "两个参考音像不像（该像）"),
             ("C", "A", "语音输出 vs 语音参考（该像）"),
             ("D", "B", "唱歌输出 vs 唱歌参考（该像）"),
             ("C", "D", "两种输出的嗓像不像（关键！）"),
             ("D", "A", "唱歌输出 vs 语音参考"),
             ("C", "B", "语音输出 vs 唱歌参考")]
    print("\n  == 相似度（1.0 最高）==")
    for x, y, why in pairs:
        if e.get(x) is not None and e.get(y) is not None:
            print(f"   {x}-{y}: {sim(e[x], e[y]):.3f}   {why}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
