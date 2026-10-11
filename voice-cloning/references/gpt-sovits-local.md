# 本机 GPT-SoVITS 克隆实操（Windows）

路径按本机约定写；换机器时把 `$HERMES_HOME` / `C:\Users\<user>` 换掉即可。

- GPT-SoVITS 仓库：`C:\Users\32672\Apps\GPT-SoVITS`（自带 `faster_whisper` / `funasr` / `torchaudio` 的 venv：`.venv\Scripts\python.exe`）
- 推理服务：`.venv\Scripts\python.exe api_v2.py -a 127.0.0.1 -p 9880 -c GPT_SoVITS/configs/tts_infer.yaml`
- ffmpeg/ffprobe：`$HERMES_HOME\tools\ffmpeg-*\bin\`（不在 PATH，用绝对路径；给原生 exe 传路径要用 `C:/...` 形式，MSYS 的 `/c/...` 它不认）
- 辅助脚本（`$HERMES_HOME\scripts\`）：`asr_transcribe.py`（整段转写）、`asr_segments.py`（带时间戳，需标点模型，一般用不上）、`pick_ref_clips.py`（VAD 切窗口 + 逐段转写，输出 `candidates.json`）

## 1. 下载分享链接里的音频（抖音为例）

无 cookie 直下会被拒（`Fresh cookies are needed`）。先用浏览器工具打开视频页，再把 cookie 导成 Netscape 文件：

```python
# browser_exec
new_tab("https://www.douyin.com/video/<id>"); wait_for_load(); time.sleep(4)
ck = cdp('Network.getAllCookies')          # 含 httpOnly
# 逐条写成: domain \t TRUE/FALSE \t path \t TRUE/FALSE \t expires \t name \t value
```

```bash
uvx yt-dlp --ffmpeg-location "$FF" --cookies douyin_cookies.txt \
  --user-agent "Mozilla/5.0 (Windows NT 10.0; Win64; x64) ... Chrome/131.0.0.0 Safari/537.36" \
  -f bestaudio -x --audio-format wav -o "ref_%(id)s.%(ext)s" "https://www.douyin.com/video/<id>"
```

短链（`v.douyin.com/xxx`）直接交给 yt-dlp，它会自己跟跳转。

## 2. 先验素材：这段音频干净吗（带 BGM 的短视频必做）

短视频素材通常是**全程铺伴奏 + 响度压到 0 dB 峰值**，靠耳朵或靠「挑安静段」都救不回来。判断只看数字：

```bash
# 找一段“应该是停顿”的 8-10 秒，量它的音量：与说话段同量级 = 全程有伴奏
"$FF/ffmpeg" -hide_banner -ss 40 -t 9 -i ref_<id>.wav -af volumedetect -f null -   # mean_volume ≈ -13 dB?
# 抽一张频谱图（整图规律竖条纹 = 鼓点/BGM；上方一片均匀雾气 = 压缩出的底噪）
"$FF/ffmpeg" -y -ss 45 -t 15 -i ref_<id>.wav -lavfi "showspectrumpic=s=1280x420:legend=1" spec_source.png
```

然后**真的把人声分离出来**（不是挑段落）：

```bash
# 装到 GPT-SoVITS 自己的 venv（torch 已有，省 2.5G 下载）；装包时清掉代理变量
uv pip install --python "C:/Users/32672/Apps/GPT-SoVITS/.venv/Scripts/python.exe" demucs
cd C:/Users/32672/Apps/GPT-SoVITS
./.venv/Scripts/python.exe -m demucs --two-stems=vocals -n htdemucs -d cuda \
  -o "$D/separated" "$D/ref_<id>.wav"          # 6G 卡可跑；失败就换 -d cpu
# 产物：separated/htdemucs/ref_<id>/{vocals.wav,no_vocals.wav}
```

分离前后用同一段“安静区”对账，才叫证据（本次实测：原音频 -13.2 dB → 人声轨 -14.4 / 伴奏轨 -24.5）。

## 3. 切参考片段 + 逐段转写

> 关键：识别器吃的 **16k 单声道**是消耗品；**参考必须从原始音频（或 `vocals.wav`）切 32k 单声道**，从 16k 那份切会把高频砍掉（成品发闷发毛）。

```bash
cd C:/Users/32672/Apps/GPT-SoVITS
export PATH="$PATH:/c/Users/32672/AppData/Local/hermes/tools/uv-0.12.3-win32-x64"
# 整段转写（拿全局文本，方便一眼看出素材讲什么）
./.venv/Scripts/python.exe tools/asr/funasr_asr.py -i <wav目录> -o <输出目录> -l zh
# 切候选片段（VAD→合并~10s→逐段 ASR），输出 candidates.json
#   第一个参数给**干净的那条轨**：分离过就给 vocals.wav，没分离过就给原始 44.1k，别给 16k
./.venv/Scripts/python.exe "$HERMES_HOME/scripts/pick_ref_clips.py" "$D/separated/htdemucs/ref_<id>/vocals.wav" "$D/clips" 6
# 按 candidates.json 里的 start/end 从同一条轨重切参考（32k 单声道 + 轻降噪）
"$FF/ffmpeg" -y -ss <start> -to <end> -i <轨> -ac 1 -ar 32000 \
  -af "highpass=f=70,afftdn=nr=10:nf=-35" ref1.wav
```

`candidates.json` 每项：`{clip, start, end, dur, prompt_text}` —— `clip` 给克隆当参考、`prompt_text` 当参考原文（同一时间点重切时原文不变，可继续用）。

## 4. 调 `/tts` 出成品

服务起来后 POST `http://127.0.0.1:9880/tts`（缺参数会返回 400 + `xxx is required`，可当健康检查）：

```json
{
  "text": "<要合成的演示台词>", "text_lang": "zh",
  "ref_audio_path": "<候选 clip 的绝对路径>", "prompt_text": "<该 clip 的原文>", "prompt_lang": "zh",
  "text_split_method": "cut5", "batch_size": 1, "media_type": "wav",
  "streaming_mode": false, "top_k": 15, "top_p": 1, "temperature": 1, "speed_factor": 1.0
}
```

经验速度：8–10 秒参考、~30 字台词，在 6G 笔记本卡上 **6–13 秒**出结果。

## 5. 归一化 + 本地播放给用户听

```bash
"$FF/ffmpeg" -y -i out.wav -af loudnorm=I=-16:TP=-1.5 -c:a libmp3lame -b:a 128k out.mp3
# 播放（无窗口、不抢焦点）
"$FF/ffmpeg" -y -i out.mp3 -ac 1 -ar 44100 play.wav
```

```powershell
$p = New-Object Media.SoundPlayer 'C:\path\play_v1.wav'; $p.PlaySync()
```

多版本就按 v1→v2→v3 顺序播，每段之间停 1–1.5 秒，消息里写清顺序和各自参考的原话。

## 6. 微调（可选，素材够了再做）

用 `.list` 标注（`音频路径|说话人|语言|文本`，funasr 转写脚本直接产出这个格式），再走仓库的 `s1_train.py` / `s2_train.py`。素材目标 10–30 分钟单人干净语音；只有一条短视频时先零样本，并告知上限。
