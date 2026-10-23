---
name: minecraft-livestream
description: "Use when 开 MC 服务器/直播、鱼进游戏 (server+Mindcraft+OBS)."
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [minecraft, stream, mindcraft, obs, game]
---

# MC 直播栈（本机）

## When to Use
- 主人说「开/关 MC 服务器」「要开播玩 MC」「让大肥鱼进游戏」；开播前彩排、设直播模式开关。
- mindcraft/服务器行为排查（鱼掉线、老是死、被踢出）。

主人（贾梦）要直播玩 MC：他 + 朋友（离线号）+ AI 大肥鱼一个世界。**服务器平时是关的；他说「开」再开，说「关」把服务器和鱼一起关。**

## 组件与路径
- 服务器：`C:\Users\32672\Apps\mc-server`（1.21.6，离线模式，端口 25565）
  - 启动（**pty 后台**跑，方便往控制台发指令）：
    `cd C:/Users/32672/Apps/mc-server && "C:/Users/32672/Apps/java21/jdk-21.0.12.1+1-jre/bin/java.exe" -Xmx2G -XX:+UseG1GC -jar server.jar nogui`
  - pty 会话里 submit 的控制台指令：`gamerule doInsomnia false`（禁幻翼）/ `gamerule keepInventory true`（死亡不掉装备）/ `time set day` / `stop`（优雅关服）
  - 已存进世界档（重开保留）：doInsomnia=false、keepInventory=true；server.properties 里 `player-idle-timeout=0`、`online-mode=false`
- AI 大肥鱼：`C:\Users\32672\Apps\mindcraft`（Mindcraft 接 DeepSeek）
  - 启动（后台）：`cd C:/Users/32672/Apps/mindcraft && C:/Users/32672/Apps/node22/node-v22.0.0-win-x64/node.exe main.js`
  - node 必须用 `Apps\node22`（系统 node26 编不过 canvas）；配置就绪：keys.json（DeepSeek）/ settings.js（127.0.0.1:25565, auth offline, dafeiyu profile）/ profiles/dafeiyu.json（人设+记忆）
  - ⚠️ LoginGuard 碰上「服务器正好没开」会放弃重试 → 服务器重启后鱼没回来就**重启 mindcraft**
- OBS：已装 `C:\Program Files\obs-studio`（桌面快捷方式「OBS 直播」）
- 玩家端：桌面「MC 启动器（HMCL）」→ 版本 1.21.6 → 连 `192.168.1.9:25565`；朋友同款、离线登录、同一 Wi-Fi
- 防火墙本机全关，不用放行

## 直播模式（点歌/画图闸门）
- 开播 = 建空文件 `%HERMES_HOME%\cache\stream_mode.on`；下播删掉（免重启生效）
- 效果：QQ 里点歌/画图被婉拒（「主人正在直播」话术），桥接 + image_service 双保险

## 开播（推流码 / 直播伴侣 / OBS）
主人问「推流码/推流地址在哪看」= 抖音的「推流地址 + 串流密钥」两段，填进 OBS：`设置 → 直播 → 服务：自定义`（服务器=rtmp 段、串流密钥=stream 段）。
- **抖音直播伴侣已装**：`C:\Program Files (x86)\webcast_mate`（启动器 `*Launcher.exe`、主程序在版本号子目录、开始菜单「直播伴侣」）。它既能自己推流，也是 OBS 推流码的来源；开播前把它打开是标准动作（agent 可代开）。启动器路径用通配取（`Get-Item '...\webcast_mate\*Launcher.exe'` 再 `Start-Process`），**别把中文 exe 名写进命令**。
- **拿码两条路**：① 伴侣登录 → 开播流程（游戏直播方向）→ 找「推流地址/推流码」（或带 OBS 字样的选项）；② 手机抖音：`+` → 开直播 → 游戏直播 → 开始游戏直播 → 弹推流地址页 → 复制。
- **伴侣里找不到推流码/OBS 选项 = 该账号没被开放第三方推流**（抖音只开给部分账号）。兜底（所有账号可用、不用码）：OBS 右下角「启动虚拟摄像机」→ 伴侣里加「摄像头」来源选 `OBS Virtual Camera` → 伴侣里直接开播。
- 推流地址+密钥**每次开播都会刷新**，当次拿当次填。**码等于半个直播权限：不要接收/经手/转存**，让主人在 OBS 里自己粘贴。
- OBS 全路径：`C:\Program Files\obs-studio\bin\64bit\obs64.exe`（`Start-Process` 直接开，工作目录同 bin\64bit）。
- **启动验证**：agent 拉起的 GUI 会出现在主人的桌面上（实测）。进程名/路径过滤可能漏检（权限/编码），用窗口清单兜底：`Get-Process | ? MainWindowTitle -ne '' | ConvertTo-Json | Out-File <tmp.json> -Encoding utf8` 再读文件，看到目标窗口名即成功。

## 预检（别人可能已经起过了）
听到「接鱼/要开播」**先核状态、后动手**——服务器/鱼可能已由另一条渠道（桌面/微信会话）或上一波操作起好，重复拉起会掐掉正在进行的局：
- 服务器：`netstat -ano | grep ':25565 .*LISTENING'` 有监听 + 进程列表里 `server.jar` 在；
- 鱼：`node … main.js` 进程在，且 `tail mc-server/logs/latest.log` 能看到 `dafeiyu joined the game`（它在游戏里还会自己吱一声）；
- 开播闸门：`ls %HERMES_HOME%\cache\stream_mode.on`（下播后应被删掉；OBS 进程不在 = 大概率已下播）。
- **鱼脑子预检**：开播前拿 `mindcraft\keys.json` 里的 DEEPSEEK_API_KEY 发一次最小 chat 请求（只打印 HTTP 码/模型名，**别回显 key**）——非 200 就先修 key，别等直播中途鱼变哑巴。
- 都齐 → 回话确认即可；缺哪个补哪个（服务器→等 `Done (`→mindcraft，成对）。

## 开关机顺序
- 开：服务器（pty）→ 等 "Done (" →（可选）控制台指令 → mindcraft → 要开播再加 stream_mode.on + OBS + 直播伴侣（推流码获取见「开播」一节）
- 关：控制台 `stop` + kill mindcraft —— **必须一起关**，否则鱼会疯狂重连
