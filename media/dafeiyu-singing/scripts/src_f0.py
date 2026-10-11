import glob, numpy as np, librosa
SRC = glob.glob(r"C:\Users\32672\Apps\dafeiyu-sing\work\separated\htdemucs\*\vocals.wav")[0]
NEW = glob.glob(r"C:\Users\32672\Apps\dafeiyu-sing\work\conv_fixref\*.wav")[0]
OLD = glob.glob(r"C:\Users\32672\Apps\dafeiyu-sing\work\conv\*\vc_vocals_*.wav")[0]
def med(p, off=60, dur=60):
    y, sr = librosa.load(p, sr=16000, mono=True, offset=off, duration=dur)
    y, _ = librosa.effects.trim(y, top_db=30)
    f0 = librosa.yin(y, fmin=70, fmax=600, sr=sr)
    f0 = f0[np.isfinite(f0)]; f0 = f0[(f0>70)&(f0<600)]
    return float(np.median(f0))
a, b, c = med(SRC), med(NEW), med(OLD)
print(f"  原唱人声(分离出来的干声) 中位 {a:6.1f} Hz ≈ {librosa.hz_to_note(a)}")
print(f"  旧版输出(20s参考)        中位 {c:6.1f} Hz ≈ {librosa.hz_to_note(c)}")
print(f"  新版输出(同说话参考)      中位 {b:6.1f} Hz ≈ {librosa.hz_to_note(b)}")
print(f"  新版相对原唱: {12*np.log2(b/a):+.2f} 个半音；旧版相对原唱: {12*np.log2(c/a):+.2f} 个半音")
