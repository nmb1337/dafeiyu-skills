# Onboarding a second person (client / family) onto one Hermes install

场景：主人要把**别人的** QQ + 微信接进自己这台机器，对方要能用主人同款的功能（聊天、点歌、画图），但不能碰主人的电脑。

## 平台事实（官方文档 + 本机实测）

- **多档案网关**：`gateway.multiplex_profiles: true`（默认开）时，默认网关枚举 `profiles/` 下每个档案，**按各档案自己的凭证**启动各自的平台适配器，入站消息路由到对应档案；HTTP 平台走 `/p/<profile>/`。每个档案有自己的 `.env / skills / memory / SOUL / 模型密钥`。
- **同一个 bot token 不能被两个档案同时轮询** → 对方必须有**他自己的**机器人身份（微信要他自己扫码）。
- **微信 = iLink 机器人**：绑定的是对方微信下的 bot 身份，**收不到普通群消息，只能私聊**——先把这条告诉客户，别让他在群里找机器人。
- **QQ = NapCat/OneBot 外挂桥接**：一个 QQ 号 = 一个 QQ 客户端实例 + 一个 NapCat；配置按 uin 分文件（`onebot11_<uin>.json`），端口必须全部错开（见下）。官方 Windows 可视化工具宣称支持多账户；否则复制一份 NapCat.Shell 各管各的。
- **点歌/画图不是 Hermes 工具**，是桥接调本机共享服务（sing_service / ComfyUI 8189）→ 对方档案 **不需要 terminal/file 工具**也能有这些功能。这是「功能全给、电脑碰不到」的关键分界线。

## 步骤

1. **建档案**：`hermes profile create client1 --clone`（带模型密钥/SOUL/skills，**不带**消息平台 token）。收窄 Hermes 工具面：`hermes -p client1 config set platform_toolsets.api_server '["web"]'`；删掉克隆来的 MCP 服务器（`hermes -p client1 mcp remove …`）——MCP 工具会注入每个平台工具集，不删等于没限权。
   - **每个要用的平台都得单独收窄**：只设了 `api_server` 的档案一旦接上微信，微信私聊仍拿全量工具（terminal/file 都在）。同一条命令再设一遍该平台的键（`platform_toolsets.weixin '["web"]'`，键名对着 `config.yaml` 里现有 `platform_toolsets` 段的平台 slug 写）。
   - **`--clone` 会把主人的 `memories/MEMORY.md`、`USER.md` 一起复制过去**（里面是主人的私事和本机路径）。给客户/外人的档案要清空这两份，否则对方一句「你还记得什么」就能把主人的事读出来。
   - **克隆的 `skills/` 整棵树也会带过去**，包括描述主人桥接/NapCat 端口/AstrBot 的运维技能——客户 agent 一旦有 file 工具，这些技能就是绕过权限的说明书（实测：客户的微信 bot 照着桥接技能找到 8790/3001，改了主人的 `scripts/qq-bridge.py`，再用主人的号往主人群里发消息）。接微信/QQ 前把 `onebot-qq-bridge`、`hermes-messaging-gateway`、`astrbot-plugin-ops`、`github-qq-notify`、`hermes-model-tuning` 这类运维技能从对方档案的 skills 目录删掉。
   - **`--clone` 也把主人的 provider API key 原样复制过去**（`DEEPSEEK_API_KEY`、`HERMES_CUSTOM_*_API_KEY` 等）→ 客户的每一句都记到主人账上。建档后立即从新档 `.env` 删掉这些 key（保留 `API_SERVER_KEY`、`NO_PROXY`、终端/浏览器类配置），换上**客户自己的** key；用户会直接问「API 能用他自己的吗」。换完用 `hermes -p <profile> -z "只回复四个字：接入成功"` 冒烟一次——它同时验证新 key 可用与账单归属。
   - 客户 key 到手先验真伪再写回：DeepSeek 用 `curl -s --noproxy '*' https://api.deepseek.com/user/balance -H "Authorization: Bearer <key>"`（返回 `is_available:true` + 余额，顺带知道客户充了多少钱）；写进 `.env` 后不回显、只报「已写入 + 掩码」。如果 key 是对方在聊天里贴出来的，交付时提醒他事后在控制台删掉重发一张（换 key 只需改 `.env`，不影响任何配置）。
