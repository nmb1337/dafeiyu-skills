# 本机 GPT-SoVITS：跑起来 + 调它合成语音

## 启动

```bash
cd C:\Users\32672\Apps\GPT-SoVITS
.venv/Scripts/python.exe api_v2.py -a 127.0.0.1 -p 9880 -c GPT_SoVITS/configs/tts_infer.yaml
```

- 后台跑或 pm2 都行；启动加载模型约 25 秒，就绪标志是 `Uvicorn running on http://127.0.0.1:9880`。
- 想换模型版本改 `GPT_SoVITS/configs/tts_infer.yaml` 的 `custom:` 段（device/is_half/权重路径）。本机 2060 6G 用 `is_half: true` + v2 权重。

## 合成（POST /tts，返回**原始 wav 字节**，不是 JSON）

```json
{
  "text": "要念的中文",
  "text_lang": "zh",
  "ref_audio_path": "C:\\...\\refs\\voice_ref.wav",
  "prompt_text": "参考音里逐字对应的内容",
  "prompt_lang": "zh",
  "text_split_method": "cut5",
  "batch_size": 1,
  "media_type": "wav",
  "streaming_mode": false
}
```

调用：`curl -s --noproxy '*' -X POST http://127.0.0.1:9880/tts -H "Content-Type: application/json" --data-binary @payload.json -o out.wav`

## 参考音（决定音色）

- 3–10 秒、单人、干净；`ffmpeg -i in.mp3 -t 9 -ar 32000 -ac 1 refs/x.wav` 即可。
- **想固定一个「自己的」音色**：先用系统 TTS（`text_to_speech` 工具）生成一段目标音色的语音，再拿它当参考音克隆 —— 一次得到可复用的音色。
- `prompt_text` 必须与参考音内容**逐字**一致，否则韵律会漂。

## 验证产物（不能只看 HTTP 200）

```bash
ffprobe -v error -show_entries format=duration -of default=nw=1 out.wav
ffmpeg -i out.wav -af volumedetect -f null -   # 看 mean_volume/max_volume，确认不是静音
```

## 排错顺序

1. 400 的响应体就是错误详情：直接 `cat out.wav`（里面是 JSON，不是音频）。
2. `TorchCodec is required...` → torch/torchaudio 太新，降到仓库「已测试环境」版本。
3. `Resource 'cmudict' not found` → nltk_data.zip 的解压目标是 **venv 前缀**，不是仓库目录：`Expand-Archive -Path nltk_data.zip -DestinationPath <repo>\.venv`（官方 install.ps1 就是 `(python -c "import sys;print(sys.prefix)")` 当目标），解压后 `<repo>\.venv\nltk_data\corpora\cmudict` 必须存在。

## 用完就停 / 随时拉起（用户很在意电费）

- 常驻吃约 **3.7 GB 内存 + 2.9 GB 显存**；不做配音时停掉：按命令行匹配杀掉 `api_v2.py` 的 python 进程，再确认 `9880` 已释放，然后**把释放出来的内存/显存报给用户**。
- 单实例启动器 `start-api.bat`（纯 ASCII）：`netstat -ano | findstr ":9880 " | findstr LISTENING` 已在听就直接退出；否则 `start "GPT-SoVITS API" /min cmd /c ".venv\Scripts\python.exe api_v2.py -a 127.0.0.1 -p 9880 -c GPT_SoVITS\configs\tts_infer.yaml >> api.log 2>&1"`。
- 交付音频给用户听（我听不了，只能验波形）：
  `ffmpeg -y -i out.wav -af "loudnorm=I=-16:TP=-1.5:LRA=11" -codec:a libmp3lame -b:a 128k out.mp3`
  —— `loudnorm` 是**滤镜**，必须写成 `-af "loudnorm=..."`，写成裸选项 `-loudnorm=I=-16:TP=-1.5` 会报 `Unrecognized option`。
- 音色好不好必须让用户听：把 mp3 作为 MEDIA 发给他，并说明这是用哪段参考音克隆的。

## 性能参考

2060 6G（is_half）：16 秒中文音频约 10 秒生成（含首次预热）；显存占用约 2.9G。
