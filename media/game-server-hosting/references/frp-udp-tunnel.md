# frp UDP 内网穿透（公网 VPS 中转游戏服务器）

**场景**：游戏服务器跑在 NAT 后的 Windows 本机（UDP，如僵尸毁灭工程 16261），朋友从外网直接输公网 IP:端口 进来；不碰路由器。

**拓扑**：朋友 → `<VPS_IP>:16261/udp` → frps（VPS）→ 控制回程 7000/tcp → frpc（本机）→ `127.0.0.1:16261`（游戏服务器）

## 1. 取 frp 程序（GitHub 直连常断）

让 **VPS 自己拉**（云机国际带宽一般更好），本机需要 Windows 版就 `scp` 回来：

```bash
ssh ubuntu@<VPS> 'bash -s' <<'EOS'
cd /tmp
for pre in "" "https://ghfast.top/" "https://ghproxy.net/"; do
  curl -sL --max-time 90 -o frp_linux.tar.gz "${pre}https://github.com/fatedier/frp/releases/download/v0.71.1/frp_0.71.1_linux_amd64.tar.gz"
  tar -tzf frp_linux.tar.gz >/dev/null 2>&1 && { echo LINUX_OK; break; }
done
for pre in "" "https://ghfast.top/" "https://ghproxy.net/"; do
  curl -sL --max-time 90 -o frp_win.zip "${pre}https://github.com/fatedier/frp/releases/download/v0.71.1/frp_0.71.1_windows_amd64.zip"
  python3 -c "import zipfile; zipfile.ZipFile('/tmp/frp_win.zip').testzip()" 2>/dev/null && { echo WIN_OK; break; }
done
ls -la /tmp/frp_linux.tar.gz /tmp/frp_win.zip 2>/dev/null
EOS
scp ubuntu@<VPS>:/tmp/frp_win.zip C:/Users/<user>/Apps/frp/frp_win.zip
```

- 本机直接下也行，但必须**校验**：`unzip -t` / `tar -tzf` 通过才算下完——残缺包解压出来是半截文件，后面会报莫名其妙的错。**别用 `curl -C -` 断点续传 GitHub/镜像**：镜像对 ranged 请求会回 0 字节或错位内容，越续越坏；每次整文件 GET，校验失败就换下一个镜像重下。
- 本机反复失败时：让 VPS 拉（上面的脚本），再 `scp` 回来——云机的国际出口通常比本机稳定（实测本机直连两次断流，VPS 走 ghfast.top 一次成功）。
- 版本号可查 `https://api.github.com/repos/fatedier/frp/releases/latest`（本机经代理可用）。

## 2. VPS 端装 frps

`/opt/frp/frps.toml`：

```toml
bindPort = 7000

auth.method = "token"
auth.token = "<随机32hex>"

webServer.addr = "0.0.0.0"
webServer.port = 7500
webServer.user = "admin"
webServer.password = "<同一个 token>"

allowPorts = [{ start = 16261, end = 16262 }]
```

- token 本机生成：`python -c "import secrets; print(secrets.token_hex(16))"`，两边配置写同一个；不写进聊天记录。
- 安装脚本在**本机写好再 `ssh 'bash -s' < script`** 推送，避免多层 heredoc 引号地狱：

```bash
cd /tmp
tar -xzf frp_linux.tar.gz
sudo mkdir -p /opt/frp
sudo cp frp_0.71.1_linux_amd64/frps /opt/frp/frps
sudo chmod +x /opt/frp/frps
# sudo tee /opt/frp/frps.toml >/dev/null <<'T' ... T   ← 直接生成配置
sudo tee /etc/systemd/system/frps.service >/dev/null <<'S'
[Unit]
Description=frps server
After=network.target

[Service]
Type=simple
User=root
ExecStart=/opt/frp/frps -c /opt/frp/frps.toml
Restart=on-failure
RestartSec=3

[Install]
WantedBy=multi-user.target
S
sudo systemctl daemon-reload
sudo systemctl enable --now frps
ss -lntup | grep -E ':7000|:7500'   # 两个端口都要 LISTEN
sudo ufw status                      # active 则放行 7000/tcp、7500/tcp、游戏端口/udp
```

## 3. 本机 Windows 端装 frpc

`C:\Users\<user>\Apps\frp\frpc.toml`：

```toml
serverAddr = "<VPS_IP>"
serverPort = 7000
auth.method = "token"
auth.token = "<同一个 token>"

[[proxies]]
name = "pz-16261"
type = "udp"
localIP = "127.0.0.1"
localPort = 16261
remotePort = 16261

[[proxies]]
name = "pz-16262"
type = "udp"
localIP = "127.0.0.1"
localPort = 16262
remotePort = 16262
```

