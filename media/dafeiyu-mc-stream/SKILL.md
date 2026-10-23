---
name: dafeiyu-mc-stream
description: "Use when 大肥鱼 MC 直播/陪玩（本地服务器 + Mindcraft 机器人）。"
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [minecraft, streaming, mindcraft, douyin]
    related_skills: [onebot-qq-bridge, dafeiyu-drawing]
---

# 大肥鱼 MC 直播（本地）
主人抖音直播玩 MC（正版账号）+ 朋友离线号同屋联机 + AI 大肥鱼在服里陪玩。

## When to Use
- 主人要开播/玩 MC、机器人（大肥鱼）进服陪玩、服务器或 Mindcraft 要起停/排障时。
- 直播模式开关（生图/唱歌婉拒）、联机地址（192.168.1.9:25565）相关。

## 组件与跑法
- **服务器**：`C:\Users\32672\Apps\mc-server`（MC 1.21.6，`online-mode=false`、`player-idle-timeout=0`、eula ✓）。
  起：`cd mc-server && C:/Users/32672/Apps/java21/jdk-21.0.12.1+1-jre/bin/java.exe -Xmx2G -XX:+UseG1GC -jar server.jar nogui`（后台，完成信号 `Done (`）。重启=杀 25565 的 owner PID 再拉起。
- **机器人**：`C:\Users\32672\Apps\mindcraft`。**必须用 node22**（`C:/Users/32672/Apps/node22/node-v22.0.0-win-x64/node.exe main.js`；node26 装不上 canvas）。
  配置：`keys.json`=DEEPSEEK_API_KEY；`settings.js`：version 1.21.6 / host 127.0.0.1 / port 25565 / auth offline / profiles=["./profiles/dafeiyu.json"] / language "en"（en=跳过谷歌翻译那次报错）/ auto_open_ui false。人格在 `profiles/dafeiyu.json`（conversing=官方默认段+大肥鱼中文人设尾巴）。**游戏内名必须 ASCII：dafeiyu**（中文名进不去服务器）。
- **OBS**：`C:\Program Files\obs-studio`（桌面有快捷方式；exe 在 `bin\64bit\obs64.exe`，agent 可代开）。**推流码**从「抖音直播伴侣」（已装 `C:\Program Files (x86)\webcast_mate`）或手机抖音开播页拿（+ → 开直播 → 游戏直播 → 开始游戏直播）；伴侣里没有推流码/OBS 选项=该账号未开放第三方推流，用兜底：OBS 「启动虚拟摄像机」→ 伴侣里选 `OBS Virtual Camera` 作摄像头源（不用码）。码别经手，让主人在 OBS 里自己填。完整流程见 `minecraft-livestream` 技能「开播」一节。
- **语音（已接，2026-10-15）**：`scripts/mc-voice.py` 盯 `mc-server/logs/latest.log` 里 `<dafeiyu>` 聊天行 → `tts-dafeiyu.py`（GPT-SoVITS 9880）→ `ffplay` 播到音箱；直播间靠伴侣「系统声音」采集（开播前必须开）。挂后台用 persist_on_release=true；`--say 文本` 试音；`--all` 连引擎自语也念（默认跳过纯英文短句）。日志含 `[Not Secure] <dafeiyu>` 才算真聊天行。**念之前必须剪掉 `!命令(...)` 尾巴 + 同句 120 秒去重**——mindcraft 每条消息都拖着 `!goToPlayer(...)` 之类调试命令，不剪会一声声念 'go to player…' 像复读机（用户会报「一直在重复」）；守望重启从日志尾读起、别重播历史。游戏聊天里看的 `!命令` 字样是它大脑的工作痕迹，正常。
- **语音输入（F8，2026-10-15）**：`scripts/mc-voice-input.py`（常驻）——按住 **F8** 说话、松开：ffmpeg dshow 录音（麦克风 HECATE G5 Plus，16k mono）→ faster-whisper `small`（用 **GPT-SoVITS 的 venv** 跑，CPU int8；模型已缓存，必须带 `HF_HUB_OFFLINE=1`，本机代理会弄死在线校验）→ SendInput unicode 注入 MC 聊天 + 自动回车。注入前抢焦点（AttachThreadInput + ALT 轻敲解锁；后台进程裸 SetForegroundWindow 会被系统拦）。`--test` / `--inject 文本` 自检；幻觉黑名单（谢谢观看/字幕等）自动跳。背景：MC 里 IME 打不出中文（主人打字全是拼音乱码），语音直送是正解；测试注入凭证：服务器日志出现 `<jxcdog> 本鱼测试`。

## RCON 通道 + 防误杀自愈（2026-10-15 晚，重要）

