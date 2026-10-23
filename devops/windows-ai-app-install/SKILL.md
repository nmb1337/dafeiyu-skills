---
name: windows-ai-app-install
description: "Use when installing local AI apps on this Windows box."
version: 1.0.0
author: Hermes Agent (大肥鱼)
license: MIT
platforms: [windows]
metadata:
  hermes:
    tags: [windows, install, uv, gpt-sovits, uptime-kuma, mem0, browser-use, venv]
---

# 本机装第三方 AI 应用（Windows）

## When to Use

- 要在本机装/修第三方 AI 应用：TTS（GPT-SoVITS）、视频、记忆（mem0）、监控（Uptime Kuma）、浏览器 agent（browser-use）等
- pip/uv 安装报编译错误、报 torchcodec、服务起不来需要排查时

## 通用规矩（踩过坑的）

- **本机没有 Docker、没有 conda、没有 C++ 编译器（MSVC）**。用 `uv` 建环境：`uv venv --python 3.11|3.12 <dir>/.venv` + `uv pip install --python <dir>/.venv/Scripts/python.exe ...`。
- **任何要现场编译的包都会失败**（报 `Microsoft Visual C++ 14.0 or greater is required`）：如 `jieba-fast`、`pyopenjtalk`、`opencc --no-binary`。三条绕法：①找纯 Python 替代 ②在 site-packages 里放兼容垫片 ③直接跳过可选包。真需要编译再装 VS Build Tools（几个 G）。
- **本机 shell 带代理 `HTTP(S)_PROXY=127.0.0.1:7890`**：探测本地服务必须 `curl --noproxy '*'`，否则 502。国内源（ModelScope）也用 `--noproxy '*'` 直连更快。
- 安装目录统一放 `C:\Users\32672\Apps\<name>`；装完自己测通再报。
- Python 版本别追新：很多模型仓库只测到 3.10–3.12，用 uv 装对应版本。
- 长驻服务要**掉线自起 + 开机自启**：pm2 只管进程内重启（要 `pm2 save`），开机自启另加启动项/计划任务。VBS 启动器**不要写中文**：WSH 按 ANSI 读 .vbs，某些中文字节会被当成转义，报 `未结束的字符串常量`；拼引号用 `Chr(34)`，别手写四引号。
- **VBS 里不要拼命令行字符串** —— 把 `cmd /c "程序" 参数…` 整个塞进 `sh.Run` 的字符串里，cmd 的引号消解会把参数吃坏（实测 `-c GPT_SoVITS/configs/tts_infer.yaml` 变成 `'onfigs' 不是内部或外部命令`，而重定向的日志里**一丝痕迹都没有**，VBS 还回你一句「已启动」，极难查）。固定套路：命令行写在**同名 `.cmd`** 里，VBS 只负责隐藏调用它 —— `sh.Run q & "cmd.exe" & q & " /c " & q & <那个.cmd> & q, 0, False`。本机所有长驻服务都是 `.vbs` + `.cmd` 成对，照抄。
- **起监听端口的服务前先对一遍本机端口表**：同机另一个同名/同类服务的启动脚本常把端口**硬编码**，撞了不一定报错，而是静默把活发错地方。已占用的：`3001` NapCat OneBot WS、`3002` Uptime Kuma、`6099` NapCat WebUI、`6185` AstrBot、`7890` 加速器 / `7899` 自建中转、`8188` MiniMax-H3 视频 ComfyUI、`8189` Z-Image 生图 ComfyUI、`8642` Hermes api_server、`8790` QQ 桥接、`8795` 告警转发、`9880` GPT-SoVITS TTS。先读已有那套的启动脚本（`grep -rn 8188 *.ps1`）再决定自己用哪个。
- **凭据规矩（先看这条）**：密码永远不由我输入、也不经过聊天。`browser_vault_save_login` 在微信/API 会话下不可用（`prompt_unavailable`）→ 让用户自己跑 `hermes vault add`（无参数、全交互：类型 login → 站点 → 用户名 → 密码 → 标签）或桌面版「设置 → 密码与登录」。用户名（identifier）我用 `fill_input` 自己填，**只有密码走保险箱**。
- **保险箱的站点必须和访问地址完全一致（含 scheme）**：桌面 GUI 常默认补 `https://`，而本地服务多是 `http://`；scheme 不一致时 `browser_vault_fill` 直接报 `origin_mismatch` 拒绝（凭据白存,又得让用户改一次）。给用户指令时把完整 origin 写全（`http://127.0.0.1:<port>`）。
- 首次向导要用户亲手建立管理员账号（密码规矩）：把页面在**用户自己的浏览器**里开出来（`chrome.exe "<url>"`）——我的浏览器实例用户看不到，让他对着自己的窗口操作。
- **需要用户点 UAC 的步骤：做快捷方式并置 RunAsUser 标志位。** 本会话里 `Start-Process -Verb RunAs` 拉不出授权框（没有 `consent.exe`、也没有提权进程落地），用户那边什么都没看到。可靠做法：正常建一个 `.lnk`，再把它的 LinkFlags `RunAsUser` 置位 —— 二进制偏移 **0x15** 或上 **0x20**（`RunAsUser = 0x2000`，小端即 0x15 字节的 bit5），然后让用户双击，UAC 就在**他自己的会话**里弹出来了。全程只需他点一下「是」，比我反复尝试提权省事得多。