- 先前台试连：`timeout 8 ./frp_0.71.1_windows_amd64/frpc.exe -c frpc.toml`
  成功标志：`login to server success` + 每个代理 `start proxy success`。
- 改后台常驻：`run_frpc.cmd`（**纯 ASCII**，日志 `>> frpc.log`）+ `launch_frpc_hidden.vbs`（`ws.Run "cmd /c run_frpc.cmd", 0, False`）。
- **常驻前先 `taskkill /F /IM frpc.exe` 清残留**：旧实例还占着代理名时，新实例会报 `start error: proxy [x] already exists`，frps 上代理状态一直 offline。

## 4. 验收（从 VPS 查，比盯着本机日志靠谱）

```bash
ssh ubuntu@<VPS> "curl -s -u admin:<token> http://127.0.0.1:7500/api/proxy/udp"
# 期望：每个代理 status=online；curConns / todayTrafficIn 随玩家进出增长
ssh ubuntu@<VPS> "ss -lnu | grep -E '16261|16262'"   # frps 已监听 UDP 游戏端口
```

- 真实端到端验证 = 主人/朋友在游戏里连 `<VPS_IP>:16261`，同时盯游戏服务器日志是否出现连接行。
- 主机侧确认游戏服务器本身在跑：`Get-NetUDPEndpoint -LocalPort 16261`（frpc 只负责搬运，服务没起一样连不上）。
- **端到端证明转发（不依赖游戏）**：在 frps `allowPorts` 里临时包含一个测试端口（如 16263），frpc 加一个 `pz-test` udp 代理（localPort/remotePort=16263），本机起一个 UDP 监听（python `socket.bind(('0.0.0.0',16263)); recvfrom()`），从 VPS `sendto(b'probe', ('127.0.0.1',16263))` —— 本机监听器收到即通路 OK。**frp 对同一代理会复用 work connection，不能用「frpc 日志有没有新行」判断单个探测包是否送达**，只看监听器是否收包。
- **判断「客户端发包了但没人回」**：VPS 上 `sudo timeout 60 tcpdump -n -i any 'udp portrange 16261-16262'`（源 IP 应是玩家公网 IP，说明安全组放行且包到了）；再看 frps API 的 `todayTrafficOut` —— 恒 0 = 游戏服务器从未回应（问题在游戏侧，如没开 Steam 模式），不是隧道丢包。

## 5. 开机自启

把两个 `launch_hidden.vbs`（游戏服务器、frpc 各一个）复制到
`%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\`；登录即拉起，删掉即取消。

## 6. 排障笔记

- **安全组判断**：本机 `bash -c 'echo > /dev/tcp/<VPS_IP>/7000'`——秒回 `Connection refused` = 安全组放行、只是 frps 还没起；卡住超时 = 被云安全组拦，必须去控制台放行 7000/tcp + 游戏端口/udp（服务器里改 ufw 没用）。
- **frpc 走本机代理 = 隧道假死（最贵的一个坑，实测）**：frpc 的 work connection 对端显示 `127.0.0.1:7899`（本机加速器中转）而不是 `<VPS_IP>:7000`，说明 frpc 继承了 `HTTP_PROXY/HTTPS_PROXY`，控制连接经代理出海。表现极具误导性：frps API 里代理 `online`、`todayTrafficIn` 在涨（玩家的包到了 VPS），但 `todayTrafficOut` 恒 0，frpc 侧没有新的 work connection，游戏服务器日志零连接 → 玩家「服务器无响」，可表面看一切正常。修复：`run_frpc.cmd` 开头清空代理（`set HTTP_PROXY=`/`HTTPS_PROXY=`/`ALL_PROXY=` 及小写）+ `set NO_PROXY=*`，重启 frpc。验收：`netstat -ano | grep <frpc PID>` 必须看到直连 `<VPS_IP>:7000`；frpc 日志里 work connection 的对端也应是 `<VPS_IP>:7000`。
- 隧道通了但游戏侧还是不行时，先看游戏服务端自身的联机层是否开启（如 PZ 的 `*** Steam is not enabled`）——那是游戏的事，不是 frp 的事。
- 朋友流量全走 VPS：2 核 2G 小机器带几个人够用；按流量计费的 VPS 要提醒主人。
- 服务器无密码 + 公网可达 = 任何人可进 → 交付时提醒加密码。
- 交付时把「别人连什么」和「主人自己连什么」分开写：别人 `<VPS_IP>:16261`；主人可同地址，也可局域网 `<LAN IP>:16261`（局域网更快、不占 VPS 流量）。
