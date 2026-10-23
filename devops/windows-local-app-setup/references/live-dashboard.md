# Live Dashboard（视监面板）本机部署

上游：`Monika-Dream/live-dashboard`（Bun 后端 + Next.js 静态前端 + SQLite，端口 3000）
配套：`Pancakes-Labs/astrbot_plugin_live_dashboard`（AstrBot 插件，QQ 里用指令查状态）

**上游自带 `AI_README.md`——专门写给 AI 的部署手册（环境变量真源表 + 自检清单 + 排查表 + 禁止事项）。
部署前先拉这个文件，它比 README 准。**

## 本机为什么不用 Docker

官方三条路全走 Docker，但这台机器 **没有 Docker、没装 WSL2、且 `HypervisorPresent=False`**
（虚拟化没在 BIOS 开）—— 走 Docker 要进 BIOS + 重启，不值得。
改用源码原生跑：Bun 是单文件可执行，前后端都用它，比 Docker Desktop 轻得多。

## 布局

| 东西 | 路径 |
|---|---|
| Bun | `C:\Users\32672\Apps\bun\bun.exe`（GitHub release 的 `bun-windows-x64.zip` 解压即用） |
| 服务端仓库 | `C:\Users\32672\Apps\live-dashboard` |
| 后端（跑这个） | `...\packages\backend`，`bun run src/index.ts`，cwd 必须是这里（Bun 只读 cwd 的 `.env`） |
| 配置 | `...\packages\backend\.env`（凭证文件，只能走终端写，patch/write_file 会被拒） |
| SQLite | `...\packages\backend\data\live-dashboard.db` |
| 前端产物 | `packages\frontend\out\` → 拷到 `packages\backend\public\`（后端默认 `STATIC_DIR=./public`） |
| Windows Agent | `C:\Users\32672\Apps\live-dashboard-agent\`（`live-dashboard-agent.exe` + `config.json` 必须同目录） |
| 启动器 | `$HERMES_HOME\gateway-service\LiveDashboard.vbs` / `LiveDashboardAgent.vbs` + Startup 两个包装 |

## 从零重建（升级/迁移时照抄）

```bash
# 1) 克隆（GitHub 直连不通，靠用户级 HTTP(S)_PROXY=127.0.0.1:7899 走中转即可，无需任何绕过）
git clone --depth 1 https://github.com/Monika-Dream/live-dashboard.git

# 2) 依赖 + 构建
cd packages/backend && bun install
cd ../frontend && bun install && bun run build

# 3) 组装
cd ..; rm -rf backend/public; mkdir -p backend/public; cp -r frontend/out/. backend/public/
mkdir -p backend/data          # ← 不建它 SQLite 直接 SQLITE_CANTOPEN

# 4) .env（用 python secrets 生成，别手写）：
#    HASH_SECRET=<hex32>            ← 必填，缺了进程立刻退出
#    DEVICE_TOKEN_1=<hex16>:my-pc:我的电脑:windows
#    DEVICE_TOKEN_2=<hex16>:my-phone:我的手机:android
#    DISPLAY_NAME / PORT=3000 / DB_PATH=./data/live-dashboard.db
```

**每台设备一个 token，绝不共用**（共用的两台会挤在同一张卡片里互相覆盖状态）。
Agent 只填四段里的**第一段**。

## 踩过的坑

- **git 连不上 GitHub ≠ 要加镜像**：本机直连 github.com 是死的（curl 返回 000），但经用户级
  `HTTP(S)_PROXY=127.0.0.1:7899` 中转是 **200**。曾经全局 `.gitconfig` 里有条
  `url.https://mirror.ghproxy.com/...insteadof=https://github.com/` 把**所有** github 地址改写到
  mirror.ghproxy.com —— 那个镜像早已下线（直连/走代理都是 000），导致**一切** git 网络操作都以
  `schannel: failed to receive handshake` 告终（连 hermes 自己的更新都接连失败）。
  已删除：`git config --global --unset 'url.https://mirror.ghproxy.com/https://github.com/.insteadof'`。
  以后再遇到 git 连不上 GitHub，第一步查 `git config --global --list | grep -i insteadof`，
  **不要再靠 GIT_CONFIG_GLOBAL=/dev/null 绕——那只是掩盖症状**。

- **`SQLITE_CANTOPEN`** = `./data/` 目录不存在。Docker 镜像里自动建，裸跑要自己 `mkdir`。
- **启动器里的单实例检测会吞掉整个启动**：我用 `MSXML2.XMLHTTP` 探 3000 端口，它走 WinINET →
  继承机器级 `HTTP_PROXY=127.0.0.1:7899` → 探到的其实是中转站，判断逻辑失效、脚本静默退出。
  本地启动器**不要**用带代理语义的 HTTP 客户端做端口探测（或干脆不做——第二个实例绑不上端口自己就退了）。
