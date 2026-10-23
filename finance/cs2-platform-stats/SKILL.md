---
name: cs2-platform-stats
description: "Use when 查/播报 CS2 完美平台或 5E 战绩（分数/Rating/打完一把自动发群）。"
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [cs2, csgo, perfect-world, 5eplay, stats, qq, broadcast]
---

# CS2 战绩：完美平台 + 5E（查询 & 自动播报）

> ⛔ **2026-10-20：主人要求「把完美和5e的这个插件删掉」——功能已下线。** 脚本（`scripts/csgo-stats.py` / `csgo-match-watch.py`）、cron `4873b582ce5c`、完美 token（`cache/csgo/`）均已删除。本技能仅保留接口文档备查；**未经主人重新吩咐不要重建/重新开播报**。

完美平台从官方 App 接口取数（扫码登录换 token），5E 走公开接口（免登录）。两条线拼成一张卡片，按需发群或每打完一把自动播报。

## When to Use
- 用户要查自己的（或别人的）完美/5E 分数、Rating、最近对局。
- 要把战绩发到 QQ 群、或「每打完一把自动播报」。
- token/接口报错、播报不触发时的排障。

## 现成脚本（先跑，别重写）
- `$HERMES_HOME/scripts/csgo-stats.py` — 单次卡片。`--send` 发群（默认 `napcat-qq:GroupMessage:1093496287`），`--json` 出原始数据。
- `$HERMES_HOME/scripts/csgo-match-watch.py` — monitor：完美出现新 `matchId`、或 5E 的 ELO/场次变化 → 发群；没新对局**不输出**。状态在 `cache/csgo/match-watch-state.json`。
- cron `4873b582ce5c`「CS·打完一把播报」每 3 分钟跑 watcher（`no_agent=true`、`deliver=local`，脚本自己发群）。
- 配置：`$HERMES_HOME/cache/csgo/config.json`（`{"fivee_name": "<5E昵称>", "fivee_enabled": true|false}`；**2026-10-19 起主人不打 5E，该值已设 false——关着时脚本连查都不查、不报错**）；token：`$HERMES_HOME/cache/csgo/perfect_token.json`（`{token, steamId}`，**不进 git、不打印**）。
- 故障提醒只私聊主人（`napcat-qq:FriendMessage:1568468`），**绝不能发群**（主人 2026-10-19 明确嫌刷屏）。

## 完美平台：扫码登录换 token（唯一门槛）
完美所有接口都要 `token` + 与之匹配的 `mySteamId`。token 只能用手机号短信或**扫码**换；扫码最省事，用户用「完美世界电竞」App 扫一下即可。

1. `POST https://passport.pwesports.cn/qrAuth/applyToken`
   body：`{"appId":"5","qrType":"1","redirect":false,"website":"pvp"}`
   headers：浏览器 UA + `Referer: https://client.wmpvp.com`、`Content-Type: application/json`。
   → `result.accessUrl`（形如 `https://news.wmpvp.com?type=upgrade&accessToken=…&website=pvp&qrType=1`）。
2. 把 `accessUrl` 生成为二维码（`segno`，scale≈14 够清楚），把 PNG 发给用户。
3. 每 2 秒 `POST https://passport.pwesports.cn/qrAuth/check`，body `{"appId":"5","accessToken":"<从 accessUrl 抠出来的>"}`：
   `result.status` 0=待扫、1=已扫、2=确认（这时有 `result.token`（40 位）和 `result.accountItem.steamId`）、3=过期（二维码 5 分钟有效）。
4. 拿到后写 `cache/csgo/perfect_token.json`。轮询放后台跑，扫描期间别占用回合。

**参数形状是硬约束（踩过）**：必须 camelCase，`appId` 是**字符串** `"5"`；写成 `app_id`/数字或带 `steam_id` 会回 `1078 扫码类型无效`；带 `Origin` 头会回 `Invalid CORS request`（只带 Referer）。

## 完美平台：取数接口

`POST https://api.wmpvp.com/api/csgo/home/pvp/detailStats`
headers：`appversion: 3.5.4.172`、`token`、`platform: android`、`gameType: 1,2`、`gameTypeStr: 1,2`、`Content-Type: application/json`
body：`{"accessToken":"","csgoSeasonId":"","mySteamId":<int>,"toSteamId":<int>}` —— `mySteamId` 必须和 token 对应。
→ `data`：`pvpScore`（平台分）、`winRate`（0-1）、`cnt`、`pwRating`、`commonRating`、`adr`、`rws`、`headShotRatio`、`kills/deaths/assists`、`mvpCount`、`seasonId`（如 S25）、`name`。