- **为什么有 RCON**：前台打字只在游戏处于正常游戏画面时才有效（开菜单/最小化/失焦时全被吞——用户报「没反应」的根因）。RCON 无视游戏窗口状态，从系统层直送聊天。
- **启用**：`server.properties`：`enable-rcon=true` + `rcon.password=<随机>` + `rcon.port=25575`，**改完必须重启服务器**。密码就在 server.properties 里，工具直接读。
- **发消息**（python 标准库 socket + struct，UTF-8 完全无损，不像 process_manage 的 submit 管道会把中文转成 GBK 乱码）：`list` 先看主人在不在线 → 在线用 `execute as jxcdog run say 文本`（渲染 `[jxcdog] 文本`）；不在线用 `say [语音] 文本`——**鱼两种格式都当主人消息听**（实测都能触发回应）。tellraw 变体能渲染成 `<名字>` 样式但鱼是否认未验证，没测通过前别用。
- **mc-voice-input.py 现在的发送顺序**：RCON(as jxcdog) → RCON([语音]) → 前台打字兜底；发完照旧回读服务器日志自检。
- **防误杀**：Hermes 的清后台可能连 persist_on_release 的子进程一起杀（一套 MC 组件整批阵亡过）。对策：组件全部用 **脱离模式启动**（`DETACHED_PROCESS`，用 `scripts/run_detached.py`，日志重定向进 `logs/`），杀不到。
- **自动复活**：`scripts/mc-stack-check.py` 体检 5 项（服务器端口/鱼/看护/语音桥/语音输入），缺谁拉谁（脱离启动）；**全绿时零输出**。cron `mc-stack-watch` 每 3 分钟跑它（no_agent 模式，deliver=local）。**主人主动关服时：touch `cache/mc-stack.paused` 暂停自愈**，恢复时删掉。
- **进程计数**：mc-voice-input.py 正常显示为**一对** python（GSV venv 壳 + uv cpython-3.11 真身）；判断重复看壳层。hermes 工具目录的 python 路径含不可复现字符，命令里**永远 glob 现取**：`PYH=$(ls -d .../tools/python-*/python.exe | head -1)`。
- **黑窗坑（已修）**：组件改成脱离启动（无控制台）后，所有子进程 spawn 必须带 `creationflags=subprocess.CREATE_NO_WINDOW`（或 0x08000000）——否则每次调用（ffplay/ffmpeg/tasklist…）都会在主人屏幕/直播画面里闪一个黑色命令行窗（主人会报「每次说话都弹命令窗口」）。已修：mc-voice.py（TTS+ffplay）、tts-dafeiyu.py、mc-fish-watchdog.py（tasklist/taskkill/powershell）。
- **杀进程防自杀**：用 cmdline 正则批量杀 mc-* 时，执行命令的 bash 自身命令行含脚本名会被误杀（命令行文本自匹配）——加 `-and $_.Name -match "python"` 收窄，或先列 PID 再按 PID 杀。

## OBS 远程控制（2026-10-15 打通）
- **推流路线**：抖音对个人号不开放第三方推流码 → 走 **OBS 虚拟摄像机 → 直播伴侣「摄像头」源**（伴侣负责推流，不填码）。伴侣里没有「OBS 推流」选项 = 账号没权限，直接走这条路。
- **OBS WebSocket**：配置在 `%APPDATA%\obs-studio\plugin_config\obs-websocket\config.json`（`server_enabled` 开关、密码、端口 4455 都在这，改完**重启 OBS** 生效）。连不上先查这个文件。
- **启动 OBS 只有一种可靠姿势**：`Start-Process -FilePath 'C:\Program Files\obs-studio\bin\64bit\obs64.exe' -WorkingDirectory 'C:\Program Files\obs-studio\bin\64bit'`。裸启动/os.startfile 会报 **"Failed to find locale/en-US.ini"** 然后弹错退出（实测锁死）；强杀过 OBS 后先删 `%APPDATA%\obs-studio\.sentinel`（崩溃标记）再起，否则弹
  「检测到 OBS Studio 崩溃」安全模式框卡住（且别选安全模式——插件会禁用）。用脚本发这条启动命令时，路径一律写正斜杠或原始字符串——Python 会把 `\b`/`\6` 当转义把路径吃坏（`bin\64bit` → `bin4bit`），报错看着像 OBS 的问题、其实路径根本不存在。
- **obs-websocket v5 协议坑**：请求参数必须包在 `d.requestData` 里！摊在 `d` 层会被回 `code 300 "Your request must contain ... fields"`（明明传了也说不给，其坑无比）。认证 = `base64(sha256(base64(sha256(password+salt))+challenge))`，Identify 要带 `rpcVersion: 1`。
- **建源套路**：`CreateInput {inputName, inputKind:"monitor_capture", inputSettings:{}, sceneName, sceneItemEnabled:true}` → 成功；`SetSceneItemTransform`（OBS_BOUNDS_SCALE_INNER 1920x1080）拉全屏；`StartVirtualCam` / `GetVirtualCamStatus` 查虚拟摄像机；`SaveSourceScreenshot` 截场景验证画面。
- 验证设备：`ffmpeg -list_devices true -f dshow -i dummy` 能看到 "OBS Virtual Camera"（PnP/设备管理器查不到 DirectShow 滤镜，别用那种方式验）；伴侣里选「OBS Virtual Camera」当摄像头即可。
- **显示器采集必须显式设 `monitor_id`**（属性名不是 monitor/display，那两个会报 "Unable to find a property"）：`GetInputPropertiesListPropertyItems {propertyName:"monitor_id"}` 枚举 → **跳过第一项 DUMMY 占位符**，取真显示器值（`\\?\DISPLAY#模型#...`）→ `SetInputSettings {monitor_id:<值>, method:2}`。空值 = 黑屏；验证：OBS 日志出现 `display: G25H3 (1920x1080)` 这种非 (0x0) 行 + `SaveSourceScreenshot` 截图肉眼确认。

