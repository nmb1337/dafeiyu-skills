---
name: windows-local-app-setup
description: "Use when installing a self-hosted app on this Windows host."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [windows]
metadata:
  hermes:
    tags: [windows, install, self-hosted, uv, pm2, services, gpu]
---

# Windows 本机自托管应用：安装与运行

## When to Use

- 用户说「装一下 X / 把 X 跑起来 / 给我一个面板」—— 第三方应用要装到本机长期跑
- 需要给本机服务换端口、用 pm2 / wscript 常驻、登记到看护脚本时
- 登录自托管面板、首次建管理员账号、要凭据时

适用于「把第三方应用装到本机长期跑」这类任务（监控面板、TTS/视频模型、记忆层、浏览器 agent…）。目标不是装完就完，而是**跑起来、能被验证、挂了能自愈**。

## 0. 先侦察（每次必做）

- 运行时：`docker`（本机没有）、`node -v`、`npm -v`、`uv --version`、`git --version`、`df -h /c`
- GPU：`nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv,noheader`
- **端口地图（装前必查冲突）**：3001 NapCat OneBot WS、3002 Uptime Kuma、6099 NapCat 面板、6185/6199 AstrBot、8642 Hermes api_server、8788 闲鱼监控、8790 QQ 桥接、9880 GPT-SoVITS api。新服务一律改到空端口：`netstat -ano | grep ":<port> " | grep -i listening`。撞端口的后果是服务起不来或把别人的链路打挂。
- **本机 shell 有 `HTTP(S)_PROXY=http://127.0.0.1:7890`**：探测本机端口必须 `curl --noproxy '*'`，否则得到 502 —— 那不是服务坏了。国内源（modelscope.cn 等）也加 `--noproxy '*'` 直连更快。
- 目录约定：第三方应用放 `C:\Users\32672\Apps\<name>`。

## 1. Python 应用：用 uv，不要动系统 python

- 没有 conda、没有系统 python3（PATH 上的 `python` 是 Hermes 自带 3.14，通常太新）→ `uv python install 3.12`，再 `uv venv --python 3.12 .venv`，装包统一 `uv pip install --python .venv/Scripts/python.exe ...`。
- 版本按仓库文档的「已测试环境」选（torch/torchaudio 尤其，见 `references/windows-build-pitfalls.md`）。
- 仓库自带 `install.sh` / `install.ps1`：**即使不直接跑它，也先读它** —— 里面写着模型下载 URL、解压目标目录、ffmpeg 放置位置、按设备选哪个 CUDA index。用 curl/uv 复现它的步骤，比翻文档快得多。

## 2. Node 应用：pm2 常驻，别手拼 VBS/cmd

- `npm ci --omit dev --no-audit` → 有的项目还要 `npm run download-dist` 拿前端产物（不必本地 build）。
- 后台常驻用官方推荐的 **pm2**：`pm2 start "<入口绝对路径>" --name <n> --cwd "<dir>"`，非默认端口用环境变量（如 `UPTIME_KUMA_PORT=3002`），最后 `pm2 save`。
- **浅克隆（`--depth 1`）会让仓库自带脚本里的 `git checkout <tag>` 失败**：要么 `git fetch --depth 1 origin refs/tags/<tag>:refs/tags/<tag>` 再 checkout，要么直接 `git clone --branch <tag>`。
- 自写 VBS 启动器只在 pm2/服务方式都不行时才用；**VBS 文件里不要出现中文**（WSH 按 ANSI 读，某些汉字的字节序列会吃掉引号，报「未结束的字符串常量」），而且 `sh.Run` 手拼 cmd 引号很脆。
- **写这些含 Windows 路径的启动/配置壳时，不要用 shell 的 heredoc**：`printf` 会把路径里的 `\U...` 当转义序列吃掉（`C:\Users` 直接烂成 `C:\Users?72`，脚本静默失效），`python - <<EOF` 里的 `C:\Users` 又会报 `unicodeescape` 语法错误。改成把生成脚本写成文件再跑、或直接用 `patch` 工具改那几个字——尤其是 Startup 目录下的包装脚本，它们只在重启时才被用到，写坏了你当场看不到。
- 启动器要**自己会报错**：它依赖的东西（pm2、某个 exe、某个 venv）不在了就打印错误并非零退出，而不是静默什么都不做——否则故障要等到用户重启才发现。

