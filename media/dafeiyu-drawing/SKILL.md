---
name: dafeiyu-drawing
description: Use when 大肥鱼画图/生图 (local ComfyUI Z-Image-Turbo pipeline).
---

# 大肥鱼画图（本地生图）

QQ 里说「画一张…」/「生成…图」/「把这张图改成…」→ 本地 ComfyUI 出图 → 发回聊天。全程本地，不用任何 API。

## 关键设定
- **端口 8189**（图片专用）。8188 是视频 ComfyUI（MiniMax-H3）的端口，**绝不能共用**（视频脚本靠「8188 有应答」判断自己就绪）。
- **按需拉起**：生图不常来，而 ComfyUI 空转吃 ~4.5GB 显存 → 来了才开；画完闲 `image_idle_shutdown_s` 秒自动关，把显存还给主人。
- **图生图**：「把这张图改成…」→ 原图放进 `ComfyUI/input/`，`denoise` 控制改动幅度。
- **内容闸门**：`qq-bridge._img_blocked(prompt)` 先拦（词表 + **上下文组合规则**），命中直接拒绝、不画（拒绝话术让模型现编，别硬编码）。政策（主人定）：**擦边全放行**——比基尼/三角内裤/泳装/内衣/性感/湿身/兔女郎都画；只挡两类：①全裸类（裸体/全裸/不穿衣服/光着身子/露器官等**强词照拦**；**「裸露」单独已不盲拦**——只在贴着人/身体词（±5 字、不跨标点）时才算红线（`_NUDE_NEAR`），「裸露的齿轮/电线/岩石」放行）②**涉未成年（萝莉/幼女/未成年 × 脱衣去衣 = 组合规则，零容忍）**。
  - **闸门两份拷贝**：真源是 `qq-bridge._img_blocked`；worker（image_service 的兜底闸门）**每次运行现 import 桥接 → 改文件即时生效；消息层（群消息那条路）要重启桥接才生效**。急着交付时可用能 import websockets 的解释器加载桥接模块、手动 `_start_image_gen(umo, prompt)` 重派（等同正常派单、产物照常自己发）。
  - **误伤排查与改法**：先看日志里的命中词（bridge 层 `[image] 内容闸门拦下（uin）命中='X'` / worker 层 `内容闸门拦下：… 命中=`）；中性语境误伤（机械/自然名词被当红线）→ 改**上下文规则**而不是删词；改完**表测三组再交付**：原句放行、强词照拦、擦边回归（比基尼等）。
- **发送**：`import qq-bridge` 借它的 `send_image` 发回 QQ（换平台就换这一处）。
- 冷却：同一个人 `image_cooldown_s` 秒内只画一张（防刷屏）。
- 模型：**Z-Image-Turbo（NVFP4）** —— `z_image_turbo_nvfp4.safetensors`（unet/diffusion_models）+ `qwen_3_4b_fp4_mixed.safetensors`（text_encoders）+ `ae.safetensors`（vae）；
  工作流 8 步、cfg 1.0、`ModelSamplingAuraFlow(shift=3.0)`、CLIP type `lumina2`（上面全写死在 `scripts/image_service.py` 里）。

## 跑一条
```bash
<python> scripts/image_service.py <umo> "一只橘猫在屋顶看夕阳"
# 完成后自动把图发进聊天
```

## Kontext 编辑模型（2026-10-12 上线，改图默认走它）
- 模型（全本地）：unet `flux1-kontext-dev-Q4_K_M.gguf`（~6.6G，GGUF）+ t5xxl_fp8 + clip_l + vae `flux_ae.safetensors`；需要 `ComfyUI-GGUF` 节点包 + python 包 `gguf`。
- **必须逐节点抄官方示例**（ComfyUI_examples/flux/flux_kontext_example 的 PNG 元数据里）：SamplerCustomAdvanced + BasicScheduler + KSamplerSelect(euler/20步) + BasicGuider + RandomNoise + **EmptySD3LatentImage** + **ModelSamplingFlux(1.15/0.5)** + ReferenceLatent(VAEEncode(FluxKontextImageScale(LoadImage)))。**缺 ModelSamplingFlux → 退化成原图复印机，指令全不生效**。
- **只吃英文指令**：中文提示 = 原图复印机；先 DeepSeek 翻英文再送（`_to_english_instruction`，失败退回原文）。
- 路由：image_service `--engine auto` → 有底图=kontext、文生图=zimage。8G 显存一张约 2 分钟（量化+分载）。

