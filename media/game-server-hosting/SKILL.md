---
name: game-server-hosting
description: "Use when 给游戏开联机服务器（僵尸毁灭工程/Minecraft 等）：开服、改配置、局域网/外网加入、排障。"
version: 1.0.0
author: Hermes Agent (大肥鱼)
license: MIT
platforms: [windows]
metadata:
  hermes:
    tags: [game-server, 联机, 开服, project-zomboid, 僵尸毁灭工程, steam, port-forward]
---

# 本地游戏服务器开服（给朋友联机）

## When to Use

- 主人说「XX 怎么联机 / 帮我开个服务器 / 朋友进不来」。
- 单机游戏要变 2–8 人朋友局，本机当主机（Windows、公网 IPv4 或 CGNAT 都可能）。
- 现有家庭服务器要改设置、重启、加人/踢人。

具体游戏的实测配方放在 `references/`：僵尸毁灭工程 → `references/project-zomboid.md`。

## 流程

### 0. 「帮我开服」先查是不是已经在跑——三层一起看

开服请求先当巡检处理，不要直接重启（重启 = 世界重新加载 + 玩家被踢，还白费一次冷启动）：

- 游戏进程 + 端口：`Get-Process java`（或其他服务端进程）、`Get-NetUDPEndpoint -LocalPort <port>`。
- 中转：`frpc` 进程在，且它自己的日志尾部有当天的 `login to server success` + `start proxy success`（只看进程在不算通）。
- 出口：VPS 上 `systemctl is-active frps` + `ss -lunp | grep <port>`；frps 的 web API 若回 `Unauthorized` 不代表挂了（缺 token 而已），别据此判定故障。
- 三层全绿 → 直接把地址发给用户，并说明「已经在跑」；任一层缺 → 只补那一层。
- **一台机器装了多个游戏服时，「服务器」是歧义词**：先报当前在跑的是哪一个（附证据），再问另一台要不要一起开；不要凭习惯猜一个就开，也别把已经跑着的那个重启一遍。

### 1. 先侦察，别先装东西

- 找 Steam 库：`grep -aoE '"path"\s+"[^"]+"' "<Steam>/steamapps/libraryfolders.vdf"`（可能多盘）。
- 找游戏目录 + 版本（游戏用户目录里的 `version.txt` 之类）。**版本号记下来：联机时所有人必须完全一致，模组也要一致。**
- 游戏目录里先找**自带的服务端启动器**——很多游戏本体就带（僵尸毁灭工程 B42 = `ProjectZomboidServer.bat`；B41 = `StartServer64.bat`）。Steam「工具」里的 Dedicated Server 是可选项，先别急着装。
- 游戏用户目录已存在（`%USERPROFILE%\Zomboid` 等）= 游戏跑过，存档位置也在这里。

### 2. 脱离启动 + 日志落盘

