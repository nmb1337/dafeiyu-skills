# Project Zomboid（Build 42）专属服务器 · 本机实测配方

## 事实（实测）

- 版本：42.21.0（Build 42 已是 Steam 默认分支；联机所有人必须同版本，模组也要一致）
- 安装：`D:\SteamLibrary\steamapps\common\ProjectZomboid`（自带 `jre64`，无需另装 Java）
- 启动器：`ProjectZomboidServer.bat`（B41 时代叫 `StartServer64.bat`），本质是：
  `jre64\bin\java.exe … -cp ./;projectzomboid.jar zombie.network.GameServer`
- 首次启动：生成 `%USERPROFILE%\Zomboid\Server\<servername>.ini`、`<servername>_SandboxVars.lua`、spawnpoints/spawnregions；世界生成约 60s；日志出现 `*** SERVER STARTED ****` + `server is listening on port 16261`

## 本机托管命令

目录 `C:\Users\<user>\Apps\pz-server\`：

`run_server.cmd`（纯 ASCII）：
```bat
@echo off
cd /d "D:\SteamLibrary\steamapps\common\ProjectZomboid"
".\jre64\bin\java.exe" --enable-native-access=ALL-UNNAMED --add-exports=java.base/jdk.internal.misc=ALL-UNNAMED -XX:+UseZGC -XX:-CreateCoredumpOnCrash -XX:-OmitStackTraceInFastThrow -Xmx6144m -Dzomboid.steam=1 -Djava.library.path="./natives/;./natives/win64/;./" -cp "./;projectzomboid.jar" zombie.network.GameServer -servername dafeiyu -adminpassword <ADMIN_PW> >> "C:\Users\<user>\Apps\pz-server\server-console.log" 2>&1
```

`launch_hidden.vbs`：
```vbs
Set ws = CreateObject("WScript.Shell")
ws.CurrentDirectory = "C:\Users\<user>\Apps\pz-server"
ws.Run "cmd /c run_server.cmd", 0, False
```

- 开服：`wscript.exe "C:\Users\<user>\Apps\pz-server\launch_hidden.vbs"`
- 关服：`Get-NetUDPEndpoint -LocalPort 16261` 取 PID → `taskkill /F /PID <pid>`
- 管理员：`-adminpassword` 传的密码 + 默认用户名 admin（游戏内用）

## 服务器设置（朋友合作局口径）

| ini 键 | 默认 | 建议 | 说明 |
|---|---|---|---|
| PVP | true | **false** | 朋友合作别互相误杀 |
| MaxPlayers | 32 | 8 | 收敛人数 |
| SaveWorldEveryMinutes | 0 | 15 | 隐藏窗口只能杀进程，必须有自动存档 |
| PingLimit | 0 | 0 | 0 = 不踢人；网传的 2000 是写给旧默认值的，不要盲改 |
| Password | 空 | 先空 | 公网转发后建议加 |
| Public | false | false | 不进公共列表，直连 |
| PublicName | My PZ Server | 自定义 | 游戏内显示的服务器名（可中文，改完重启生效） |
| PauseEmpty | true | true | 没人在线暂停省资源 |
| Map | Muldraugh, KY | 默认 | |
| MapRemotePlayerVisibility | 1 | 4 | 地图（M）上显示其他玩家：1=隐藏 2=好友 3=好友+附近 4=所有人；ini 注释就是取值说明，改键前先读注释 |
| UPnP | true | — | 路由器多半不支持，日志会提示后手动转发 |

- 改法：Python `re.sub(r"(?m)^KEY=.*$", "KEY=值", text)` 写回，打印改动行自检，再重启服务器。
- 存档：`%USERPROFILE%\Zomboid\Saves\Multiplayer\<servername>`
- 配置：`%USERPROFILE%\Zomboid\Server\<servername>.ini`

## 联机

- 局域网：`<LAN IP>:16261` —— 多人游戏 → 加入 → 添加服务器 → 填 IP + 端口 16261 → 用户名随意 / 密码空
- 首次进服客户端会弹「必须输入账号和密码」：那是 PZ 的玩家账号（服务器 `Open=true` 时首次进服自动注册），**不是服务器密码**；每人自设一组，之后每次进都用同一组。
- 外网（两条路任选）：①路由器（如 `192.168.1.1`）端口转发 **UDP 16261–16262 → 本机 LAN IP**，朋友连 `<公网IPv4>:16261`；②拿不到路由器权限时用公网 VPS 的 frp UDP 中转（配方见 `references/frp-udp-tunnel.md`），朋友连 `<VPS_IP>:16261`，主人自己也可以用同一地址或局域网地址进。
- 公网 IPv4 **以光猫 WAN 页为准**：家里是联通 PT1570-H10，用户页 `192.168.1.1` 免登录但**没有端口映射**；超级管理员页 `http://192.168.1.1/cu.html`（单密码框）才有。WAN 看 PPPoE 那条 `2_INTERNET_R_VID_88`（实测 116.167.200.22，动态）。**别信 curl**：开加速器时 `curl --noproxy '*' http://ip.3322.net` 返回的是加速器出口 IP（实测 150.255.50.22，和真公网完全不同的网段）；只有返回 `100.64–127.x` 才是 CGNAT，那才需要 ZeroTier/蒲公英
- 服务器名有两套，被问「服务器叫什么」时两个都答：启动参数 `-servername dafeiyu` 决定 ini/存档文件名；游戏内显示名 = ini 的 `PublicName`（默认 `My PZ Server`）
- 版本匹配：Steam 默认分支（无 BetaKey，`appmanifest_108600.acf` 无 betakey 字段）
- UPnP：日志实测 `No UPnP-enabled Internet gateway found` → 手动转发

## 已知坑

- `netstat -anu` 在 Windows 上打印帮助（没有 -u）→ PowerShell `Get-NetUDPEndpoint`。
- 日志 append 模式：重启后要数 `SERVER STARTED` 次数确认是新启动。
- `-Xmx6144m` 时 RSS ≈ 6.5GB；常驻费电，主人不玩就关。
- 隐藏窗口无法输控制台命令（/save /quit）→ 靠自动存档 + 游戏内管理员命令；`taskkill /PID`（不带 /F）对这类 console java 通常无效，直接 `/F`，世界由 `SaveWorldEveryMinutes=15` 兜底。
- `*** Steam is not enabled` = 启动命令漏了 `-Dzomboid.steam=1` → Steam 客户端连不上（局域网也不通）；修好后日志变 `*** Steam is enabled`。