2. **档案自己的 `.env` 必须有 `API_SERVER_KEY`**（multiplex 下 `/p/<profile>/` 的鉴权），否则 api_server 镜像拒绝该档案。
3. **微信**：在该档案下跑 weixin 扫码登录（setup wizard / adapter 的 `qr_login`，`hermes_home` 指向这个档案），**对方本人扫码**；凭证落进该档案 `.env`（`WEIXIN_ACCOUNT_ID` / `WEIXIN_TOKEN`）。启用该档案的 `platforms.weixin` → 网关重启后两套微信同时在线。人不在跟前、扫完就走的场景按 `qr-login-flows.md` §Hands-off finish 做（确认后自动写 `.env` + 重启，不用等下一轮对话）。
   - **扫码的实际跑法**：先找一个 `import aiohttp` 的运行时 venv——网关自己用的解释器不一定带 messaging 依赖：`for p in installs/*/environments/*/venv/Scripts/python.exe; do "$p" -c "import aiohttp" 2>/dev/null && echo "$p"; done`。**cwd 必须在 hermes-agent checkout 根目录**（否则 `import gateway.*` 解析不了），脚本用技能自带的 `scripts/capture_qr_login.py`（它在技能目录里，不在 checkout），并设 `HERMES_HOME=<该档案目录>`、适配器 `gateway.platforms.weixin:qr_login`。
   - **二维码只在对方准备好扫的时候生成**：有效期约 2 分钟，过期会自动刷新几次，整个进程在刷新预算（~7 分钟）用完后就退出了——提前生成的码等人来扫是白忙。过期就重跑一次拿新码，别复用旧图。客户不在本机时，把这个实例的 WebUI 经 Cloudflare 快速隧道交给他自己扫（一条 `/webui?token=<token>` 链接，token 在副本的 `config/webui.json`）；隧道是一次性的、重启会变，发之前先 `curl` 验 200，且要提醒他别用电脑端 QQ 的登录窗（那会列出这台机器保存的其他账号）。
   -   - 确认成功后检查 `profiles/<name>/weixin/accounts/<id>.json` 已生成（adapter 自己写的，不要手写）——**这个 JSON 只有 `token/base_url/user_id/saved_at`，没有 account_id，id 就是文件名**；写 `.env` 时三件套一起写：`WEIXIN_ACCOUNT_ID=<文件名>`、`WEIXIN_TOKEN=<json.token>`、`WEIXIN_BASE_URL=<json.base_url>`（只写 id 会看到 `[MULTIPLEX] Profile '<p>': skipping weixin - no bot credential in this profile's secrets`）。写完把扫码临时目录整个删掉（`login_result.json` 里是凭据）。
4. **授权对方的微信（pairing 流）**：默认 `dm_policy` 是 `pairing`——对方第一条私聊不会进 agent，而是收到一条英文提示 + 配对码（`Your pairing code: XXXXXXXX`，1 小时有效）。在本机跑 `hermes -p <profile> pairing approve weixin <CODE>`，然后让对方**再发一次**消息（首条已被配对流程消费）。`hermes -p <profile> pairing list` 核对已授权用户；`pairing clear-pending` 清待处理。想改成白名单：把对方 sender id 写进该档案 `.env` 的 `WEIXIN_ALLOWED_USERS`、`WEIXIN_DM_POLICY=allowlist`，再重启。**不要用 `dm_policy: open`**（没有 `GATEWAY_ALLOW_ALL_USERS=true` 会拒绝启动网关，开了又等于对全网开放）。
   - 用户 id 从 `pairing list` 或 `gateway.log` 的配对/inbound 行取（形如 `<hash>@im.wechat`）；别把扫码返回的 bot 身份（`<hash>@im.bot`）当用户 id。
