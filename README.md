# 大肥鱼技能库（dafeiyu-skills）🐟

本机 Hermes Agent（by Nous Research）里在用的**全部技能**打包 —— 由主人 QQ 1568468 一手调教出来的。

## 这是什么

每个子目录是一个**技能（skill）**，核心是 `SKILL.md`：

- 顶部 YAML 头：`name` / `description`（description = "什么时候该用它"）
- 正文 = 干活步骤、踩过的坑、验证方法
- 配套文件放 `scripts/`、`references/`、`templates/`、`assets/`

外层目录只是**分类**，方便浏览。一共 **78 个技能**。

## 目录结构

| 分类 | 大概内容 |
|---|---|
| `autonomous-ai-agents/` | AI 代理编排（claude-code / codex / hermes-agent 等） |
| `creative/` | 设计图 / 信息图 / ASCII / 像素画 / 歌曲创作 |
| `devops/` `software-development/` | 本机装软件、调试、代码评审、数据库检查 |
| `email/` `note-taking/` `productivity/` | 邮件、笔记、文档 / 表格 / PDF / 演示 |
| `media/` `social-media/` `voice-cloning/` | 音频视频、抖音短视频、声音克隆、**点歌翻唱** |
| `web/` `browser-use/` `research/` | 网页抓取、浏览器控制、资料研究 |
| `local-proxy-resilience/` 等 | 本机环境专属的血泪经验 |

## 两条重型本地流水线（唱歌 / 画图）

这两条是本机真正跑起来的完整流水线，**代码随技能一起打包**，换台机器照 `SETUP.md` 装完就能复刻：

- **`media/dafeiyu-singing/`** —— 点歌翻唱：歌曲 → demucs 分离人声 → Seed-VC 零样本换成「大肥鱼」嗓 → 混音出 mp3。
  需要 NVIDIA GPU（torch 用 cu128）、约 1GB 模型（HuggingFace 可下）、一段自己的参考音。见 `SETUP.md`。
- **`media/dafeiyu-drawing/`** —— 本地画图：ComfyUI + Z-Image-Turbo（NVFP4），8 步出图；按需拉起、空闲自关（不占着显存）。见 `SETUP.md`。

其余技能多数是方法论 / 流程，直接读 `SKILL.md` 就能用。

## 怎么用

把想要的那个技能目录拷进你的 Hermes 技能目录就行，例如：

```
~/AppData/Local/hermes/skills/<分类>/<技能名>/
```

Windows 一般在 `C:\Users\<你>\AppData\Local\hermes\skills\`。放进去之后 Hermes 会自动扫到，需要时按 description 触发。

## 注意

- 本仓库只含**方法 / 代码 / 配置**：不含任何密钥、令牌、密码，也不含模型权重和成品音频（几 GB 的东西按 `SETUP.md` 自行下载）。
- 里面的路径、端口是本机环境的实际布局，换机器时按自己环境改。

---

*本鱼的所有本事，都是我家主人一点点喂出来的* 🐟
