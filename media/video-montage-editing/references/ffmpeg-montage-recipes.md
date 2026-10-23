# ffmpeg montage 配方与参数核对表

## 每镜头滤镜链（顺序不能乱）

```
[0:v]trim=start=I:end=O,setpts=(PTS-STARTPTS)/SP
  → minterpolate=fps=60:mi_mode=mci:mc_mode=aobmc:vsbmc=1   # 仅慢镜(SP<0.9)，光流补帧
  → fps=60                                                    # 正常速度镜头
  → zoompan=z='EXPR':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=1:s=1280x960:fps=60
  → crop=1200:900:x='(in_w-1200)/2+12*sin(80*t)*exp(-5*t)':y='(in_h-900)/2+10*cos(95*t)*exp(-5*t)'
    → scale=1280:960:flags=lanczos                        # 只有手持抖动镜头要这两行
  → eq=contrast=...:saturation=...[,...] / vignette=PI/4 / hue=s=0
  → rgbashift=rh=3:bh=-3:gv=1
  → tpad=stop_mode=clone:stop_duration=X
  → drawtext=...
  → fade=t=in:st=0:d=0.12:color=white
  → 自定义 fin（如 fade=t=out:st=0.25:d=0.75:color=black）
  → setsar=1,format=yuv420p
```

## zoompan 的 z 表达式（推拉镜）

- 缓推：`1+0.035*on/60`（3 秒约 1.10x）
- 强推（击杀）：`1+0.088*on/60`
- 推回：`1.14-0.06*on/60`
- 定格微推：`1+0.006*on/60`
- `on` = 输出帧序号（60fps 下 on/60 = 秒）。**不要用 `crop` 的 w/h 做动画——crop 输出尺寸必须恒定，w/h 里没有 t。**

## 声音图（三路混音）

```
每镜头：[0:a]atrim=I:O,asetpts=PTS-STARTPTS,atempo链,apad(定格),volume=每镜头音量,
aresample=48000,aformat=sample_fmts=fltp:channel_layouts=stereo
concat=v=1:a=1[vc][ac]
[ac] volume=1.0 [ga]
[1:a] volume=0.58, afade=t=out:st=TOTAL-0.7:d=0.7 [bg]
[2:a] volume=0.80 [fx]
[ga][bg][fx] amix=inputs=3:duration=first:normalize=0, alimiter=limit=0.84:level=false [aout]
```

- `amix` 默认按输入数自动衰减 → 必须 `normalize=0`，不然整体音量莫名其妙变小。
- `alimiter` 的 `level=false` 不可省：默认会把整体拉高到限制线（实测峰值 0.0dB，会削波）。
- 每镜头游戏音量：慢镜 0.45–0.55、正常 0.85、定格 0（`apad` 补静音对齐时长）。

## 音乐分析（找「高潮」+ 节拍网格）

```python
import librosa, numpy as np
y, sr = librosa.load(P, sr=22050, mono=True)
tempo, beats = librosa.beat.beat_track(y=y, sr=sr, units="time")
hop = int(sr*0.25)
rms = np.array([np.sqrt(np.mean(y[i:i+hop]**2)) for i in range(0, len(y)-hop, hop)])
win = 64  # 64*0.25 = 16s
best = max((rms[i:i+win].mean(), i) for i in range(len(rms)-win))
# best[1]*0.25 => 高潮起点（对齐到最近的 beat）
oe = librosa.onset.onset_strength(y=y, sr=sr)
onsets = librosa.onset.onset_detect(onset_envelope=oe, sr=sr, units="time")
```

- 副歌起点从 `beats` 里挑，不从任意毫秒切；拍长 = 60/BPM。
- 剪辑点对齐公式：`小节起点 = 段落起点 + n×4×拍长`；脚本里把每个镜头的输出时长加起来，断言钱镜头起始 == 目标节拍。

## 质检命令

```bash
# 帧数完整性（nb_read_packets == duration×60）
ffprobe -v error -count_packets -select_streams v:0 \
  -show_entries stream=nb_read_packets,r_frame_rate,duration -of default=nw=1 out.mp4
# 电平
ffmpeg -i out.mp4 -af volumedetect -f null - 2>&1 | grep -aE "mean_volume|max_volume"
# 成品拼图（vision 复核字幕/转场/坏帧）
ffmpeg -y -i out.mp4 -vf "fps=1,scale=320:240,tile=4x4" -frames:v 1 out_sheet.jpg
```

## 抖音 CS 击杀剪辑风格清单（本轮复盘）

- 击杀切入落在副歌小节重拍上（闪白 0.10–0.12s + 低频爆点）。
- 击杀段 0.42x 光流慢镜，game 原声压低（0.5），保留枪声层次。
- RGB 分离（`rgbashift`）+ 前 0.3s 手持抖动（crop 位移衰减）强调命中。
- 收刀/走位用 0.55–0.8x 慢镜 + 暗角。
- 收尾：黑白高对比定格（`hue=s=0,eq=contrast=1.22:brightness=-0.06`）+ 大字「G G」+ 小水印。
- **最后 1 秒 = 新片段从白闪开始 + 淡出黑场**（拆两段实现，不要用中段 fade-in）。
- 大字幕：微软雅黑 Bold、白字黑边（borderw=5）、居中偏下。