`POST https://api.wmpvp.com/api/csgo/home/match/list`（同一套 headers）
body：`{"csgoSeasonId":"","dataSource":0,"mySteamId":<int>,"page":1,"pageSize":6,"pvpType":0,"toSteamId":<int>}`
→ `data.matchList[]`：`matchId`（形如 `LOCAL@…`）、`mapName`、`score1/score2`、`kill/death/assist`、`rating`、`pwRating`、`team`/`winTeam`（相等=赢）、`mode`（国服竞技/国服优先/国际服竞技）、`startTime`、`pvpScoreChange`。
`dataSource=0` 同时含国服竞技+国服优先；`dataSource=2` 是国际服。

## 5E：公开接口（免登录）
1. 搜索：`GET https://arena.5eplay.com/api/search/player/1/16?keywords=<urlencoded>` → `data.user.list[]`（`username`、`domain`）。
2. 换 uuid：`POST https://gate.5eplay.com/userinterface/http/v1/userinterface/idTransfer`，body `{"trans":{"domain":"<domain>"}}`，headers 必须带静态签名组合：
   `x-ca-key: 5eplay`、`x-ca-signature: pm/c+nYSScWXLOYG7WCczBallQAPFsQ+mu3szgvr7xg=`、`x-ca-signature-headers: Accept-Language,Authorization`、`x-ca-signature-method: HmacSHA256`、`Accept-Language: zh-cn`、`authorization: ""` → `data.uuid`。
3. 赛季数据：`GET https://gate.5eplay.com/crane/http/api/data/player/home?uuid=<uuid>` → `data.season_data.<id>`：`name`（对战匹配/优先排位）、`elo`、`rating`、`adr`、`rws`、`match_total`、`win_match_total`、`per_win_match`（0-1）、`per_headshot`、`impact`、`level_id`。取 `match_total` 最大的那季当当前季。

5E 没有找到公开的逐场详情接口 —— 「打完一把」的播报用赛季数据差值（ELO 变化 + 场次变化）。要找本人 5E 昵称：搜 `%APPDATA%\5E对战平台` 下的缓存文件里的 `nickname/username`（本机实测能从客户端缓存里认出）；客户端日志里有 `steamid_64`。

## 发到群
- 复用桥接：`importlib` 加载 `scripts/qq-bridge.py`，`send_qq(umo, text, True)`；UMO 用 `napcat-qq:GroupMessage:<群号>`。
- 发完在 `logs/qq-bridge.log` 里确认 `[send] -> … {'status': 'ok'}`；只看脚本返回值不算数。
- 群里按需查：用户在群里 @ 大肥鱼 说「查战绩」→ 跑 `csgo-stats.py --send`（不需要改桥接代码）。

## 坑
- **完美接口走系统代理会偶发 TLS 错误**（`SSLV3_ALERT_BAD_RECORD_MAC`）——本机 7899 中转不稳。所有国内请求用 `build_opener(ProxyHandler({}))` 绕代理；每轮重试 3 次；监控只在**连续 3 轮失败**时提醒一次（且只私聊主人），单次抖动不报。
- **token 会过期**：`statusCode` 非 0 / `errorMessage` 提示时，重跑扫码流程；别把过期当接口坏了。
- **首次跑 watcher 必须静默初始化**，否则会拿历史最后一局当「新对局」播报；状态文件丢了就删掉重跑一次初始化。
- **cron no_agent 脚本空闲时不能有任何 stdout**（空输出=不投递；打印 `[SILENT]` 会被当消息发出去）。
- 完美返回的 `rating`/`pwRating` 有时一个是 0，展示时取非零的；`pvpScoreChange` 为 0 就不要显示「+0」。
- 别在聊天/日志里回显 token；`perfect_token.json` 只落本地缓存。

## 本机现状（会变，用前核对）
- 完美：`IDK1337`，steamId 76561199857219177（与 5E 客户端同号）。
- 5E：`J2em`。
- 播报群：`1093496287`。
