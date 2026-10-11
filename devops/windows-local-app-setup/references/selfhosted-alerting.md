# 自托管服务的告警推送（面板 → 本机转发器 → 用户 IM）

目标：服务挂了/恢复了能主动推给用户，而不是只在面板里躺着。全线本机、不需第三方账号。

## 出站通道：`hermes send`

- `hermes send --to <platform> "<text>"` —— 复用 gateway 已配置的平台凭据，**不走 LLM、不花钱**，给脚本/cron/告警用。
- `hermes send --list [platform]` 查可用目标；`--to` 支持 `platform`（home 频道）/`platform:chat_id`/`platform:#channel`；正文也可 `--file`/stdin；带附件在正文里写 `MEDIA:<path>`。
- 本机 `hermes` 在 `$HERMES_HOME\bin\hermes.exe`（不一定在 PATH，转发器里写全路径）。

## 本机转发器（`scripts/uptime-alert.py`）

- 只依赖标准库：`ThreadingHTTPServer` 监听 `127.0.0.1:8795`，端点 `POST /kuma`，收 JSON → 拼中文消息 → `subprocess.run([HERMES, "send", "--to", TARGET, text])`。
- 日志由脚本自己写 `logs/uptime-alert.log`（含 `send rc=... ok=...`），**不要**在 VBS 里做 `>>` 重定向。
- 常驻：`gateway-service/UptimeAlert.vbs`（纯 ASCII）里直接 `sh.Run q & py & q & " -u scripts\uptime-alert.py", 0, False` —— 不经 cmd、不手拼重定向引号；带 8795 单实例守卫；再登记进看护 SERVICES（name/port/launcher/wait_s）。
- 消息模板：`🔴 服务挂了：<name>` / `🟢 恢复正常：<name>` + 原因 + URL + 时间。

## 面板 Webhook 载荷（Uptime Kuma）

- body：`{"monitor": {...}, "heartbeat": {...}, "msg": "..."}`；`heartbeat.status`：`0`=DOWN `1`=UP `2`=PENDING `3`=MAINTENANCE（据此选 emoji/文案）。
- 通知配置 JSON（服务端读 `notification.webhookURL / httpMethod / webhookContentType / webhookAdditionalHeaders`）：
  `{"type":"webhook","webhookURL":"http://127.0.0.1:8795/kuma","httpMethod":"post","webhookContentType":"json"}`
- **「测试」按钮的载荷里没有 monitor/heartbeat** → 单独判成「✅ 测试通知：通道已打通」，别渲染成「未知监控项」。

## 通知不落库时的兜底（Kuma 通知走 socket.io）

现象：表单填好、点「保存」无报错、弹窗不关、通知列表仍是「暂不可用，请先设置。」、`notification` 表 0 行。监控项的 `/add`、`/edit/<id>` 同样方式却能保存 —— 差别在通知走 socket.io。

做法：`pm2 stop uptime-kuma` → 写库 → `pm2 start uptime-kuma` → 回读核对。

```sql
-- 表：notification(id,name,active,user_id,is_default,config)；user_id 用 1；is_default=1 让新监控项自动挂上
insert into notification (name, active, user_id, is_default, config) values (?, 1, 1, 1, ?);
-- 表：monitor_notification(id,monitor_id,notification_id) —— 每个要通知的监控项一行
insert into monitor_notification (monitor_id, notification_id) values (?, ?);
```

- 改库前**必须停服**（避免写入竞争）；只读查询用 `sqlite3.connect("file:<path>/kuma.db?mode=ro", uri=True)`。
- 健康检查端点先 `curl --noproxy '*'` 找返回 200 的路径（如 `/health`），404/401 的路径会让监控项一开始就判故障。

## 验证（两层，缺一不可）

1. 直接给转发器打一条模拟载荷：`curl --noproxy '*' -X POST http://127.0.0.1:8795/kuma -H 'Content-Type: application/json' --data-binary "@C:/path/test.json"` → 看日志出现 `send rc=0 ok=True`。
2. 再从面板页面点一次「测试」→ 日志应再出一条（证明**保存后的那条配置**真在跑，而不是内存里的临时表单）。