5. **QQ**：第二套 QQ 客户端实例 + 第二套 NapCat。端口错开示例：OneBot WS `3011`（原 3001）、WebUI `6100`（原 6099）、第二桥接 `8791`（原 8790）。`onebot11_<对方uin>.json` 里 `websocketServers` 开 3011。
   - **做法**：`robocopy` 一份 QQNT 安装目录 + 一份 NapCat.Shell 到独立目录；启动器（纯 ASCII cmd）里 `NAPCAT_*` 五个变量全指向副本自身，`QQPath` 指向副本的 `QQ.exe`，并加 `--user-data-dir="<副本目录>\data"`；`config/webui.json` 改端口 6100。
   - **复制来的 `loadNapCat.js` 是坑**：它只有一行 `await import("file:///C:/…/NapCat.Shell/napcat.mjs")`，**绝对路径写死指向原版**——不改的话第二实例实际跑的是原版代码，二维码/缓存/配置全写进原版目录（实测日志 `二维码已保存到 …Downloads\NapCat.Shell\cache\qrcode.png`）。改成副本自己的 `napcat.mjs` 路径，之后日志里的路径应变成副本目录，才算真隔离。
   - **QQNT 默认 profile 是 `%APPDATA%\Roaming\QQ`，副本不传 `--user-data-dir` 时两个实例共用它**：第二个实例登录另一个号会把原机器人踢下线——实测原实例的 6099 和 3001 同时消失。启动器必须给副本传自己的 `data` 目录（副本目录下会生成），并以进程 CommandLine 核实参数真的到了 QQ；验收一律用 `CheckLoginStatus`/`get_login_info` 的真实 uin，不看登录窗口列了哪些号。第二实例每次登录/重启后都要复查原机器人；恢复 = `taskkill /F /IM QQ.exe` → `explorer.exe NapCat.vbs` → WebUI 快捷登录（别在机器人正回消息时全杀 QQ）。
   - **第二实例的登录态不保证跨重启保留**：重启后 WebUI 的快捷登录列表里可能没有对方的 uin（实测只列出老账号），只能让对方重扫。所以 `onebot11_<uin>.json` 要在扫码**之前**配好（登录时加载），避免「登录→改配置→重启→又要重扫」的死循环。
6. **第二桥接**：`qq-bridge.py` 现在支持 `QQ_BRIDGE_ID=<id>` 环境变量——设置后配置读 `$HERMES_HOME/qq_bridge_<id>.json`、会话表写 `qq_bridge_sessions_<id>.json`（不设则用原来的 `qq_bridge.json` / `qq_bridge_sessions.json`）。第二份配置：`listen_port=8791`、`napcat_ws="ws://127.0.0.1:3011"`、`bot_uin=<对方uin>`、`owner_qq=[]`、`guest_profile="client1"` → 所有发送者都路由到 `/p/client1`。
   - **必须设 `send_via_napcat: true`**：文本回复默认走 AstrBot OpenAPI（`astrbot_bot_id`/6185 = 绑死原机器人号），第二实例不设这个开关就会用**原机器人的身份**回客户的消息。开着它后文本走本实例的 NapCat WS（`send_private_msg`/`send_group_msg`）；再把 `astrbot_base_url` 留空关掉回退（语音/图片/表情本来就直走 NapCat）。
   - 启动后先验 `/health`（8791）：`ws_connected: true` 且 `bot_uin` = 对方 uin，再发一条真实私聊回读。唱歌/画图沿用同一套本机服务（共享 GPU，任务串行执行）。
7. **验收**：对方微信私聊 → `gateway.log` 出现该档案的 inbound + 回复；对方 QQ 私聊 → 第二桥接 `[recv]/[send]` + 客户端收到；点歌、画图各跑一次；确认 client1 的工具集里没有 terminal/file（实际调不动主人机器）。**逐个平台查工具集**：`hermes -p <p> config get platform_toolsets` 里 `api_server`、`weixin`（以及任何已启用的平台）都必须是收窄后的列表——收窄只对写过的那个键生效，只设了 `api_server` 就接微信，微信侧仍拿全量工具（terminal/file 都在）。
   - 档案建好后 `hermes gateway status` 会立刻列出 `<profile>/api_server: http://127.0.0.1:8642/p/<profile>/v1`——HTTP 路由不需重启就生效，可直接当「档案已被网关接纳」的证据；平台适配器（微信/QQ）才需要重启。
8. **交付说明里写清风险**：对方账号登录在主人机器上（消息全文经过、隐私与责任在主人）；NapCat 是第三方注入，有封号风险（微信官方通道没有）；8GB 显卡上主人和对方同时点歌/画图会互相拖慢；唱歌默认用主人的克隆嗓——要对方自己的声音须另训一套 GPT-SoVITS 音色。

## 客户自助权限（改人设 / 加技能，但碰不到电脑）

（默认建议：不给 `file`/`terminal`/`code_execution`，用下面的「窄工具集 + 沙盒 MCP」。如果主人明确要求开放全部工具，见下一节。）

