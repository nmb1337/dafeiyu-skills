# 部署说明书（SETUP）

> 把这套技能装到**你自己的机器**上，让 Hermes 具备同样的实战能力。
> 读完后你应该能：装好 Hermes → 装好技能 → 知道哪些要改 → 跑通唱歌/画图 → 排掉常见坑。

---

## 0. 适用对象

- 系统：Windows 10/11（原生）、macOS、Linux、WSL2 都行
- 硬件：日常技能无要求；**唱歌/画图需要 NVIDIA 显卡**（8GB 显存实测够用）
- 基础：会用终端/命令行，知道什么是环境变量

---

## 1. 前置条件

| 项目 | 要求 | 说明 |
|---|---|---|
| Hermes Agent | 最新版 | 见第 2 节 |
| Python | 3.11+ | Hermes 安装器自带；重型流水线用独立 venv |
| Git | 任意版本 | 拉这个仓库用 |
| 模型 API | 任一 Hermes 支持的供应商 | DeepSeek / OpenRouter / OpenAI / Anthropic / 本地 Ollama 都行，配在 `.env` |
| GPU（可选） | NVIDIA 8GB+ | 只影响唱歌/画图/视频流水线 |

---

## 2. 安装 Hermes

### 2.1 Windows（原生，推荐）

PowerShell（**不需要管理员**）：

```powershell
iex (irm https://raw.githubusercontent.com/NousResearch/hermes-agent/main/scripts/install.ps1)
```

安装完：
- 程序与数据在 `%LOCALAPPDATA%\hermes\`
- `hermes` 被加进用户 PATH —— **要开新终端**才生效
- 首次运行 `hermes setup` 选模型/填 key

### 2.2 macOS / Linux / WSL2

```bash
curl -fsSL https://raw.githubusercontent.com/NousResearch/hermes-agent/main/scripts/install.sh | bash
```

数据目录：`~/.hermes/`。

### 2.3 验证

```bash
hermes doctor        # 体检
hermes               # 进聊天
```

官方文档：<https://hermes-agent.nousresearch.com/docs/>

---

## 3. 技能（skill）是什么

```
skills/
└── creative/
    └── pixel-art/
        ├── SKILL.md          ← 必须有：YAML 头 + 正文
        ├── scripts/          ← 可选：可直接运行的脚本
        ├── references/       ← 可选：深入资料
        ├── templates/        ← 可选：模板
        └── assets/           ← 可选：图片等
```

`SKILL.md` 最小结构：

```markdown
---
name: pixel-art
description: "Use when 画像素画 / 像素风素材。按年代调色板出图。"
---

