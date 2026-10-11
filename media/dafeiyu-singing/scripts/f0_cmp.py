"""量一下「音高」：语音回复 vs 唱歌输出 —— 如果不在一个音区，听感就会像两个人。"""
import glob, os, numpy as np, librosa

ROOT = r"C:\Users\32672\Apps\dafeiyu-sing"
items = {
    "语音参考(GPT-SoVITS)": r"C:\Users\32672\Apps\GPT-SoVITS\refs\dafeiyu_voice.wav",
    "唱歌参考(我切的20s)": os.path.join(ROOT, "refs", "dafeiyu_ref20s.wav"),
}
voice = sorted(glob.glob(r"C:\Users\32672\AppData\Local\hermes\cache\qq-voice\*.mp3"),
               key=os.path.getsize, reverse=True)[0]
items["语音输出(TTS)"] = voice
convs = sorted(glob.glob(os.path.join(ROOT, "work", "conv", "*", "vc_vocals_*.wav")), key=os.path.getmtime, reverse=True)
items["唱歌输出(人声)"] = convs[0]

def f0_stats(tag, path):
    y, sr = librosa.load(path, sr=16000, mono=True)
    y, _ = librosa.effects.trim(y, top_db=30)
    if len(y) < sr:
        print(f"  {tag}: 太短/几乎没声"); return
    f0 = librosa.yin(y, fmin=60, fmax=600, sr=sr)
    f0 = f0[np.isfinite(f0)]
    f0 = f0[(f0 > 60) & (f0 < 600)]
    if f0.size == 0:
        print(f"  {tag}: 测不到音高"); return
    print(f"  {tag:22} 中位音高 {np.median(f0):6.1f} Hz | 5%~95% {np.percentile(f0,5):5.1f}~{np.percentile(f0,95):5.1f} Hz")
    print(f"  {'':22} 折算 ≈ 音名 {librosa.hz_to_note(float(np.median(f0)))}")

print("== 音高对比 ==")
for k, v in items.items():
    f0_stats(k, v)