## 3. 缺编译器/缺资源：绕过去，别下几个 G 的构建工具

细节见 `references/windows-build-pitfalls.md`（MSVC 缺失的包、torchcodec 无 Windows 版、垫片包写法、nltk_data 放置）。

## 4. 首次建管理员账号 / 登录自托管面板

- **用户名（标识符）我自己填；密码永远不经过我**：凭据先入保险箱，再用 `browser_vault_fill`。
- 保险箱条目的 **origin 必须与页面一字不差**（`http://127.0.0.1:3002` ≠ `https://127.0.0.1:3002`），否则 `origin_mismatch` 直接拒填。录入时极易被自动补成 https，提醒用户改掉那几个字母。
- 聊天平台会话里 `browser_vault_save_login` 的遮罩弹窗**不可用**（`prompt_unavailable`）→ 让用户自己跑 `hermes vault add`（或桌面版：设置 → 密码与登录），或让他在页面上手输一次。**不要**为了「帮到底」把密码写进命令行、脚本或 chat。
- 首次向导某个按钮点了没反应时：**读服务端源码找它调的接口**，直接 `curl` 调。例：Uptime Kuma 选库卡住 → `curl -X POST http://127.0.0.1:<p>/setup-database -H 'Content-Type: application/json' -d '{"dbConfig":{"type":"sqlite"}}'`（它随后写 db-config.json 并切到建号页）。
- 表单里的 401/404 端点别当健康检查：先 `curl` 找返回 200 的路径（例：Hermes api_server 用 `/health`，`/` 是 404）。

## 5. 自动化配置自托管面板（Vue 表单）

- Vue 绑定的 input 直接 `el.value = x` 不生效，要用**原生 setter + 派发事件**：
  ```js
  const set=(sel,val)=>{const el=document.querySelector(sel);
    Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value').set.call(el,val);
    el.dispatchEvent(new Event('input',{bubbles:true}));
    el.dispatchEvent(new Event('change',{bubbles:true}));};
  ```
  （TEXTAREA 换成 `HTMLTextAreaElement.prototype`。）
- 页面里同名按钮常有多个（各模态框一个）：用 `x.offsetParent` 过滤出**可见**那个，再按 `getBoundingClientRect()` 取中心点击。
- 路由一般可直达（如 Uptime Kuma 的 `/add` 新建、`/edit/<id>` 编辑），比点菜单稳。
- 模态框底部的按钮常在视口之外（`getBoundingClientRect().y > window.innerHeight`）：先 `el.scrollIntoView({block:'center'})` 再取中心坐标点击，否则点空、且看不出错。
- **点完「保存」一定要回读验证**（读应用自己的库或接口确认写进去了）。若界面填好、点保存无报错、弹窗不关、库里仍是 0 行 —— 别再反复试点，说明这条保存走的不是普通 HTTP 表单（例如只走 socket.io）；**停服 → 服务端直接写（DB/API）→ 起服 → 回读核对**。Uptime Kuma 的通知就是这样，细节见 `references/selfhosted-alerting.md`。

## 6. 收尾：验证 + 脱离 gateway + 登记看护