- 写纯 ASCII 的 `run_server.cmd`（cd 到游戏目录 → 调 java/exe → stdout+stderr 重定向到 `server-console.log`），再用 `launch_hidden.vbs`（`WScript.Shell.Run "cmd /c run_server.cmd", 0, False`）隐藏启动——和本机其他长驻服务同一套路。启动器放独立目录（如 `C:\Users\<user>\Apps\<game>-server\`），游戏更新不会覆盖。
- **日志是追加模式**：确认「这次启动成功」要数关键行出现次数（`grep -ac "SERVER STARTED"`），不能只看 tail 最后一行（上一轮的行还在）。

### 3. 等首次启动（世界生成）

- 首次启动会生成配置 + 世界，1–3 分钟正常；轮询日志关键词（`SERVER STARTED` / `listening on port`）。
- **Windows 上查端口别用 `netstat -anu`（Windows netstat 没有 -u，会直接打印帮助）** → 用 `powershell Get-NetUDPEndpoint -LocalPort <port>` / `Get-NetTCPConnection -LocalPort <port>`。

### 4. 改配置 → 重启生效

- 配置一般在 ini/lua（如 `Zomboid/Server/<servername>.ini`）。用 Python 正则改键并打印改动行；**服务器只在启动时读配置，改完必须重启**。
- 重启：按端口取 PID → `MSYS_NO_PATHCONV=1 taskkill /F /PID <pid>` → 重新 `wscript` 拉起 → 再数一次 `SERVER STARTED`。
- 默认值常不适合朋友局（例：僵尸毁灭工程默认 `PVP=true`、`MaxPlayers=32`、自动存档 0 分钟）→ 按「合作局」口径调：关友伤、人数收敛、开自动存档（15 分钟）、密码先留空。

### 5. 加入方式（先问玩法，再选方案）

- **先定玩法再动手**：临时凑一局 → 游戏内 Host + Steam 邀请（零端口，但主机必须在线）；「朋友直接输 IP、24h 常驻」→ 路由器端口映射优先，拿不到路由器权限就用公网 VPS 的 frp 中转（见 §6.5），都没有再 ZeroTier（双方都要装客户端）。方案没定就先别开建。
- **局域网**：本机 LAN IP（`Get-NetIPAddress -AddressFamily IPv4`）+ 端口，朋友直接输 `IP:端口`。
- **外网**：公网 IPv4 + 路由器端口转发（UDP）。**公网 IP 必须从路由器/光猫的 WAN 页读，不要信 curl**：机器上装着加速器（TUN 模式）时，`curl --noproxy '*' ip.3322.net` 返回的是加速器出口 IP，不是家里的真公网 IP（实测两条完全不同的网段，朋友按 curl 的地址连必然失败）。没有管理员权限时可以先拿 curl 粗值，一旦进得了路由器就必须回 WAN 页核对。
- **`100.64.0.0/10` 段 = 运营商 CGNAT**，端口转发无效 → 改走 ZeroTier/蒲公英组网，或让正版朋友走游戏自带 Host + Steam 邀请。
- UPnP 不一定有：服务器日志会打 `No UPnP-enabled Internet gateway found` → 手动转发（协议 UDP、外部端口 → 内部 IP:端口）。

### 6. 密码 / 路由器登录（硬规矩）

- 主人在聊天里贴了任何密码（路由器/账号）→ **不落用、不存、不拿去登录**，并说明聊天日志会留记录。
- 两条正路：① 他本人执行 `hermes vault add`，或在浏览器掩码弹窗里输入（`browser_vault action=save_login`，之后自动填）；② 他本人在页面/弹窗输入。
- 浏览器自动化被占用时的**可工作兜底**：把菜单路径 + 每个字段（协议/外部端口/内部 IP/内部端口）写成逐步清单交给他点。不要为了自动化硬杀他正在用的浏览器——先问；关浏览器会丢未保存标签。
- **服务器/SSH 凭据同理**：本机 `ssh-keygen -t ed25519 -f ~/.ssh/id_ed25519 -N ""` 生成密钥对，把**公钥**塞进双击 `.cmd`（`ssh -o StrictHostKeyChecking=accept-new <user>@<ip> "mkdir -p ~/.ssh && chmod 700 ~/.ssh && echo '<公钥>' >> ~/.ssh/authorized_keys && chmod 600 ~/.ssh/authorized_keys"`），他双击、在自己窗口里输一次密码；装完 `ssh -o BatchMode=yes <user>@<ip> "echo KEY_LOGIN_OK"` 验证，之后全程密钥免密。
- **`.cmd` 必须纯 ASCII，中文提示也不行**：cmd 按系统 ANSI(GBK) 解析批处理，UTF-8 中文会吃掉行尾、把后半行拆成乱码命令执行，表现就是「双击没反应」或窗口一闪而过；`chcp 65001` 救不了（文件已被按 GBK 读入）。提示语全用英文。
- **先确认用户名，再谈密码**：云厂商 Ubuntu 镜像默认禁用 root 密码登录，正确用户常是 `ubuntu`（带免密 sudo）；Debian=`debian`、CentOS=`centos`。用户名不对和密码错都会回同一句 `Permission denied (publickey,password)`——`ssh -v` 里看到 `we sent a password packet` 才说明密码确实发出去了。
- **别用 BatchMode 试用户名**：`BatchMode=yes` 直接跳过密码认证，只能验证公钥，用它挨个试用户名等于没试——试密码要 `-o PreferredAuthentications=password -o NumberOfPasswordPrompts=1`。
- **用户明确把密码交给你、让你来试时**（双击脚本这条路走不通的兜底）：`SSH_ASKPASS=<临时脚本> SSH_ASKPASS_REQUIRE=force DISPLAY=:0 ssh …` 一次性登录 → 立刻装公钥，临时脚本用完 `rm`；装完只走密钥。事后提醒：这串密码已在聊天记录里，建议在控制台改掉（改密码不影响已装好的密钥）。
- 服务器无密码 + 公网转发 = 任何人可进 → 交付时提醒加密码。

### 6.5 拿不到路由器权限时的兜底（按顺序选）

- **先分层找端口映射**：用户级页面可能根本没有 NAT 设置（联通光猫 PT1570-H10 实测：`192.168.1.1` 免登录进去只有 状态/网络/安全/管理，全网无端口映射）；端口映射只在超级管理员页 `http://192.168.1.1/cu.html`（一个密码框、用户名隐含 CUAdmin），密码是光猫贴纸上的。拿到后**让他本人在浏览器窗口里输密码**，你再接手点配置。
- **浏览器自动化怎么开**：Hermes 的 local 浏览器（`browser.use_real_profile`）要求本机 Edge/Chrome **完全退出**才不被 profile 锁挡住（托盘模式会自动复活进程，关完要验证进程数=0，必要时 `taskkill /F /IM msedge.exe`——但先问他）；不想关他的浏览器就用 **Playwright MCP**（`mcp__playwright__browser_*`）——独立浏览器、能直达局域网地址、完全不碰他的 profile。
- **ZeroTier（不碰路由器）**：本机装 MSI 要提权（`Start-Process msiexec -ArgumentList '... /qn' -Verb RunAs -Wait`，会弹 UAC）；装完服务 `ZeroTierOneService` 应为 Running。`zerotier-cli` 以普通用户跑会报 `authtoken.secret not found or readable` → 用提权 shell 跑；只读时改从 `C:\ProgramData\ZeroTier\One\identity.public` 取第一段（10 位十六进制）拿本机节点 ID。**建网络必须他本人注册**（my.zerotier.com 邮箱验证，无法自动化）；16 位 Network ID 不是密码，可以发。流程：他建网络 → 本机 `zerotier-cli join <id>` → 他在后台 Devices 勾 Authorized → 朋友装客户端 join 同一 ID → 他再勾 → 朋友连「本机 ZeroTier IP:16261」。
- **主人有公网 VPS 时用 frp**（朋友直接连公网 IP，不用装任何软件）：完整配方见 `references/frp-udp-tunnel.md`（frps.toml / systemd / frpc.toml / 开机自启 / 验收一条龙）。要点：VPS 跑 frps（7000/tcp 控制 + `type="udp"` 的 remotePort），Windows 跑 frpc；先解决登录（见 §6）。最容易卡住的三件事：①**云安全组要放行 7000/tcp 和游戏端口**（控制台操作，服务器里改不了）——本机 `bash -c 'echo > /dev/tcp/<ip>/7000'` 秒回 `Connection refused` = 安全组已放行、只是没服务；卡住超时 = 被安全组拦；②**GitHub 下 frp 包经常残缺**→ 下完必须 `unzip -t`/`tar -tzf` 校验；本机拉不动就让 VPS 拉（镜像 `ghfast.top` 实测可用）再 `scp` 回本机；③**残留 frpc 抢代理名**：旧实例没退时新实例报 `start error: proxy [x] already exists` → 先 `taskkill /F /IM frpc.exe` 再启唯一实例；④**frpc 继承 `HTTP(S)_PROXY` 会绕本机中转出海而假死**：frps 的 `todayTrafficIn` 在涨、`todayTrafficOut` 恒 0，frpc 的 work connection 对端是 `127.0.0.1:7899` 之类本地中转而不是 VPS——启动器里清空 HTTP_PROXY/HTTPS_PROXY/ALL_PROXY（小写也清）并设 `NO_PROXY=*`，重启后 netstat 必须看到直连 `<VPS_IP>:7000`（细节 `references/frp-udp-tunnel.md` §6）。