## 坑（都踩过）
- **mindcraft 的 LoginGuard 重试有限**：服务器重启窗口里连不上就 `will not be restarted`，鱼再也不回来 → 手动重启 mindcraft 进程。服务器和机器人要成对确认。
- **掉线自愈看护（2026-10-15 起常驻）**：`scripts/mc-fish-watchdog.py` —— 最后一次 join 后出现 left/lost 且缺席 >45s → 自动重启 mindcraft（冷却 120s、1h 最多 8 次、pid 文件单实例）；它平时“卡一下→4 秒自己回来”的小磕绊不会触发（<45s）。看护自身挂后台 `persist_on_release`。
- 服务器踢挂机已关（`player-idle-timeout=0`）；关之前它每 ~30 分钟被踢一次、又自己爬回来。
- **启动链别用 wscript**（WSH 的 Echo 弹窗会卡死调用方）：直接 `Start-Process …\_hermes_start.cmd -WindowStyle Hidden`。
- 重开机后 NapCat 可能没注入（6099/3001 全死但 QQ 进程在）→ 见 `onebot-qq-bridge` 技能的 reboot 修复流程。
- **鱼的「卡住自愈」是正常行为，别修**：`I'm stuck! → I'm free.`，实在出不来就 `Exiting.` → 约 4 秒后自己重连回来（可能伴随服务器警告 `dafeiyu moved wrongly!`）。每次重连还会再打一条 `joined the game`（watch "logged in" 的会再弹通知）——都不是故障，别重启 mindcraft；玩家视角的补救是传送（下条）。
- **鱼飘远/过不来/找不到：控制台直接传**（服务器跑在 pty 会话里，用 process submit 发指令）：`tp dafeiyu <玩家名>` 或 `execute at <玩家名> run tp dafeiyu ~2 ~ ~`（偏两格，否则和玩家重叠成一坨看不见）；日志出现 `Teleported dafeiyu to …` 即成功。
- **朋友连不上 `Invalid characters in username`**：启动器（HMCL）里用户名含中文/特殊字符——离线服也拒非 ASCII 名，改成纯英文/数字再连。
- **「鱼不理人」先查日志再查鱼**：`latest.log` 里得有玩家的 `[Not Secure] <玩家名>` 行才算消息真发出去（教玩家：按 T → 打字 → **回车**）；发出去了还要等它想 5~20 秒（大模型）+ 配音几秒，别当掉线。

## 直播模式（与群里联动）
- 开播前放空文件 `HERMES_HOME/cache/stream_mode.on`（下播删）→ 桥接 `_stream_mode_on()` 自动让唱歌/画图闸门**委婉劝退**（不用重启）。
- 直播/游戏期间点歌、生图都压着（闸门已做 & 实测过）；别自己编「显卡忙」的借口，只在系统明说时转述。
- **坑（2026-10-15 踩实）：下播忘了删 `stream_mode.on` → 唱歌/画图被持续劝退数小时**（当晚 17:07 挂上，23 点主人来问「我没直播，怎么也不让唱歌画图」；其间所有婉拒解释里说的「主人在直播」全是误判）。排查口诀：① `ls cache/stream_mode.on` —— 在，就是它，删掉即时恢复（桥接每回合现读、无缓存、不用重启；**正在直播时绝不要动**）② Steam 状态 `last_states.json` 里主人号（myself）的 `gameextrainfo`。两个都为否仍拦 = 另查。**下播收尾第一条：删它。**
- **忘删有自动兜底（2026-10-15 晚加）**：`qq-bridge-watchdog.py` 每 10 分钟体检 —— 开关挂着 ≥90 分钟且连续 3 轮（≈30 分钟）看不到任何直播/游戏迹象（OBS / 直播伴侣 / MC / 游戏全无）→ **微信提醒主人一次**；同一开关 24h 最多一次，删掉/换新即重置；人在直播或打游戏时绝不打扰。提醒只走看护的推送通道（`_hermes_cmds()` 动态探测多级候选，别在脚本里写死单个 hermes 路径）。

## 常用检查
- 服务器在线：`grep "Done (" mc-server/logs/latest.log`；谁进来了：`grep "joined the game"`
- 机器人：进程 stdout watch `logged in`；它自己的记忆 `mindcraft/bots/dafeiyu/memory.json`
- 端口：25565=服务器、8189=画图（Kontext 编辑）、3001=QQ 事件、8790=桥接。