客户要「能改自己人设、能加新功能」时，别给 `file` / `terminal` / `code_execution`：那等于把整台机器交出去。`HERMES_WRITE_SAFE_ROOT` 也救不了——它是**进程级环境变量**，multiplex 下所有档案共用一个网关进程，给客户设了会连主人的微信 agent 一起限死。正确形状是「窄工具集 + 无路径参数的沙盒 MCP」：

- **工具集**：`hermes -p <p> config set platform_toolsets.api_server '["web","skills","memory"]'`。`skills` 工具集（skill_view/skill_manage）天然只写**本档案**的 `skills/` 目录 → 这就是「加新功能」的安全实现；`memory` 同理只写本档案。
- **沙盒 MCP**（本机实例：`C:\Users\32672\Apps\mcp-client-admin\server.py`）：FastMCP 写 6 个工具——`read_persona` / `write_persona(content)` / `list_skills` / `read_skill(name)` / `create_skill(name, description, body)` / `profile_info`。**关键：所有路径硬编码在档案目录内，工具参数里没有任何路径成分**，技能名用 `^[a-z0-9][a-z0-9_-]{0,63}$` 校验 + realpath 前缀校验——结构上写不到别处。人设写入先备份（`SOUL.md.bak.<ts>`），限 50~20000 字符。
- **解释器要真的有 `mcp` 包**：Hermes 自带的 tools python 没有；用专门的 venv（本机 `Apps\mcp-local\.venv\Scripts\python.exe`）。注册：`printf 'Y\n' | hermes -p <p> mcp add client_admin --command "<python>" --args "<server.py>"`（交互确认要管道喂 Y，`--args` 必须放最后）。MCP 配置逐档案，客户档案的 server 不会出现在主人档案里。
- **人设里要教它怎么用**：往该档案 `SOUL.md` 追加一节「客户特权」——改人设=先 read 再整体 write；加功能=create_skill；红线=删文件/格式化/装软件一律拒绝。工具存在不代表模型知道何时该用。
- **生效时机**：人设和技能都只在**新会话**生效（系统提示在会话创建时固化）→ 改完让客户发 `/new`（或我们清会话）；新 MCP 工具用 `/reload-mcp` 或新会话。
- 验收：`hermes -p <p> -z "调用 profile_info 工具，原样输出返回内容"`——返回档案信息即工具链通（顺带验证客户 key 计费正常）。

## 主人坚持给客户开 terminal / file / code_execution 时

先说清结构限制：**同一个 Windows 账号下做不到硬隔离**。`terminal` 能读 `.env`、config、`scripts/`；`code_execution` 直接在网关进程里跑，能读整个 `os.environ`（所有 provider key、平台 token）；`HERMES_WRITE_SAFE_ROOT` 是进程级环境变量，multiplex 下会连主人档案一起限死，不能当客户专用护栏。能做的是把事故面收窄，并在交付时明说这是「软隔离」：

1. **逐平台设同一套工具集**（`platform_toolsets.weixin` 与 `.api_server` 都设），并用 `hermes -p <p> config get platform_toolsets` 确认没有别的平台键留空吃默认全量。
2. **删运维技能 + 人设写死红线**：只准操作自己的号（QQ/微信 bot）和自己的档案目录；禁止连接 3001/8790/6185、禁止改 `scripts/`、`profiles/default/`、`profiles/qqguest/`；群功能只作用于自己机器人所在的群。红线写在 `SOUL.md`（新会话生效）。
3. **共享桥接里新功能默认关**：客户写进 `qq-bridge.py` 的功能（如群聊自由接话）在 `DEFAULTS` 和每个 `.get(..., False)` 兜底里都必须是 False，只在它自己的 `qq_bridge_<id>.json` 里开；用 `git diff` 审它的改动、`agentlock.py status` 看它拿的租约（`release <lock_id>`）、审完再 commit。
4. **客户桥接必须只用自己的号发**：`send_via_napcat: true` + `astrbot_base_url` 留空（否则回退到绑定原机器人的 AstrBot）。
5. **改完让客户发 `/new`**：老会话的系统提示和工具集都是建会话时固化的，不发 `/new` 会看到「新工具没有」「人设没变」。
6. **定期审计**：`git -C scripts status/diff`、`agentlock.py status`、NapCat 日志里是否有不属于主人的发送。要真隔离只能上 Docker/VM/独立 Windows 用户（本机 docker 未安装）。

## 多个客户复用（client2、client3…）