### 7. 交付说明（通俗，能直接转发给朋友）

- 怎么进：游戏菜单路径 + IP + 端口 + 用户名/密码规则。
- 怎么开/关服：启动器路径双击 / 「跟本鱼说关服」；存档 & 配置路径。
- 管理员口令单独给一次，之后不要复述。
- 版本必须一致 + 模组必须一致。
- 电费提醒：主人很在意，服务器常驻费电，不玩了就关。
- 常驻需求：把 `launch_hidden.vbs`（游戏服务器、隧道各一个）复制到 `%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\`，登录即自动恢复；告诉主人删掉即取消。

## 坑

- 服务端启动器参数（管理员密码、服务器名、内存）可以直接传给服务端主类；改内存就是改 `-Xmx`（`-Xmx6144m` 时 RSS 约 6.5GB，32GB 机器无压力）。
- 隐藏窗口开服 = **无法在控制台输管理命令**（save/quit 只能杀进程）→ 把自动存档开起来（`SaveWorldEveryMinutes>0`），重要节点用游戏内管理员命令 `/save`；需要控制台就改可见窗口启动。
- 杀进程重启前先想清楚世界状态：刚生成的空世界可以硬杀；有玩家在的服先等自动存档或先看控制台能不能优雅 quit。
- 公网 IP 是动态的——告诉用户「哪天连不上先喊本鱼查最新 IP」。
- 端口别猜：以官方文档为准（僵尸毁灭工程 B42 = UDP 16261，16262 一起转发更稳），协议选错（TCP 填成 UDP 的反面）是最常见的「转发完还是连不上」。
- **官方（Steam）客户端报「服务器无响」时，先查服务端有没有开平台联机层，别先怀疑端口**：第三方启动器直接跑服务端主类时常常不带平台开关（僵尸毁灭工程日志 `*** Steam is not enabled`），此时 Steam 客户端会拒绝连接——**局域网也一样连不上**，于是端口映射/防火墙全线白查。PZ 修法：启动参数加 `-Dzomboid.steam=1`，重启后日志应出现 `*** Steam is enabled` 与 `listening on port 16261 (for Steam connection)`；客户端看到「必输入账号和密码」才算真连上（首次进服要账号+密码，服务器无密码 ≠ 无玩家账号）。
- **按命令行关键字过滤进程会匹配到自己**：`Get-CimInstance Win32_Process | Where CommandLine -like '*GameServer*'` 会把正在执行这条查询的 shell 也列进去，误报「残留进程」。确认服务是否真活着用：`Get-Process java`、端口归属（`Get-NetUDPEndpoint` / `Get-NetTCPConnection` 的 OwningProcess）、或 Linux 侧 `ss -lntup`。

## References

- `references/project-zomboid.md` — 僵尸毁灭工程 Build 42 专属服务器本机实测配方（启动命令、ini 键值、端口、存档路径、联机说明）。
- `references/frp-udp-tunnel.md` — 公网 VPS 中转 UDP 游戏服（frps + frpc 全流程、systemd、开机自启、验收与排障）。
