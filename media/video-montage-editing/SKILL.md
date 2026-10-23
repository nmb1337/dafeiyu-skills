---
name: video-montage-editing
description: "Use when 剪游戏高光/击杀集锦/卡点 montage，或把一段素材剪成宣传片风格短片。"
version: 1.0.0
author: Hermes Agent (大肥鱼)
license: MIT
platforms: [windows]
metadata:
  hermes:
    tags: [ffmpeg, montage, 剪辑, 卡点, 抖音, game-highlight]
---

# 视频高光剪辑（卡点 montage · ffmpeg 流水线）

## When to Use

- 主人说「把这个视频剪成超帅的游戏剪辑 / 高光集锦 / 抖音那种击杀剪辑 / 卡点视频」。
- 已有成片要返工：换 BGM（指定高潮段）、加转场、改节奏、加字幕。
- 不适用于：大肥鱼账号的口播/图文视频（那是 `douyin-short-video`）。

## 交付标准（主人定的硬线，别谈判）

- **60fps 满帧**：输出 `-r 60`；验收用 `ffprobe -count_packets`，`nb_read_packets` 必须 == duration×60，少一帧都算翻车。
- **画质**：`libx264 -preset slow -crf 14 -pix_fmt yuv420p`，保持素材**原生分辨率不裁切**；成品码率通常应高于源片（重编码反而更厚才是对的）。
- **声音**：峰值压到 ≤ -0.7dB；慢镜段游戏原声压到 0.45–0.55（抖音教程原话：慢放段原声会杂），BGM 0.55–0.62。
- **交付**：拷到 `C:\Users\32672\Videos\`（scratch 目录会过期清理），用 `ffplay -autoexit` 在他电脑上当场播一遍，消息里附 `MEDIA:` 绝对路径。
- **「不像样子」= 没按平台风格做**：先去搜对应平台（抖音/B站）的剪辑教程，逐条复刻教程里点名的技术手法（闪白/光流补帧/振动/RGB抖动/黑白定格/大字幕），不要只调个色就交片。

## 流程（按顺序，每步都有验收）

### 1. 侦察素材（先看清再动刀）

```bash
FF=~+/tools/ffmpeg-*/bin   # 本机 $HERMES_HOME/tools/ffmpeg-9.0.1-win32-x64/bin
"$FF/ffprobe.exe" -v error -show_entries format=duration,size:stream=width,height,r_frame_rate,avg_frame_rate,nb_frames -of default=nw=1 "C:/path/in.mp4"
# 1fps 拼图看全景：
"$FF/ffmpeg.exe" -y -i "C:/path/in.mp4" -vf "fps=1,scale=426:320,tile=3x3" -frames:v 1 sheet.jpg
# 动作瞬间用 10fps 细拼图（先 -ss/-to 卡窗口）：
"$FF/ffmpeg.exe" -y -ss 4.4 -to 6.8 -i "C:/path/in.mp4" -vf "fps=10,scale=320:240,tile=6x4" -frames:v 1 sheet_kill.jpg
```

用 vision 读拼图：认出游戏/动作/击杀帧的精确秒数。**击杀帧、收尾帧的秒数是后面全部时间轴的地基，必须靠图确认，不能猜。**

### 2. 侦察音乐（「高潮部分」就是能量最高的窗口）

用唱歌 venv（有 librosa+numpy）：`C:\Users\32672\Apps\dafeiyu-sing\.venv\Scripts\python.exe`，曲库在 `Apps\dafeiyu-sing\songs\`。

```python
import librosa, numpy as np
y, sr = librosa.load(P, sr=22050, mono=True)
tempo, beats = librosa.beat.beat_track(y=y, sr=sr, units="time")
hop = int(sr*0.25); rms = np.array([np.sqrt(np.mean(y[i:i+hop]**2)) for i in range(0,len(y)-hop,hop)])
win = 64  # 16s
best = max(((rms[i:i+win].mean(), i) for i in range(len(rms)-win)))
print("最响16s窗口", best[1]*0.25, "~", (best[1]+win)*0.25, "BPM", float(np.ravel(tempo)[0]))
```

- 全曲最响的连续 16–18s 窗口 ≈ 最后一遍副歌 = 用户说的「高潮」。从**节拍边界**（beats 里最接近窗口起点的那个）切段，别从任意毫秒切。
- 记下 BPM 和拍长（如 117.5BPM → 0.5106s/拍）；后面所有剪辑点都要落在拍网格上。

### 3. 设计时间轴（把「钱镜头」钉在重拍上）

- 先定结构：慢镜开场 → 提速推进 → **击杀/高光切入落在副歌某小节重拍**（4 拍 = 1 小节；目标是 4.09/8.17 这类小节起点，误差 0）→ 慢放展示 → 收尾定格 + **最后 1 秒转场**。
- 逐镜头写清 `src_in / src_out / speed`，用脚本**求和验证**关键镜头起始时刻 == 目标节拍时刻（打印断言，不靠心算）。
- 素材很短（<10s）时用「同段素材多次使用」：刚镜击杀回放、慢镜走位，靠不同速度和推镜避免重复感。
- 抖音 CS 击杀片常用配方（实测有效）：击杀段 0.42x 光流慢镜 + 白闪切入 + RGB 分离抖动 + 低频爆点；结尾黑白高对比定格 + 大字 GG；**最后 1 秒 = 白闪切 + 淡出黑场**。

### 4. 构建 ffmpeg 滤镜图

直接用模板 `templates/montage_build.py`（改 SHOTS 表即可，含音效床/混音/质检）。每个镜头的标准链条：

```
trim → setpts=(PTS-STARTPTS)/speed → minterpolate(fps=60) [慢镜] → fps=60
→ zoompan(推拉) → crop+scale(手持抖动) → eq/vignette(调色) → rgbashift(RGB分离)
→ tpad(定格) → drawtext(字幕) → fade(白闪/淡黑) → setsar=1,format=yuv420p
```

音频：`atrim → asetpts → atempo链 → apad(定格段) → volume → aresample/aformat`，与原视频一起 `concat=v=1:a=1`，再与 BGM、音效床三路 `amix=inputs=3:normalize=0` → `alimiter`。

### 5. 验收（不验收等于没做）

```bash
# 帧数必须精确 = 时长×60
"$FF/ffprobe.exe" -v error -count_packets -select_streams v:0 -show_entries stream=nb_read_packets,r_frame_rate,duration -of default=nw=1 out.mp4
# 电平：峰值应为负值（约 -0.7dB），mean 约 -11~-14dB
"$FF/ffmpeg.exe" -i out.mp4 -af volumedetect -f null - 2>&1 | grep -aE "mean_volume|max_volume"
# 成品 1fps 拼图，用 vision 过一遍：黑帧/坏帧/字幕时间/转场位置
```

**把成品拼图交给 vision 检查**（尤其：字幕有没有出现、结尾黑白定格/白闪/黑场顺序对不对）；**1fps 拼图会漏掉不到 1 秒的转场**——结尾单独抽一段 4fps 拼图复核顺序（`-ss <总长-3.5> -vf "fps=4,scale=320:240,tile=7x2"`），确认「定格→白闪→淡黑」各就各位；发现坏帧就修脚本重渲，别带病交付。

### 6. 交付

复制到 `C:\Users\32672\Videos\` → `ffplay -autoexit -loglevel quiet -volume 90 -x 960 -y 720 "C:/..."` 当场播 → 消息里 `MEDIA:` + 画质验收数据 + 剪辑设计说明（结构表）。

## 坑（每条都咬过人）

- **`crop` 的 w/h 不能随 t 变**（输出尺寸必须恒定），只有 x/y 能动 → 动画推拉镜用 `zoompan=z='1+0.088*on/60'`（`on` = 输出帧序号），crop 只能做静态推镜或抖动位移。
- **`fade=t=in:st=X`（X>0）语义不可靠**：想在中途闪白，别用中段 fade-in；**把镜头拆成两段**，让新镜头从 st=0 淡入（白闪 → 淡黑收尾就是这么实现的）。
- **drawtext 必须排在 fade 之前**：否则淡出黑场时字幕还亮着挂在黑底上。`enable='between(t\,a\,b)'` 逗号要转义；中文字体 `fontfile='C\:/Windows/Fonts/msyhbd.ttc'`（路径里的冒号也要转义）。
- **`alimiter` 默认 `level=true` 会把音量自动抬到限制线**（实测峰值打到 0.0dB）→ 永远写 `alimiter=limit=0.84:level=false`。
- **`atempo` 单次只支持 0.5–2.0**：0.42x 要链式 `atempo=0.5,atempo=0.84`。
- **WAV（pcm_s16le）不接受 `-sample_fmt fltp`**：提取 BGM 时别带这个参数。
- **给 ffmpeg 传路径一律 `C:/...` 原生格式**，MSYS 的 `/c/...` 会被当普通字符串拒绝。
- **`minterpolate` 要放在 `setpts` 之后、`zoompan` 之前**，且只给慢镜镜头加（正常速度镜头用 `fps=60` 即可），否则渲染时间爆炸还伤画质。
- **剪映专业版本机是 11.6**：草稿生成可用（见 `douyin-short-video` 技能），但**自动导出在 11.6 走不通**（QML 界面 UIA 全空）→ 需要保证出片时走 ffmpeg 流水线；剪映工程只作为「他可自己打开微调」的附加物，导出请他手动点。
- **剪映 wrapper 的文档 ≠ 实现**：`jianying-editor-skill/docs/api.md` 写了 `add_effect_simple / add_transition_simple`，但 `scripts/jy_wrapper.py` 里并没有这两个方法（实际可用的是 `add_clip / add_media_safe / add_text_simple / save` 等，特效散在各 Mixin 里）。写脚本前先 `grep -nE 'def (add_|save)' scripts/jy_wrapper.py` 确认签名，别照文档盲写一段 AttributeError 给主人看。

## References
- `templates/montage_build.py` — 可改 SHOTS 表直接跑的构建脚本（含音效床、BGM 抽取、质检输出）。
- `references/ffmpeg-montage-recipes.md` — 滤镜/混音/音乐分析的具体参数与验证命令。