# 正文：什么时候用、怎么做、怎么验证
```

- `description` 是**触发表述**：Hermes 靠它判断「现在该不该加载这个技能」。写「Use when …」最稳。
- 正文别写论文，写**步骤 + 坑 + 验证方法**。
- 技能是**按档案（profile）隔离**的：`default` 档案用 `HERMES_HOME/skills`，其他档案用 `HERMES_HOME/profiles/<名字>/skills`。

---

## 4. 安装本技能库

### 4.1 整库安装（Windows PowerShell）

```powershell
cd $env:TEMP
git clone https://github.com/nmb1337/dafeiyu-skills.git
Copy-Item -Recurse .\dafeiyu-skills\* "$env:LOCALAPPDATA\hermes\skills\" -Force
```

### 4.2 整库安装（macOS / Linux / WSL）

```bash
cd /tmp
git clone https://github.com/nmb1337/dafeiyu-skills.git
mkdir -p ~/.hermes/skills
cp -r dafeiyu-skills/* ~/.hermes/skills/
```

### 4.3 只装你需要的（推荐）

按分类拷，例如只要创意+办公：

```powershell
Copy-Item -Recurse .\dafeiyu-skills\creative   "$env:LOCALAPPDATA\hermes\skills\"
Copy-Item -Recurse .\dafeiyu-skills\productivity "$env:LOCALAPPDATA\hermes\skills\"
```

只要一个技能：

```powershell
Copy-Item -Recurse .\dafeiyu-skills\media\dafeiyu-singing "$env:LOCALAPPDATA\hermes\skills\media\"
```

### 4.4 装进某个档案（多开 Hermes 时）

```powershell
Copy-Item -Recurse .\dafeiyu-skills\* "$env:LOCALAPPDATA\hermes\profiles\myprofile\skills\" -Force
```

### 4.5 验证

```bash
hermes
# 然后输入：
你现在有哪些技能？用一句话列出每个技能的用途。
```

也可以直接看目录是否出现 `SKILL.md`。

> 技能在**新会话**才加载完整列表；已经开着的会话可以发 `/reload-skills`（若你的版本不支持就重开）。

---

## 5. 目录索引（89 个技能）

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

---

## 6. 分类怎么选（给新手的建议）

| 你想要 | 先装这些 |
|---|---|
| 日常办公（文档/表格/PDF/邮件/笔记） | `productivity/` `email/` `note-taking/` |
| 写代码/代码评审 | `software-development/` `autonomous-ai-agents/` |
| 做图/做视频/做音乐 | `creative/` `media/` |
| 让 AI 接管桌面/浏览器 | `browser-use/` `cua-driver/` |
| 接 QQ/微信机器人 | `productivity/onebot-qq-bridge` `autonomous-ai-agents/hermes-messaging-gateway` |
| 本地唱歌/画图 | `media/dafeiyu-singing` `media/dafeiyu-drawing`（要 GPU） |
| 服务器/联机游戏 | `media/game-server-hosting` `media/dafeiyu-mc-stream` |

---

## 7. 需要改本机参数的技能

> 下面这些技能写的是**原作者机器**的路径/端口/账号。不改也能读，但跑不起来。

| 技能 | 要改什么 | 原值（示例） |
|---|---|---|
| `media/dafeiyu-singing` | 项目路径、venv、参考音、GPU 型号、TTS 参考音要和唱歌用同一段 | `C:\Users\32672\Apps\dafeiyu-sing`；refs `dafeiyu_ref20s.wav` |
| `media/dafeiyu-drawing` | ComfyUI 路径、端口（图片 8189 / 视频 8188 **不能混**）、模型文件名、内容闸门词表 | `Apps\ComfyUI_windows_portable` |
| `media/dafeiyu-mc-stream` | MC 服务器目录、RCON 密码、OBS 路径、WS 4455、语音桥 | `C:\Users\32672\Apps\...` |
| `media/minecraft-livestream` | 同上 + Mindcraft 配置 | — |
| `media/game-server-hosting` | 端口、内网 IP、frp/VPS 地址 | 16261/25565 |
| `productivity/onebot-qq-bridge` | 桥接端口 8790、NapCat WS 3001、配置文件名、机器人的 QQ 号 | `qq_bridge.json` |
| `productivity/github-qq-notify` | GitHub 仓库、群号、AstrBot 地址 | — |
| `productivity/astrbot-plugin-ops` | AstrBot 目录、端口 6185、插件目录 | `Apps\astrbot` |
| `local-proxy-resilience` | 代理端口（7890/7899）、中转脚本路径 | `scripts/net-relay.py` |
| `devops/windows-ai-app-install` `devops/windows-local-app-setup` | Windows 安装路径、服务名 | `C:\Users\<你>\Apps` |
| `finance/cs2-platform-stats` | 完美/5E 账号、群号、桥接口令 | — |
| `social-media/douyin-short-video` | 抖音账号、发布流程、素材目录 | 本机客户端登录态 |
| `apple/*` | 只适用于 macOS，需要「完全磁盘访问」等权限 | — |
| `email/himalaya` `productivity/google-workspace` `notion` `airtable` `box` | 各平台自己的账号/OAuth/API key，放 `.env` | — |

**统一原则**：
1. 路径全换成你的（Windows 用 `C:/...` 正斜杠，给原生程序时别用 `/c/...`）
2. 密钥全部进 `HERMES_HOME/.env`，技能里只留变量名
3. 端口冲突就换，但**同一个技能里所有相关文件要一起改**

---

## 8. 重型流水线：唱歌

**目标**：说「唱《起风了》」→ 自动找歌 → 分离人声 → 换成你的音色 → 混音出 mp3 → 发回聊天。

**前置**：
- NVIDIA GPU（8GB 够，原作者 5060 Ti 8G；整首 4 分钟约 6~10 分钟）
- `torch` cu128 的独立 venv（**不要**和别的项目混）
- Seed-VC 代码（Plachtaa/Seed-VC）+ demucs
- 一段 8~20 秒干净人声当参考音（**必须和 TTS 用同一段**，否则唱歌和说话像两个人）
- 找个音源：B 站搜索（`fetch_bili.py`）或本地 mp3

**步骤**：见 `media/dafeiyu-singing/SETUP.md`（含模型下载、venv、参考音处理、常见音准问题）。

**常见坑**：
- 换声后音低 6 个半音 → 参考音音区不对（Seed-VC 的 `--auto-f0-adjust` 会把歌声往参考音拽）
- 代理把 B 站搜索掐死 → 服务启动时清代理环境变量
- `yt-dlp` 指定 mp3 却留下 m4a → 显式转换

---

## 9. 重型流水线：画图

**目标**：「画一张…」→ 本地 ComfyUI 出图 → 发聊天；「把这张改成…」→ 图生图/指令编辑。

**前置**：
- NVIDIA GPU（8GB 够，Z-Image-Turbo NVFP4 8 步）
- ComfyUI（便携版即可）+ 模型：
  - `z_image_turbo_nvfp4.safetensors`（unet）
  - `qwen_3_4b_fp4_mixed.safetensors`（text encoder）
  - `ae.safetensors`（vae）
  - 改图另需 Flux Kontext（`flux1-kontext-dev-Q4_K_M.gguf`）+ `ComfyUI-GGUF` 节点 + `gguf` 包
- 端口规划：**图片 8189，视频 8188**（视频脚本靠 8188 判断就绪，别混）

**步骤**：见 `media/dafeiyu-drawing/SETUP.md`。

**常见坑**：
- 屏幕采集/工作流缺失 → 按 `scripts/image_service.py` 里写死的节点逐一对齐
- Kontext 缺 `ModelSamplingFlux` → 退化成「原图复印机」
- 显存吃紧 → 按需拉起 + 空闲自动关（技能里已有）

---

## 10. 常见问题（FAQ）

**Q：技能装了但 Hermes 不用？**
1. 确认目录结构是 `skills/<分类>/<技能名>/SKILL.md`
2. 检查 `SKILL.md` 头部的 `---` 是否成对、`name`/`description` 是否有
3. 重开会话（技能列表在会话开始时加载）

**Q：中文乱码？**
Windows 控制台用 UTF-8；脚本读写文件显式 `encoding="utf-8"`。

**Q：`python` 找不到 / 版本不对？**
Hermes 安装器会自带一个 Python；重型流水线各用独立 venv（`uv venv` + `uv pip install`）。

**Q：端口被占？**
`netstat -ano | findstr :8790`（Windows）或 `lsof -i:8790`。

**Q：GPU 显存不够？**
- 画图：关掉视频 ComfyUI、降低分辨率/步数
- 唱歌：整首分段处理，或先跑 60 秒试听

**Q：技能里的路径全是 `C:\Users\32672`？**
那是原作者机器。全局搜一下替换成你的路径即可（第 7 节有清单）。

**Q：能只用一部分技能吗？**
能。技能互相独立，按目录拷即可。

---

## 11. 安全提示

- 这些技能里有**大量终端/文件/系统操作**。装之前先读 `SKILL.md` 和 `scripts/`，确认你接受它的行为。
- 涉及账号的技能（QQ/微信/抖音/邮箱/Notion）**只在你自己的账号上用**。
- 多档案（profile）部署时，技能是隔离的：客户档案别放你自己机器的运维技能。
- 仓库不含任何密钥；如果你 fork 后要提交，先 `git diff` 检查有没有把 `.env` 带进去。

---

## 12. 更新与卸载

```bash
# 更新
cd dafeiyu-skills && git pull
# 再覆盖拷一次（同上第 4 节）

# 卸载某个技能
rm -rf ~/.hermes/skills/<分类>/<技能名>
```

---

## 13. 致谢

- Hermes Agent：<https://github.com/NousResearch/hermes-agent>
- 部分技能改编自 Hermes 官方技能库（MIT）
- 其余来自作者在 Windows 上的实际踩坑记录