## GPT-SoVITS（语音克隆，已跑通）

- Python **3.11**；依赖 `-r extra-req.txt --no-deps` + `-r requirements.txt`。
- **torch/torchaudio 必须 cu128**：本机显卡是 **RTX 5060 Ti 8G（Blackwell，sm_120）**——老的 CUDA 轮子在这个架构上根本跑不起来，任何新环境都装 `+cu128`。（新版 torchaudio(≥2.9) 还把音频 IO 外包给 `torchcodec`，而 **torchcodec 没有 Windows wheel**，会报 `TorchCodec is required for load_with_torchcodec`，所以 torchaudio 也钉 2.7.0。）
- **装 torch 别用 `--index-url https://download.pytorch.org/whl/cu128`**：本机 shell 挂着加速器中转时，那个源的大轮子会被 TLS 抛错（`cannot decrypt peer's message`，见 `local-proxy-resilience`）。用国内镜像 + 脱代理（实测能装完整套）：
  `env -u HTTP_PROXY -u HTTPS_PROXY -u ALL_PROXY uv pip install --python <dir>/.venv/Scripts/python.exe --find-links https://mirrors.aliyun.com/pytorch-wheels/cu128/ "torch==2.7.0+cu128" "torchaudio==2.7.0+cu128"`（阿里云/SJTU 都镜像 cu128，清华没有这个目录）。其余包继续走清华 pypi 镜像。
- **uv 是一口气落地**：装的过程中 venv 目录看着只有几百 KB（它是先下载+暂存，最后一次写入），别据此判定“没在装”或重复起第二个安装进程（两个 uv 抢同一个 venv 会互相覆盖）；看进度看 `uv.exe` 进程 CPU 和它的日志。
- 依赖里的 `jieba_fast`（C 扩展）编译不了 → 在 venv 的 `site-packages/jieba_fast/` 放垫片包：`__init__.py` 转出 `jieba`（含 `setLogLevel`/`cut`/`posseg`），`posseg.py` 转出 `jieba.posseg`，不改上游源码。同时从 requirements 里删掉 `jieba_fast`、`pyopenjtalk`（日语用不上）和 `--no-binary=opencc` 行，生成 `requirements.win.txt`。
- 把 `ffmpeg.exe` / `ffprobe.exe` 拷到仓库根（官方 Windows 要求）。
- 模型从 ModelScope 下：`https://www.modelscope.cn/models/XXXXRT/GPT-SoVITS-Pretrained/resolve/master/{pretrained_models.zip,G2PWModel.zip,nltk_data.zip}`，分别解压到 `GPT_SoVITS/`、`GPT_SoVITS/text/`。
- 起服务：`.venv/Scripts/python.exe api_v2.py -a 127.0.0.1 -p 9880 -c GPT_SoVITS/configs/tts_infer.yaml`（v2 模型 + cuda + is_half；RTX 5060 Ti 8G 上约占 3G 显存）。
- 调用：`POST http://127.0.0.1:9880/tts`，JSON 里 `text` / `text_lang=zh` / `ref_audio_path`（3–10s wav）/ `prompt_text`（参考音逐字稿）/ `prompt_lang=zh` / `text_split_method=cut5`。首个参考音可以先用 edge TTS 生成的 mp3 转 wav 当素材。
- **这个服务是「按需自启」的，别当常驻服务看**：桥接侧的 `scripts/tts-dafeiyu.py` 在 9880 不通时会自己拉起并等最多 240s（模型加载 30–60s），代价是**第一条语音很慢**。想先预热就脱离启动 `gateway-service/TTS.cmd`（由 `TTS.vbs` 隐藏调用）：先探端口、没起才拉，日志写 `$HERMES_HOME/logs/gpt-sovits.log`。冷启动实测约 **70s** 到 `Uvicorn running`。
- 合成一条的耗时参考：5060 Ti 8G 上约 14s（短句、模型已加载）。用 `python scripts/tts-dafeiyu.py <text_path> <out.mp3> mp3` 单跑一条验证时，**路径必须写成 `C:/...` 形式**（原生 python 不认 MSYS 的 `/c/...`，会报 No such file）。