## 人名参考图 & 主客同框（2026-10-12）
- **画具体人物**：「画一张科比在打篮球」→ `_guess_person` 猜人名 → `_fetch_ref_image` 搜参考图（百度百科 og:image → 百度图库 acjson（跳过昵图/千图等素材站）→ Bing）→ 当 Kontext 底图 +「这是一张XX的照片…保持长相特征」→ 才画得像本人。搜不到就退回普通文生图。已知缺陷：某些名字会抓歪（马斯克→马），后续再调；加号验证靠 vision。
- **画我和大肥鱼**：`_expand_self_prompt` 先查「我和/跟/与大肥鱼|本鱼|你」→ 返回 `_OWNER_DESC`（主人印象：湖北20岁男生、螺丝刀、拆机主机）+ `_WHALE_CORE`（鱼的外观）同框描述。
- 主人档案（写进三档 QQ 指令）：湖北 20 岁、明年高考、会 AI 提示词/装机/电脑回收、GitHub nmb1337。
- **猜人名要排除虚词**：`_guess_person` 的候选名若含 还/没/不/的/衣/穿/去/改… 一律不认——「衣服还没」曾被当成人名去搜参考图，底图=垃圾素材甚至带水印。真名（科比/马斯克/贾梦）不含这类字，回归测两条即可。

## 官方文档结论（2026-10-12 通读 ComfyUI docs + Z-Image guide 后应用）
- **Z-Image**：不要负向词；喜欢**长而具体**的提示词（80-250词）——短了它自己发挥 → 文生图先经 `_to_detailed_prompt`（DeepSeek 扩写，保留原意+镜头/光线/构图细节，禁空泛词）。8 步 / cfg1.0 / shift3 ✓；1024 原生，竖横版用 896x1152 / 1152x896（桥接按「竖/手机壁纸/横/电脑壁纸」自动传 --size）。
- **Kontext（ComfyUI 官方技巧）**：只支持英文 ✓（已有自动翻译）；**官方建议明确写出「保持什么不变」**——五官/发型/衣服（但**别提姿势**，会把用户要的动作钉死）；别用「transform」用「change/replace」；分段修改效果更好。底图**不要预缩**（FluxKontextImageScale 自己挑最优分辨率，缩了丢细节）。20步/2.5guidance 即官方值 ✓。

