# 大肥鱼技能库（dafeiyu-skills）🐟

> Hermes Agent（by Nous Research）的实战技能库 —— **89 个技能**，全部来自一台真在干活的 Windows 机器，由主人 QQ 1568468 一手调教出来。

## 这是什么

Hermes 的「技能（skill）」= 一个目录 + 一份 `SKILL.md`：

- 顶部 YAML：`name`（技能名）、`description`（**什么时候该用它** —— 这是触发词，写得越准调用越准）
- 正文：干活步骤、踩过的坑、验证方法（不是论文，是操作手册）
- 可选配套：`scripts/`（可直接跑的脚本）、`references/`（深入文档）、`templates/`、`assets/`

Hermes 启动会话时会把这些技能的名字+描述放进上下文，模型判断该用时再读全文。**所以技能质量 ≈ 代理的实战水平**。

分类目录只是文件夹，方便浏览。

## 快速开始（3 步）

```powershell
# 1) 装 Hermes（Windows PowerShell）
iex (irm https://raw.githubusercontent.com/NousResearch/hermes-agent/main/scripts/install.ps1)
```

```bash
# macOS / Linux / WSL
curl -fsSL https://raw.githubusercontent.com/NousResearch/hermes-agent/main/scripts/install.sh | bash
```

```powershell
# 2) 把技能拷进 Hermes 技能目录（Windows）
git clone https://github.com/nmb1337/dafeiyu-skills.git
Copy-Item -Recurse .\dafeiyu-skills\* "$env:LOCALAPPDATA\hermes\skills\"
```

```bash
# macOS / Linux
git clone https://github.com/nmb1337/dafeiyu-skills.git
cp -r dafeiyu-skills/* ~/.hermes/skills/
```

3) 打开 `hermes`，问一句「**你现在有哪些技能？**」——能看到这些名字就装好了。

> ⚠️ 完整步骤、每个技能要改的本机参数、重型流水线（唱歌/画图）的前置条件，看 **[SETUP.md](SETUP.md)**。

## 目录索引

共 **89** 个技能，17 个分类：

### 🍎 `apple/` —— Apple 生态（macOS 本机）（4 个）

| 技能 | 什么时候用它 |
|---|---|
| `apple-notes` | Manage Apple Notes via memo CLI: create, search, edit. |
| `apple-reminders` | Apple Reminders via remindctl: add, list, complete. |
| `findmy` | Track Apple devices/AirTags via FindMy.app on macOS. |
| `imessage` | Send and receive iMessages/SMS via the imsg CLI on macOS. |

### 🤖 `autonomous-ai-agents/` —— AI 代理编排 / Hermes 自身（9 个）

| 技能 | 什么时候用它 |
|---|---|
| `claude-code` | Delegate coding to Claude Code CLI (features, PRs). |
| `codex` | Delegate coding to OpenAI Codex CLI (features, PRs). |
| `computer-use` | Drive the desktop background-first; escalate on signal. |
| `hermes-agent` | Use, configure, theme, extend, and orchestrate Hermes Agent. |
| `hermes-messaging-gateway` | Use when wiring up or debugging a Hermes gateway platform. |
| `hermes-model-tuning` | Use when tuning Hermes models or reasoning effort. |
| `mcp-server-onboarding` | Use when adding or fixing an MCP server in Hermes. |
| `opencode` | Delegate coding to OpenCode CLI (features, PR review). |
| `vscode-control` | Use when opening or driving VS Code on Windows. |

### 🌐 `browser-use/` —— 浏览器控制（1 个）

| 技能 | 什么时候用它 |
|---|---|
| `SKILL.md` | Direct browser control via CDP for web interaction: automation, scraping, testing, screen… |

### 🎨 `creative/` —— 创意生产（设计/信息图/像素画/视频/音乐）（18 个）

| 技能 | 什么时候用它 |
|---|---|
| `ai-presenter-video` | Make a verified AI presenter video from script + image. |
| `architecture-diagram` | Dark-themed SVG architecture/cloud/infra diagrams as HTML. |
| `ascii-art` | ASCII art: pyfiglet, cowsay, boxes, image-to-ascii. |
| `ascii-video` | ASCII video: convert video/audio to colored ASCII MP4/GIF. |
| `audiocraft-audio-generation` | AudioCraft: MusicGen text-to-music, AudioGen text-to-sound. |
| `baoyu-infographic` | Infographics: 21 layouts x 21 styles (信息图, 可视化). |
| `claude-design` | Design one-off HTML artifacts (landing, deck, prototype). |
| `comfyui` | Generate images, video, and audio via diffusion workflows. |
| `design-md` | Author/validate/export Google's DESIGN.md token spec files. |
| `heartmula` | HeartMuLa: Suno-like song generation from lyrics + tags. |
| `humanizer` | Humanize text: strip AI-isms and add real voice. |
| `hyperframes` | Render MP4/WebM videos from HTML compositions. |
| `manim-video` | Manim CE animations: 3Blue1Brown math/algo videos. |
| `meme-generation` | Create meme PNGs from templates with Pillow text overlay. |
| `p5js` | p5.js sketches: gen art, shaders, interactive, 3D. |
| `pixel-art` | Pixel art w/ era palettes (NES, Game Boy, PICO-8). |
| `popular-web-designs` | 54 real design systems (Stripe, Linear, Vercel) as HTML/CSS. |
| `songwriting-and-ai-music` | Songwriting craft and Suno AI music prompts. |