- **`printf` 写 Startup 包装脚本会吃掉路径里的反斜杠**（`C:\Users` → `C:\Users?72`）。用 Python 以
  ASCII 写，写完 `cat` 回读一遍。
- 前端 `bun install` 慢（140s+，45 个包）；`timeout` 命令在 git-bash 里会撞 Windows 自带的同名 exe。

## AstrBot 插件侧

- 克隆到 `<core>/data/plugins/astrbot_plugin_live_dashboard`（`--depth 1`）。
- 配置 `<core>/data/config/astrbot_plugin_live_dashboard_config.json`：按 `_conf_schema.json` 递归取默认值，
  只改 `connection.base_url = http://127.0.0.1:3000`（公开读接口不需要 token）。
- 依赖 httpx/aiohttp **AstrBot venv 里本来就有**，不用装。
- 热重载：自签 HS256 JWT（`dashboard.jwt_secret`，任意非空 username）→ `POST /api/plugin/reload {"name": ...}`
  到 6185，见技能 astrbot-plugin-ops。
- 指令：`视奸`（别名 ldb / 设备状态 / 状态面板）、`视奸服务状态`、`视奸时间线`、`视奸健康`、`视奸好友`。
- **本机 AstrBot 收得到 QQ 群消息**：NapCat 的 `onebot11_*.json` 里配了 websocketClient
  `ws://127.0.0.1:6199/ws`（name=astrbot），所以群消息会同时到 qq-bridge（3001）和 AstrBot（6199）——
  插件的指令因此能触发。核对方法：`netstat -ano | grep :6199` 要有 ESTABLISHED，
  且 `logs/astrbot.log` 里能看到 `[napcat-qq(aiocqhttp)] ...` 的实时消息行。

## 直接查（回合里自己用，不经过 AstrBot 插件）

有人问「视奸 / 我在干嘛 / 主人现在在做什么」时，直接打后端公开读接口（无需 token；loopback 记得 `--noproxy '*'`）：

```bash
curl -s --noproxy '*' http://127.0.0.1:3000/api/current
# → {devices:[{device_name,app_name,status_text,is_online,last_seen_at}],recent_activities:[…]}
curl -s --noproxy '*' "http://127.0.0.1:3000/api/timeline?date=YYYY-MM-DD"
# → {segments:[{started_at,ended_at,app_name,status_text,duration_minutes}],summary:{按 App 的分钟数}}
```

- `app_name`/`status_text`＝那台电脑的前台应用＋卖萌状态文案（如「正在看任务管理器喵~」；离开时「暂时离开了喵~」）。报给用户时**口语转述**，别贴 JSON。
- timeline 的 `date=` **必填**（缺了报 `date parameter required`）；`segments` 是全天 1 分钟一段、很长，**看尾部**才是最近活动；`summary` 可用来算「今天玩了多久游戏」。
- 网页版 `http://127.0.0.1:3000`；局域网 `http://<电脑IP>:3000`（手机端一节有隐私提醒）。

## 手机端（含 iPhone）

- **平台矩阵：只有 windows / macOS / linux / android，没有 iOS。** 上游 issue 里维护者说得明确：
  iOS 沙箱不允许任何第三方 App 读前台应用，**上报「正在用什么 App」在 iPhone 上永远做不到**（任何方案
  都绕不开，不是技术难题）。别去给 iPhone 找"装个 App 就行"的路子。
- **iPhone 只能走健康数据这条路**：App Store 装 `Health Auto Export`，建一条 REST API 自动化，
  `POST http://<电脑IP>:3000/api/health-webhook`，头带 `Authorization: Bearer <该设备的 DEVICE_TOKEN>`，
  指标映射（心率/步数/睡眠/血氧…）由服务端自动识别，单位自动换算。本机 `REQUIRE_EXPLICIT_CONSENT` 未开
  → 不需要先做 consent 就能直接入库。两个未被验证的卡点，提前告诉用户而不是事后猜：iOS 的 ATS 可能拦
  `http://` 明文请求（被拦就得配 https 隧道）；Health Auto Export 的 REST 自动化可能部分要付费。
- **手机看面板不需要任何配置**：服务端绑 `0.0.0.0`（本机防火墙三个档全关），同一 WiFi 下直接开
  `http://<电脑IP>:3000` 即可；给用户生成该地址的二维码让他扫，比让他手敲 IP 强。静态导出天然自适应
  手机（已按 390×844 验过单栏排版）。
- **隐私提醒**：正因为是 `0.0.0.0` + 关防火墙，同一局域网里任何人都能打开这个面板——用户问起或者在公共
  WiFi 下要主动提，并给出「改绑 127.0.0.1」或「走隧道」两个选项。
