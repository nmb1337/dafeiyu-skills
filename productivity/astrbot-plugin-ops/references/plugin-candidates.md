# 群聊玩法插件候选清单（AstrBot + 独立项目）

用途：用户问「有啥好玩的能装到机器人上」时先从这里起步，再用「Finding plugins」里的 `gh` 命令现场核星数和活跃度。装之前读 `main.py`，确认触发方式是指令型（不和大肥鱼抢话）。

## AstrBot 插件

| 插件 | 仓库 | 玩法 | 注意 |
|---|---|---|---|
| 群日常分析总结 | `SXP-Simon/astrbot_plugin_qq_group_daily_analysis` | 群聊总结成海报/网页，还能出群友连环漫画 | 需要 LLM；插件自带管理后台 |
| 主动搭话 | `Pancakes-Labs/astrbot_plugin_proactive_chat` | 主动发消息、动态情绪、TTS、免打扰时段 | 要给 AstrBot 配模型；频率不调会变话痨 |
| 词云与排名 | `GEMILUXVII/astrbot_plugin_cloudrank` | 群聊词云图 + 活跃度排行 | 纯分析，不依赖 LLM，安全 |
| 轮盘赌 | `piexian/astrbot_plugin_rg2`；另有「恶魔轮盘赌游戏」多人霰弹版 | 左轮/霰弹对决，带战绩排行榜 | 指令触发，适合整活 |
| 运势签到卡片 | `fiatlux2333/astrbot_plugin_jrys`（「今日运势签到」） | 抽签、签到、等级、每日宜忌，HTML 卡片 | 需 Playwright 渲染 |
| 赛博修仙志 | 市场搜「赛博修仙志」 | 群聊修仙 RPG：闭关、偷灵石、打架、炼丹、渡劫 | 纯指令玩法，文本量大 |
| 海龟汤 | 市场搜「谭某某的海龟汤」 | 出题、群友提问、LLM 当裁判 | LLM 可选但体验更好 |
| 本地猜歌 | 市场搜「本地猜歌」 | 本地曲库随机切片段让群友猜 | 正好可指向本机现成曲库 |
| 人格蒸馏器 | 市场搜「人格蒸馏器」 | 从群聊记录提炼某群友的人格 | 生成的是 AstrBot 人格，需手动启用 |
| 功德榜 | 市场搜「功德榜」 | 群聊功德账本，加分扣分、日报周榜 | 轻量，无外部依赖 |
| MC 状态查询 | `Celraw/astrbot_plugin_minecraft_status` | 群里查 MC 服务器状态（SLP 直连，本地出图） | 新仓，先试装 |
| 奶龙表情包 | `GeorgeNaNN/astrbot_plugin_nailong` | 随机/指定抽象表情包 | 需配图库仓库 |
| 互动合集 | `techjiang/astrbot-plugin-hd` | 40+ 群聊玩法、群 Boss 战、宠物养成 | 新仓 0★，先读代码再试 |
| 链接解析 | 「短视频聚合解析插件」/「社交媒体链接自动解析插件」 | 抖音/快手/小红书/B站链接自动转视频或图集 | 有的靠第三方 API，注意失效 |
| CS2 赛事助手 | 「HLTVCS2赛事助手」 | 实时比分、赛程、世界排名、比赛订阅 | 学生党刚需，指令型 |

## 独立项目（非 AstrBot 插件，可接进桥接）
- `Dituon/petpet`（~371★）— 群友头像生成摸头/亲亲 GIF。
- `MemeCrafters/meme-generator`（~1k★）— 文字生成沙雕表情包，可本地起 API 由桥接调用。

## 不装
- 色图/JM/涉未成年类插件（`astrbot_plugin_setu`、`astrbot_plugin_jm_cosmos` 等）——账号红线，直接跳过。
- 「读空气」类全量自动接话插件——和桥接抢话，除非先把桥接的群聊关掉。
- 与现有能力重复的：LLM 人格、长期记忆、点歌、画图、live dashboard。