### 🖱️ `cua-driver/` —— 桌面 GUI 自动化（1 个）

| 技能 | 什么时候用它 |
|---|---|
| `SKILL.md` | Drive a native GUI app (macOS, Windows, Linux) via the cua-driver CLI (default) or MCP se… |

### 🛠️ `devops/` —— 部署运维（3 个）

| 技能 | 什么时候用它 |
|---|---|
| `sdlc-review` | Review Kanban handoffs and route verified outcomes. |
| `windows-ai-app-install` | Use when installing local AI apps on this Windows box. |
| `windows-local-app-setup` | Use when installing a Windows self-hosted app, or fixing 弹窗/自启/看护 (stray console windows,… |

### 📧 `email/` —— 邮件（2 个）

| 技能 | 什么时候用它 |
|---|---|
| `email-inbox-triage` | Triage an inbox: prioritize threads, draft replies safely. |
| `himalaya` | Himalaya CLI: IMAP/SMTP email from terminal. |

### 📈 `finance/` —— 行情/战绩（非交易）（1 个）

| 技能 | 什么时候用它 |
|---|---|
| `cs2-platform-stats` | Use when 查/播报 CS2 完美平台或 5E 战绩（分数/Rating/打完一把自动发群）。 |

### 🕳️ `local-proxy-resilience/` —— 本机网络代理容错（1 个）

| 技能 | 什么时候用它 |
|---|---|
| `SKILL.md` | Use when the proxy breaks local services or GitHub pushes. |

### 🎬 `media/` —— 音视频 / 游戏 / 直播（9 个）

| 技能 | 什么时候用它 |
|---|---|
| `dafeiyu-drawing` | Use when 大肥鱼画图/生图 (local ComfyUI Z-Image-Turbo pipeline). |
| `dafeiyu-mc-stream` | Use when 大肥鱼 MC 直播/陪玩（本地服务器 + Mindcraft 机器人）。 |
| `dafeiyu-singing` | Use when 大肥鱼点歌/翻唱 (local singing pipeline). |
| `game-server-hosting` | Use when 给游戏开联机服务器（僵尸毁灭工程/Minecraft 等）：开服、改配置、局域网/外网加入、排障。 |
| `gif-search` | Search/download GIFs from Tenor via curl + jq. |
| `minecraft-livestream` | Use when 开 MC 服务器/直播、鱼进游戏 (server+Mindcraft+OBS). |
| `songsee` | Audio spectrograms/features (mel, chroma, MFCC) via CLI. |
| `video-montage-editing` | Use when 剪游戏高光/击杀集锦/卡点 montage，或把一段素材剪成宣传片风格短片。 |
| `youtube-content` | YouTube transcripts to summaries, threads, blogs. |

### 📝 `note-taking/` —— 笔记（1 个）

| 技能 | 什么时候用它 |
|---|---|
| `obsidian` | Read, search, create, and edit notes in the Obsidian vault. |

### 📦 `productivity/` —— 办公与自动化（文档/表格/PDF/QQ 插件）（18 个）

| 技能 | 什么时候用它 |
|---|---|
| `airtable` | Airtable REST API via curl. Records CRUD, filters, upserts. |
| `astrbot-plugin-ops` | Use when installing or extending AstrBot plugins. |
| `box` | Box manages cloud files, sharing, search, and metadata. |
| `document-to-action-items` | Extract cited obligations, deadlines, tasks from documents. |
| `docx` | Create, read, edit, template, and review Word .docx files. |
| `github-qq-notify` | Use when 调试或改造 GitHub 推送→QQ 群播报（github-watch 服务）。 |
| `google-workspace` | Gmail, Calendar, Drive, Docs, Sheets via gws CLI or Python. |
| `maps` | Geocode, POIs, routes, timezones via OpenStreetMap/OSRM. |
| `meeting-action-items` | Turn meeting notes into cited decisions, owners, tickets. |
| `notion` | Notion API + ntn CLI: pages, databases, markdown, Workers. |
| `onebot-qq-bridge` | Use when debugging or tuning the NapCat/OneBot QQ bridge. |
| `pdf` | PDF files: create, read, merge, fill, OCR, edit text. |
| `powerpoint` | Create, read, edit .pptx decks with python-pptx. |
| `product-price-monitor` | Watch product, flight, or listing prices; alert on target. |
| `teams-meeting-pipeline` | Teams meeting summaries, job replay, Graph subscriptions. |
| `weekly-review-planning` | Weekly reset: commitments, stalled work, next-week plan. |
| `xianyu-hardware-monitor` | Use when working on the local 闲鱼 hardware monitor. |
| `xlsx` | Create, read, edit Excel .xlsx workbooks and CSVs. |

### 🔬 `research/` —— 资料研究（4 个）

| 技能 | 什么时候用它 |
|---|---|
| `arxiv` | Search arXiv papers by keyword, author, category, or ID. |
| `competitor-news-monitor` | Watch named companies for material news; cited digests. |
| `grounded-citations` | Ground answers and documents in cited, verifiable sources. |
| `llm-wiki` | Karpathy's LLM Wiki: build/query interlinked markdown KB. |

### 📱 `social-media/` —— 社交媒体（2 个）

| 技能 | 什么时候用它 |
|---|---|
| `douyin-short-video` | Use when making a 抖音 short video for the 大肥鱼 account. |
| `xurl` | X/Twitter via xurl CLI: raw post search, posting, DM, media. |

### 💻 `software-development/` —— 软件开发（13 个）

| 技能 | 什么时候用它 |
|---|---|
| `codebase-inspection` | Inspect codebases w/ pygount: LOC, languages, ratios. |
| `dogfood` | Exploratory QA of web apps: find bugs, evidence, reports. |
| `github` | GitHub via gh CLI: PRs, issues, reviews, repos, auth. |
| `hermes-agent-skill-authoring` | Author in-repo SKILL.md files: frontmatter and structure. |
| `inspecting-hermes-desktop-dom` | Read the live Hermes desktop DOM/CSS over CDP. |
| `node-inspect-debugger` | Debug Node.js via --inspect + Chrome DevTools Protocol CLI. |
| `python-debugpy` | Debug Python: pdb REPL + debugpy remote (DAP). |
| `requesting-code-review` | Pre-commit review: security scan, quality gates, auto-fix. |
| `simplify-code` | Parallel 4-agent cleanup of recent code changes. |
| `spike` | Throwaway experiments to validate an idea before build. |
| `systematic-debugging` | 4-phase root cause debugging: understand bugs before fixing. |
| `test-driven-development` | TDD: enforce RED-GREEN-REFACTOR, tests before code. |
| `windows-desktop-launch` | Use when opening a Windows app or project window. |

### 🎙️ `voice-cloning/` —— 声音克隆（1 个）

| 技能 | 什么时候用它 |
|---|---|
| `SKILL.md` | Use when cloning a voice from reference audio (音色克隆). |

### 🕸️ `web/` —— 网页抓取（1 个）

| 技能 | 什么时候用它 |
|---|---|
| `blocked-page-recovery` | Use when a fetch fails: 403/429, paywall, WAF, bot wall. |

## 三条「真机跑通」的重型流水线

| 流水线 | 做什么 | 前置 |
|---|---|---|
| `media/dafeiyu-singing` | 点歌 → 自动找歌 → demucs 分离 → **Seed-VC 零样本换声**（大肥鱼嗓）→ 混音出 mp3 | NVIDIA GPU（8GB 够）、torch cu128、~1GB 模型、一段参考音 |
| `media/dafeiyu-drawing` | 「画一张…」→ 本地 ComfyUI（**Z-Image-Turbo**，8 步）→ 出图发聊天；「把这张改成…」→ Flux Kontext 改图 | NVIDIA GPU、ComfyUI（8199/8189 端口分开）、对应模型 |
| `media/dafeiyu-mc-stream` / `minecraft-livestream` | MC 服务器 + Mindcraft 机器人 + OBS 推流 + 游戏内语音 | Java 21、Node 22、OBS、正版 MC |

唱歌/画图这两条是**代码随技能打包**的，照各自目录里的 `SETUP.md` 装就能复刻。

## 哪些技能要改配置

带 `本机` 字样的技能写的是原作者那台机器的路径/端口/账号。换机器要改的地方集中在：

1. **路径**：`C:\Users\32672\Apps\...` → 你的安装路径
2. **端口**：QQ 桥接 8790/3001、图片 ComfyUI 8189、视频 ComfyUI 8188、RCON 25575 —— 别和本机已有服务撞
3. **账号**：QQ 号、群号、微信/邮箱/Notion 之类都要换成你自己的
4. **密钥**：一律放 `HERMES_HOME/.env`，**不要**写进技能文件

具体到每个技能：见 [SETUP.md 第 7 节](SETUP.md#7-需要改本机参数的技能)。

## 没有上传的内容

- 炒股/量化类技能（沪金量化、OKX 代币化股票、股票自动交易）—— **不上传**
- 本机状态文件（`.locks`、`.usage.json`、`.curator_*`、`.hub` 缓存）—— 不上传
- 任何密钥/token —— 仓库里只有占位符（`sk-xxx`、`ghp_xx`）

## 许可

技能内容来自作者的实际使用经验，MIT 随意取用；其中 `hermes-agent` 等技能改编自 Nous Research 的 Hermes Agent 官方技能，版权归原作者。