- **端口顺延表**：主人 6099/3001/8790；client1 6100/3011/8791；client2 **6102**/3013/8792（6101 被 QQ 本身占用，别选）。每加一个客户顺延一组，定之前先 `netstat` 探一遍。
- **沙盒 MCP 用环境变量指向档案**，一份 `server.py` 服务所有客户：注册时 `--env "CLIENT_PROFILE=<…>/profiles/clientN"`，代码里 `os.environ.get("CLIENT_PROFILE")` 兜底最早那个档案；命令 `printf 'Y\n' | hermes -p clientN mcp add client_admin --command "<mcp venv python>" --env "CLIENT_PROFILE=…" --args "<server.py>"`（`--args` 永远最后）。
- **克隆会连主人的 MCP 一起带过来**：`vscode`（指向主人的编辑器）、`playwright`（复用主人的浏览器会话）必须从客户档案删掉；`sqlite/ffmpeg/context7/deepwiki` 这四个就是「系统 MCP」的合理含义。`hermes -p <p> mcp list` 核对——**这一步容易漏**：克隆出来的 `mcp_servers` 看着已经有一堆，实际全是主人的。
- **新客户的 QQ 号在扫码前未知**：启动器要能无快登启动（`if "%NAPCAT_QUICK_ACCOUNT%"==""` 时不传 `-q`）。把上一个客户的 uin 当占位留在启动器里，等于把别人的号登进新副本。而且新号第一次登录后 NapCat 才生成 `onebot11_<uin>.json`（空的 `websocketServers`，只在启动时读、不热加载），改完要重启实例 → 登录态掉 → 再扫一次；扫码前就把「要扫两次」告诉客户。
- **每个客户一套 Startup 项**：`QQ_ClientN_AutoStart.vbs` + `QQ_ClientN_Bridge_AutoStart.vbs`，各自指向自己的启动器。
- **SOUL 模板复用**：复制上一个客户的 `SOUL.md` 后 `sed` 把旧 QQ 号/微信 bot id 换成本客户的，并把 `profiles/client1/` 改成 `profiles/clientN/`——漏改路径会让客户的红线指向别人的档案。
- **每个客户一套模型 key**：拿到先打 `/user/balance` 验余额再写 `.env`（`is_available:false` + `0.00` 的 key 写进去也没用，冒烟会回 `Add credits`）。
- **复制来的 NapCat 副本带着上一个客户的凭据，先清再换**：`config/passkey.json` 是登录态，`napcat_<uin>.json` / `onebot11_<uin>.json` 是账号配置（复制时会把上一家的 uin 一起带过来）——启动前把这些删掉，否则新客户的实例沿用别人的登录态/端口配置。再给副本 `config/webui.json` 换一个**全新的 token**（如 `secrets.token_hex(16)`，32 位十六进制；WebUI 登录 hash 仍是 `sha256(token + '.napcat')`），不要把上一个客户的 token 原样复制过去。
- **克隆出来的 `mcp add` 会「Cancelled.」**：sqlite/ffmpeg 这类已经在克隆配置里的服务器，重新 add 时确认提示不是 Enable-all，管道喂 Y 也会被判为取消；先用 `mcp list` 看已有的，缺什么补什么，重复的直接跳过。

## 坑