## Uptime Kuma（监控面板，已跑通）

- 无 Docker → 走 Node 路线。**别浅克隆**：`npm run setup` 会 `git checkout 2.5.4`，浅克隆找不到 tag。改成 `git clone --depth 1 --branch 2.5.4`，然后 `npm ci --omit dev --no-audit` + `npm run download-dist`。
- 用 **pm2** 常驻（官方推荐，比手搓 VBS 稳）：`pm2 start <dir>\server\server.js --name uptime-kuma --cwd <dir>` + `pm2 save`。
- **默认端口 3001 和 NapCat 的 OneBot WS 撞车** → 启动前 `export UPTIME_KUMA_PORT=3002`。
- 首次向导：选项页的「下一步」按钮点不动（前端卡住），直接 `curl -X POST http://127.0.0.1:3002/setup-database -H 'Content-Type: application/json' -d '{"dbConfig":{"type":"sqlite"}}'` → 服务自动切到 /setup。
- **管理员账号必须用户本人建**（见上面「凭据规矩」）：把 `http://127.0.0.1:3002/setup` 在用户自己的 Chrome 里打开，他填用户名/密码/重复密码点「创建」；之后我登录加监控项靠保险箱那条凭据（站点必须是 `http://` 而不是 `https://`）。
- 加监控项：路由直达 `/add`，用原生 setter 填 `#name`/`#url` 再点**可见**的「保存」（Vue 表单操作见 `windows-local-app-setup` §5）；健康检查路径要选返回 200 的（Hermes api_server 用 `/health`，`/` 是 404，会让监控项一上线就判故障）。
- **告警推送（挂了 → 用户微信）**：面板通知 + 本机转发器 + `hermes send` 的完整做法，在技能 `windows-local-app-setup` 里那篇讲告警推送的参考文件中（本技能不复写，避免两份走形）。注意两点：通知在界面上点「保存」可能不落库（走 socket.io），需**停服后直接写 DB**；「测试」按钮的载荷没有 monitor/heartbeat，文案要单独判。

## browser-use（浏览器 agent，已跑通）

- `uv venv --python 3.12 .venv` + `uv pip install browser-use`；把官方技能装进 Hermes：`.venv/Scripts/browser-use.exe skill install --path "C:\Users\32672\AppData\Local\hermes\skills\browser-use"`。
- 它连的是**开了远程调试的 Chrome**。本机日常 Chrome 没开 → 起一个独立实例：`chrome.exe --remote-debugging-port=9222 --user-data-dir=<独立目录>`，再用 `BU_CDP_WS=ws://127.0.0.1:9222/devtools/browser/<id>` 调 `browser-use`。用完记得杀掉，省电。
- 冒烟测试：`BU_CDP_WS=... browser-use <<'PY'` + `print(page_info())`。

## mem0（记忆层，已跑通）

- `uv venv --python 3.12` + `uv pip install mem0ai sentence-transformers qdrant-client`。
- 配置：LLM 用 `provider=openai` + `openai_base_url=https://api.deepseek.com/v1`（DeepSeek key 从 `$HERMES_HOME/.env` 读，别打印）；embedding 用 `provider=huggingface`（本地 `BAAI/bge-small-zh-v1.5`，dims 512，设 `HF_ENDPOINT=https://hf-mirror.com`）；向量库 `provider=qdrant` + `path=<本地目录>`（全免费、不出本机）。
- **mem0 2.x API**：`search()` 里 `user_id` 不能再当顶层参数，要写 `m.search(q, filters={"user_id": "..."}, limit=n)`；`add(text, user_id=...)` 不变。
- 可选 `mem0ai[nlp]`（spaCy）开 BM25 混合检索，纯向量也够用。

## ComfyUI + Z-Image-Turbo（本地生图，已跑通）

**选型结论**：要「中文提示词 + 图生图」就上 **ComfyUI + Z-Image-Turbo**（阿里通义，6B，Apache-2.0）。Z-Image 是原生双语、中文文字渲染是招牌强项；SD1.5/SDXL 那套中文拉胯。官方 `Z-Image-Edit`（指令改图）**至今未发布**，所以「提示词改图」走经典图生图（参考图 + 提示词 + denoise）。