## 生图踩坑（2026-10-12 修复，别再踩）
- **「画图发不出去」复发大坑（2026-10-16 实锤）**：Hermes 环境轮换会悄悄把旧 venv（如 b3b）里的 `websockets` 抽走——桥接老进程靠内存里的模块继续活，但**新派生的 image_service 找不到 websockets → 图能画出来但发不出去**（image.log 现 `[napcat] 连接失败：No module named 'websockets'` + `[image] … | None`，文字走 AstrBot 旁路还能兜底）。**修**：`env -u HTTP_PROXY -u HTTPS_PROXY uv pip install --python "<桥接venv>/Scripts/python.exe" -i https://pypi.tuna.tsinghua.edu.cn/simple websockets`——**装完不用重启桥接**（生图=每次新进程）；修完用「能 import websockets 的解释器」加载桥接手动 `_start_image_gen(umo, prompt)` 重派旧单验证。
  - **2026-10-18 复发纪录**：桥接实际跑在 `installs/<装>/environments/b3b5898…/venv/Scripts/python.exe`——**别信 `.Path`**（那只是底层 exe，会误导排查），用 PowerShell `Get-CimInstance Win32_Process -Filter 'ProcessId=<pid>'` 看 **CommandLine** 才是真解释器；uv 装包时路径要写**原生格式**（`C:/...`，MSYS `/c/...` 会报 no venv）。
  - **已内置兜底（2026-10-18）**：`scripts/_vendor/websockets` + qq-bridge 启动时 try-import 失败就 sys.path 注入（`-S` 断 site-packages 实测通过）——以后环境轮换抽走依赖，桥接/生图/点歌子进程照样能发，不用再修解释器。
  - **补发已画好但没发出去的图**：不用重画——加载桥接模块直接 `send_image(umo, 图片绝对路径)` 发原图（ComfyUI output 目录里 `qq_00xxx_.png` 就是）；发前先用 vision 过一眼图合适不合适（图生图/文生图偶尔跑偏，比如「形象画」出成写实真人）。
  - **游戏运行中画图会被自动取消**（服务侧兜底，提示「图片任务取消」）——不是坏了，是保护显卡；等主人下号再画。**但「没玩游戏还被拦」是 Steam 服务器状态滞后/串号，不是真在玩**：`_steam_now()` 现在会本机复核 `HKCU\Software\Valve\Steam` 的 `RunningAppID`——本机没跑任何 Steam app 就按未玩处理（画图/点歌/语音共用这一个探针）。排查顺序：加载桥接打印 `_steam_now()` / `_stream_mode_on()` → `reg query "HKCU\Software\Valve\Steam" /v RunningAppID`（0=没在玩）→ 看 `astrbot_plugin_steam_monitor\last_states.json` 里主号（`monitored_targets[0]`）的 `gameextrainfo`。改探针后桥接要重启（长驻进程有 60s 缓存），image_service 每次新进程即时生效。
- **图生图底图先适配尺寸**：`_fit_src` 把长边缩到 ~1024（8 的倍数）。QQ 里的截图/竖图（480×1384、几十 KB）直喂 VAEEncode → 出图又糊又小、尺寸非标。
- **denoise 分档（实测扫描过的组合，重要）**：小改/加东西 = **0.5**；换装/变身/风格化 = 0.6；**换场景/大动作（「在棉花地里被鞭子抽」）= 0.55 + 提示词必须附上「保持人物原本的五官样貌和衣服不变，只更换背景与场景」** —— 实测 0.55+此句 = 脸/衣服全保住+背景换掉；0.62 脸就变、0.68 直接换人、0.72 更是无关。**光调 denoise 不够，提示词那句才是关键**（0.5+没那句话=只动脸不动景）。
- **链式改图**：「把刚才那张改成…」没带图 → 读 `cache/qq-images/last_out/<umo>.txt` 拿该聊天上一张出图当底图（image_service 成功送图后写这个文件）。
- **说了改图但没带图**（「把提供的照片改成…」+ 文本里有「这张/原图/提供的照片」）→ 别硬画文生图，回话先要图。
- **称呼≠宾语**：句首的「大肥鱼，帮我改这张图」是叫名字 —— `_expand_self_prompt` 绝不能展开成人设（否则照片被硬画成二次元；主人 2026-10-12 抓包）。只有「画大肥鱼/把大肥鱼改成…」这种宾语位置才展开。
- **旧图兜底要保守**：没带底图时，只有明说「刚才那张/上一张」才用 last_out 当底图；其它情况回话要图，别偷偷套旧图。
- **改图提示词**：`_edit_prompt` 抠「想变成的样子」，指代词/「改成」这类动词对模型是噪音。

## 换机器 / 给别人用
见 `SETUP.md`：改 `image_service.py` 头部的三个常量（HERMES_HOME / ROOT / BRIDGE），并照 SETUP 装 ComfyUI + 下三个模型文件。