- `--clone` 不含消息 token；`--clone-channels` 会复制 token，但 multiplex 活着时会被拒绝（token 撞车）。
- 每个档案的微信身份必须不同，否则第二个 adapter 起不来；`WEIXIN_ACCOUNT_ID` 与 token 要成对落进**该档案自己的** `.env`（没落进去会看到 `Skipping weixin on <profile>: no bot credential in this profile's secrets.`）。
- 微信 iLink 的能力边界要提前讲：群消息收不到；`WEIXIN_GROUP_POLICY` 设成非 `disabled` 只会在启动时打 WARNING，并不会让群消息真的送达。
- 别为了给「唱歌/画图」而放开 terminal——那两个功能在桥接里，放 terminal 只会让对方真的能碰这台电脑。
- **微信档案不会自动有点歌/画图**：这两个能力挂在 QQ 桥接（`_looks_like_song_request` / 生图派单）上，微信侧只有聊天 + 联网。向客户介绍功能时必须分开说，别承诺「微信里也能点歌」——要就得另接一条落到该档案的流水线。
- 客户 QQ 若想放到云机（不占主人电脑）：Linux 版 NapCat（Docker/AppImage）+ 桥接经隧道连它的 WS；2C2G 云机够跑 1 个 QQ，但唱歌/画图仍在主人 8GB 显卡上执行，两者别混为一谈。
- 先备份再测试：新档案第一次跑起来前，确认默认档案的网关没被这次改动影响（两个档案的适配器同进程共存，一个坏凭证不应拖垮另一个）。
- **远程 URL 型 MCP 在 `hermes mcp add` 的连接校验里可能挂几分钟**（context7/deepwiki 过代理时实测 300s 超时），`printf 'Y\n' |` 也救不了。先加 `--connect-timeout 10`；仍然挂就直接把 `context7:`/`deepwiki:` 两行写进该档案 `config.yaml` 的 `mcp_servers:` 段（子项缩进 2 空格、保留 CRLF），再用 `hermes -p <p> mcp list` 验证。本地 stdio MCP（sqlite/ffmpeg）一般秒过。
- **网关跑着的时候改 `config.yaml`/`.env` 会触发 `[MULTIPLEX] Re-scanned profile '<p>' after config/.env change (0 adapter(s) connected)`**——热重扫可能把该档案刚连上的适配器弄没；所有改动攒完只重启一次，重启后复查 `✓ <platform> connected (profile: <p>)` 还在。
- **`hermes gateway restart` 从桌面工具 shell 里跑可能报 `The process may have been created and then killed — e.g. by a parent Job Object` 并把网关停掉**：改用手动 `hermes gateway stop` + `explorer.exe "<Startup>\Hermes_Gateway.vbs"` 脱离启动，等 ~25 秒再用 `hermes gateway status` 和日志确认。

## 让每个微信指挥自己的 QQ 机器人

每个档案装同一个 `qq_admin` MCP，用 `--env QQ_NAPcat_WS` 指向**本实例**的 OneBot 端口；工具只有 `status / list_groups / list_friends / send_group / send_private`，作用域全部来自环境变量、没有任何 URL 参数——所以客户档案结构上够不到别人家的号：

- 注册（`--command` 必须是原生 `C:/...` 路径，`--args` 放最后）：
  `printf 'Y\n' | hermes -p clientN mcp add qq_admin --command "C:/Users/…/mcp-local/.venv/Scripts/python.exe" --env "QQ_NAPcat_WS=ws://127.0.0.1:3013" "QQ_LABEL=clientN机器人" --args "C:/Users/…/mcp-qq-admin/server.py"`
- 服务器用 `websockets` 直连 NapCat（连接时 `proxy=None`），所以那个 venv 必须有 `websockets`；发消息就是 `send_private_msg` / `send_group_msg` 加 text segment，不需要经过桥接。
- 人设（SOUL.md）里补一节：看状态 `status()`、看群 `list_groups()`、看好友 `list_friends()`、群里说话 `send_group(group_id, text)`、私聊 `send_private(user_id, text)`，并写死「只能操作自己的号」。
- 验收：`hermes -z "调用 status 工具…"` 报主人的号（1150111337）；`hermes -p clientN -z …` 报客户自己的 uin 或「未连接」——后者才是隔离生效的样子（对方 QQ 掉登录时「未连接」是正常态）。
- 现有微信会话要 `/new` 才加载新工具；新会话自动有。

## 守护：网关/桥接被外部停掉时自动拉起

网关会无声消失：`gateway.log` 末尾是 `Received UNKNOWN as a planned gateway stop — exiting cleanly`（parent_pid 不明），三个微信适配器同时断开，用户只会看到「微信都用不了了」；`hermes gateway status` → `No gateway process detected`，8642 不在听。

- 装一个每 5 分钟的计划任务兜底：`schtasks /Create /SC MINUTE /MO 5 /TN HermesWatchdog /TR "<…>\scripts\gateway-watch.cmd" /F`。
- 脚本逻辑：按 CommandLine 含 `*gateway run*` 判断网关是否存活，缺了才 `Start-Process wscript.exe "<Startup>\Hermes_Gateway.vbs"`；然后 `Test-NetConnection 127.0.0.1 -Port 8790/8791/8792`，哪个不在听就启动对应桥接的 VBS。缺了才启动 = 健康时反复运行也不会叠进程。
- 验证：健康状态下手动 `schtasks /Run` 一次，网关/桥接进程数必须不变；`Get-ScheduledTaskInfo` 的 `LastTaskResult` 为 0。
- 分清影响面：网关挂 = 所有微信断；桥接挂 = 只有那个 QQ 机器人不回。两套都要看。