- 装完必须**用真请求验证**：端口在听 + HTTP 状态码 + 真实产物（音频/数据）。安装退出码 0 不算数。
- 长期服务要**脱离 Hermes gateway 进程树**（gateway 重启会把子进程连坐杀死）——pm2 或 wscript 独立拉起。
- 登记到已有看护脚本 `scripts/qq-bridge-watchdog.py` 的 `SERVICES` 列表，新服务/端口都要加一条，否则挂了没人拉；`launcher` 用**纯 ASCII 的 VBS**（见 §2），加完跑一次 `python scripts/qq-bridge-watchdog.py` 自测（全在听时应无动作、退出 0）。
- 服务状态要能**推给用户**，不能只躺在面板里：告警链路（面板 webhook → 本机转发器 → `hermes send`）见 `references/selfhosted-alerting.md`。
- 用户很在意电费和内存：**重量级的模型服务（TTS/视频）用完就停**，停完把释放的内存/显存报给他（例：GPT-SoVITS 停掉省 ~3.7G 内存 + ~1.4G 显存），同时留一个单实例 `start-api.bat`（纯 ASCII）供随时拉起。
- **手动拉起已装好的服务（用户说「把 X 打开 / 把 X 跑起来」）**：不要在 terminal 前台直接跑它——前台命令一旦被工具超时杀掉，服务跟着那个进程树一起死，端口回空，看起来像「打开了但什么都没在听」。用 `Start-Process … -WindowStyle Hidden -RedirectStandardOutput/-Error` 分离拉起；注意这种调用**本身可能一直挂着不返回**（重定向句柄不放），所以「拉起」和「验证」分成两次调用：先拉起就结束，再单跑 `netstat -ano | grep ':PORT .*LISTENING'` + `curl -s --noproxy '*' http://127.0.0.1:PORT/` 确认。
- **服务在听 ≠ 它在干活**：面板型服务往往有独立的「任务运行中」状态，光起 web 进程它什么都不扫。拉起后还要按它的控制接口显式启动，再读 status/health 确认在跑（例：闲鱼监控只起 `src/server.js` 时 `/api/status` 是 `running:false` +「监控尚未启动」，要 `POST /api/monitor/start` 才开始扫描；端口 + HTTP 200 都正常也不代表任务在跑）。

## 7. 重启/掉电后的自启体检（用户重启后主动跑）

用户说「我刚重启了电脑」时，不要只 ping 自己那几个服务——**按"开机后还能不能自己回来"逐项核**：

1. **端口体检**：把全部服务端口过一遍（网闸、Hermes 网关、桥接、AstrBot、Kuma、监控、模型服务），标出 ❌。
2. **自启清单 vs 端口**：把 Startup 文件夹和计划任务（`Get-ScheduledTask`）逐条列出来，再对照实际在跑的东西——**缺一项就是重启后会静默缺席的那一项**（本机就踩过：NapCat、Kuma 面板、告警转发三项根本没有自启项）。
3. **启动器不能用可选工具做前置**：面板原先靠 pm2 拉起，而 pm2 已经从本机消失 → 重启后永远起不来。启动器要绕过中间层，**直接调应用自己的运行时**（例：`node <app>\server\server.js`）。
   - 补自启项时**两件东西都要真建出来**：Startup 里的包装脚本 + 它指向的 `gateway-service\<X>.vbs`。只写包装脚本、被指向的启动器不存在，重启后还是静默不起——写完两个文件后**当场执行一次启动器**，看端口有没有起来。
4. **常驻服务必须显式给端口**：Uptime Kuma 不带 `UPTIME_KUMA_PORT` 就默认去听 **3001**，正好撞 NapCat 的 OneBot WS（`EADDRINUSE` 当场退出）→ 启动器里写死端口，并在 §0 的端口地图上先确认。
5. **有些服务重启后必须要人**：QQ 客户端（注入式）需要扫码登录；这类服务的自启只能把它抬到登录界面，你要把"等登录"这个状态指出来（扫码图的位置：`NapCat.Shell/cache/qrcode.png` 变新 = 在等扫码；它的面板端口活着而业务端口不监听 = 没登录，不是配置坏了）。
6. **修完立刻提交 + 写 PROGRESS**，并且当场验证一次（重启后端口全绿、桥接的事件流 `ws_connected: true`）。

## 报进度的话术（用户偏好）

大白话、先结论后细节；说清「我踩了什么坑 + 怎么修的 + 现在状态」，并把**真实验证输出**贴出来（几行就够）。别只报「已安装成功」。