**安装（portable 路线，本机无编译器所以别走 pip 装 flash-attn 之类）**：
- 下载 `https://github.com/comfyanonymous/ComfyUI/releases/latest/download/ComfyUI_windows_portable_nvidia.7z`（~2GB，v0.39.0 自带 Python 3.13 + torch 2.14+cu130，正好喂 Blackwell sm_120）。
- **解压用 Windows 自带的 bsdtar**：`/c/Windows/System32/tar.exe -xf xxx.7z`（MSYS 那个 GNU tar 1.35 **不认 7z**）。解压 2GB 包要 7 分钟以上，前台跑会撞 420s 超时 → 用 background。tar 不打印进度，看目标目录 `du -sh` 判断。
- 目录：`C:\Users\32672\Apps\ComfyUI_windows_portable`。

**模型（8GB 显存选 NVFP4——Blackwell 原生 4bit，比 int8 小又快）**：
| 放哪 | 文件 | 大小 |
|---|---|---|
| `ComfyUI/models/diffusion_models/` | `z_image_turbo_nvfp4.safetensors` | 4.51 GB |
| `ComfyUI/models/text_encoders/` | `qwen_3_4b_fp4_mixed.safetensors` | 3.48 GB |
| `ComfyUI/models/vae/` | `ae.safetensors` | 0.34 GB |

源：`https://huggingface.co/Comfy-Org/z_image_turbo/resolve/main/split_files/<子目录>/<文件名>`（hf-mirror.com 同路径可用作备胎；本机实测 huggingface.co 直连更快）。全套 8.33GB，1024² 出图 ~9-27s。

**关键参数（少一个就不收敛）**：`CLIPLoader.type = "lumina2"`（Z-Image 没独立 type）、必走 `ModelSamplingAuraFlow shift=3`、latent 用 `EmptySD3LatentImage`（图生图用 `VAEEncode`）、KSampler `steps=8 cfg=1.0 sampler=res_multistep scheduler=simple`。denoise：0.3-0.4 微调 / 0.5-0.65 明显改动 / 0.75-0.9 大改——**实测 0.6 已经偏保守，想换场景得 0.75+**。

**中文界面**：写 `ComfyUI/user/default/comfy.settings.json` 里的 `"Comfy.Locale": "zh"`（键名就是 `Comfy.Locale`）。

**手搓 UI 工作流的坑（踩了一整轮）**：工作流 JSON 有三处必须同时写对，只写一处会导致「节点全在、连线全断、还不报错」：
1. 顶层 `links` 数组 = `[link_id, 源节点id, 源槽位, 目标节点id, 目标槽位, 类型]`
2. 每个源节点的 `outputs[i].links` 要包含该 link_id
3. 每个目标节点的 `inputs[j].link` 要等于该 link_id
存到 `ComfyUI/user/default/workflows/`，然后**在 UI 里真加载一遍**、用 `app.graph._nodes` 逐个查 `inputs[].link != null` 才算验证过。

**进程与启动**：`python_embeded/python.exe -s ComfyUI/main.py --windows-standalone-build --port 8189`，服务在 **127.0.0.1:8189**。

⚠️ **端口必须避开 8188**：本机另有一套 **MiniMax-H3 视频 ComfyUI** 装在 `C:\ComfyUI_windows_portable`（40GB，桌面上 4 个「MiniMax-H3 …」快捷方式）。它的 `launch-h3.ps1` / `run-ref-shot.ps1` / `h3-make-film.ps1` 把 8188 **硬编码**在里面，而且 `run-ref-shot.ps1` 的逻辑是「8188 有响应 → 认为视频服务已就绪」——共用端口会把视频工作流发到生图服务上，报莫名其妙的「模型不存在」。所以生图固定跑 **8189**，视频版继续用 8188。**装第二个 ComfyUI 之前先 `netstat` 看端口，把已有那套的启动脚本先读一遍。**

**必须用 wscript 拉起脱离进程**（见 `ComfyUI.vbs`），否则会话一结束服务就死。一键启动 `start_comfyui.bat`（桌面 `ComfyUI 生图.lnk` 指向它），**没做开机自启**——它空闲就占 4.5GB 显存，会挤掉 GPT-SoVITS 的 TTS 和游戏。

**本机 curl 坑**：`curl -o /dev/null` 和 `-o /tmp/x` 都不行（原生 curl 不认 MSYS 路径，表现为 `http=200 got=0B`）。下载测试要落到真实相对路径再看文件大小。

**NVIDIA 系 CDN（international.download.nvidia.com/.cn）下载要带 Referer**：裸 curl 一律 403（会跳转到 .cn 后被拦）；可用组合 = `--noproxy '*' -A "<Chrome UA>" -e "https://www.nvidia.com/en-us/geforce/broadcasting/broadcast-app/"`，实测 206 放行。**走 7899 中转反而 403**，必须直连（`--noproxy '*'`）。
