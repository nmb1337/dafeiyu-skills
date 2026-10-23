# 第二套 QQ 实例（NapCat 多账号 / 客户二号）· Windows 实测配方

一个 QQ 号 = 一个 QQ 客户端进程 + 一份 NapCat.Shell。NapCat 官方不做单实例多账号（issue #741/#743），
两个号同时在线 = 两套实例，端口全部错开。以下是本机实测路径与核对项。

## 端口规划

| 用途 | 第一套（机器人，如 1150111337） | 第二套（客户号） |
|---|---|---|
| OneBot WS | 3001 | 3011 |
| NapCat WebUI | 6099 | 6100 |
| 桥接 | 8790 | 8791 |

## 步骤

1. **复制 QQ 客户端**（约 1.2 GB）——同一 exe 再启动只会激活原窗口，必须换目录才能起第二个客户端：
   `robocopy "C:\Program Files\Tencent\QQNT" "C:\Users\<u>\Apps\QQ-client1\QQNT" /E /NFL /NDL /NJH /NJS /NP`
   （robocopy 退出码 0–7 都算成功。）
2. **复制 NapCat.Shell**（约 112 MB）到 `C:\Users\<u>\Apps\NapCat-client1`。
3. **改副本的 `loadNapCat.js`** —— 全文只有一行，硬编码着原目录：
   `(async () => {await import("file:///C:/…/原目录/napcat.mjs")})()`
   改成副本自己的 `napcat.mjs`。不改的话副本加载的是**原版 NapCat 代码**：二维码写回原目录、配置也混在一起。
4. **改副本 WebUI 端口**：副本 `config/webui.json` 顶层 `port` 6099 → 6100（该 json 有十来 KB，只改 `port` 一个键）。
5. **写启动器**（纯 ASCII `.cmd`，见主 SKILL 的「.cmd 必须纯 ASCII」）：
   ```bat
   set "NAPCAT_PATCH_PACKAGE=%cd%\qqnt.json"
   set "NAPCAT_LOAD_PATH=%cd%\loadNapCat.js"
   set "NAPCAT_INJECT_PATH=%cd%\NapCatWinBootHook.dll"
   set "NAPCAT_LAUNCHER_PATH=%cd%\NapCatWinBootMain.exe"
   set "NAPCAT_MAIN_PATH=%cd%\napcat.mjs"
   set "QQPath=C:\Users\<u>\Apps\QQ-client1\QQNT\QQ.exe"
   "%NAPCAT_LAUNCHER_PATH%" "%QQPath%" "%NAPCAT_INJECT_PATH%" --user-data-dir="C:\Users\<u>\Apps\QQ-client1\data"
   ```
6. **隐藏启动**：vbs → `cmd /c start_client1.cmd > client1-boot.log 2>&1`，用 `explorer.exe` 交给 shell；不要在同一次工具调用里等它（boot main 会一直挂着）。
7. **启动后核对（缺一不可）**：
   - 副本进程 CommandLine 里是 `--user-data-dir=C:\…\Apps\QQ-client1\data`；
   - 新二维码写在副本 `cache/qrcode.png`（不是原目录）；
   - 副本 WebUI 6100 能应答（用副本 `webui.json` 的 token 算 `hash=sha256(token+'.napcat')` 调 `/api/auth/login`）；
   - **机器人本体的 6099 / 3001 仍然正常**（关键回归项）。
   —— 四项全过才让客户扫码登录。
8. 客户扫码登录后：从副本 WebUI 拿 uin → 建副本 `config/onebot11_<uin>.json`（照第一套的结构，websocketServers 开 3011，HTTP client 指向第二桥接）→ 重启副本实例 → 第二桥接连 `ws://127.0.0.1:3011`。

## 坑

- **不隔离 `--user-data-dir` 会踢掉正在跑的机器人**：QQNT 默认 profile = `%APPDATA%\Roaming\QQ`，两个客户端共用同一会话目录 → 机器人 QQ 被顶下线，6099 和 3001 一起消失（桥接 `ws_connected:false`）。恢复：`taskkill /F /IM QQ.exe` → `explorer.exe …\gateway-service\NapCat.vbs` → WebUI 快捷登录机器人 uin。这个代价是实测的，不是理论风险。
- `--user-data-dir` 是否被 QQ 接受要以副本进程的 CommandLine 为准：仍显示 `AppData\Roaming\QQ` 就是没生效——此时宁可换便携版 QQ 另装一套，也不要继续登录（登录会再次抢会话）。
- `loadNapCat.js` 硬编码路径的症状：日志/二维码出现在**原目录**（`Downloads\NapCat.Shell\cache`），两个实例像在共用配置。复制后立即改正并复查。
- 健康判断按端口归属（`Get-NetTCPConnection -LocalPort 6100`）+ 每实例自己的 boot log；「QQ 进程总数」会把两个实例混在一起，没有诊断价值。
- 二维码过期会自动刷新几次（日志里 `二维码已过期，正在刷新…`）；客户没在有效期内扫就重启副本实例拿新码，不要等旧码。
- 第二套要开机自启：把它自己的 vbs 放 Startup 目录；两个实例的启动器互不依赖，但端口不能再撞。
