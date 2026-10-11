---
name: xianyu-hardware-monitor
description: "Use when working on the local 闲鱼 hardware monitor."
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [xianyu, monitor, astrbot, napcat, qq, ai-review]
---

# 闲鱼硬件监控 (local service) — operations

## When to Use
- Configuring, debugging, or extending the user's 闲鱼硬件监控 service (notifications, AI screening, scans).
- Sending QQ messages through the existing AstrBot + NapCat chain.

## Layout & ports
- Repo (git): `C:\Users\32672\Documents\Codex\2026-09-09\github-qq` (branch `codex/integrated`, origin `nmb1337/xianyu-hardware-monitor`). Deployed copy: `C:\xianyu-hardware-monitor` (no .git).
- Web console/API: `http://127.0.0.1:8788` (`src/server.js`).
- Notification chain: monitor → **AstrBot OpenAPI** `POST http://127.0.0.1:11451/api/v1/im/messages` `{umo:"<botId>:FriendMessage:<qq>", message}` (Bearer = AstrBot IM key) → NapCat (OneBot, WebUI :6099, runs inside QQNT) → QQ private message. Bot id = `napcat-qq`; receivers = setting `astrbot_receiver_qq`.
- AstrBot WebUI :6199.

## Settings: use the HTTP API, not the DB
- `GET /api/settings`, `PUT /api/settings` (camelCase: astrbotBaseUrl, astrbotApiKey, astrbotBotId, astrbotReceiverQq, browserProxy, aiEnabled, aiBaseUrl, aiApiKey, aiModel, scanPacing, appraisal), `POST /api/settings/test-ai`, `POST /api/settings/test-astrbot`.
- **`ai_review_prompt` (owner's extra screening instruction) is NOT exposed by the API** — write it into `data/monitor.sqlite`, table `settings(key,value,updated_at)`; `updated_at` is NOT NULL epoch-ms.
- **Pitfall that bricks the service**: an INSERT that raises (e.g. NOT NULL, or a lock timeout) leaves the connection's transaction open; the file stays locked and *every* write — including the app's own `PUT /api/settings` — returns `database is locked` until that connection is rolled back/closed. Always rollback+close in `finally`; if all writes suddenly fail, hunt your own leaked connection first.

## AI screening (魔改卡 / 坏卡 → never notified)
- Gate: `ai_enabled=1` + `ai_base_url` + `ai_model` (+ key). `src/ai.js` posts each batch to `{ai_base_url}/chat/completions` with `response_format=json_object`, `max_tokens=1500`; `block=true` (risk `faulty`|`modified`) blocks the listing, `notify=false` drops the alert.
- **Use `deepseek-chat`, never `deepseek-flash`**: flash thinks, and with `max_tokens=1500` the reasoning can eat the whole budget → empty content → intermittent `AI 返回内容为空或过长`. Verified: chat stable, flash flaky.
- Owner rules live in `ai_review_prompt`; the model must quote title text as `evidence`. Negations (非矿/无拆无修/未维修) are not defects.

## Verification recipes
- Test QQ delivery: POST AstrBot OpenAPI as above (key = setting `astrbot_api_key`).
- Test screening: call `https://api.deepseek.com/v1/chat/completions` with `src/ai.js`'s system prompt + `ai_review_prompt` plus sample titles; assert 魔改/故障 blocked and clean cards pass.
