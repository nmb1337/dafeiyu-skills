---
name: douyin-short-video
description: "Use when making a 抖音 short video for the 大肥鱼 account."
version: 1.0.0
author: Hermes Agent (大肥鱼)
license: MIT
platforms: [windows, macos, linux]
metadata:
  hermes:
    tags: [douyin, 抖音, short-video, tts, ffmpeg, content, social-media]
---

# 抖音短视频（大肥鱼账号）

## When to Use

- 主人说「发一条抖音 / 做个短视频 / 学别人怎么做视频 / 评论区怎么运营」时
- 给大肥鱼账号定选题、写口播稿、配音、合成视频、写话题标签、复盘数据时
- 新账号/新平台（抖音号、小号、视频号）规划与发布时

号主是这台机器上的 Hermes/大肥鱼本人：内容源就是**我自己的日常**——修桥接、盯服务器、写监控、翻车与复盘。不露脸，用配音 + 画面（截图/卡片/录屏）。

## 平台硬规则（2026，违反会降权/封号）

- **AI 内容必须标注**：发布时勾选「AI 辅助创作」。不标 = 降权甚至封号；发布前把这一步当清单项。
- **至少 30% 人工/原创成分**：纯 AI 批量产出的容忍度在下降；每条至少要有自己的观点、真实的机器画面或实拍素材。
- **不搬运、不混剪他人视频**；素材优先用①本机截图/录屏 ②自己生成的图卡 ③有明确授权/免费商用库。
- **评论不能刷**：小号自导自演、买粉、刷互动属于作弊，会拉低账号权重；真实回复评论才是加分项。
- **隐私红线**：主人的 QQ 号、群号/群名、微信号、项目密钥、闲鱼监控细节、客户信息——**一律打码或改成示意**。发布前逐帧过一遍。

## 账号基础（一次性）

- 昵称：「大肥鱼」+ 领域词（如「大肥鱼的AI日常」）；头像用蓝色鲸鱼娘形象；简介三段式：我是谁 → 发什么 → 更新频率/钩子。
- 封面模板：统一风格（大标题 + 鲸鱼娘形象 + 对比色），固定复用。
- 垂直：前 30 天只讲一类（AI 帮主人干活 / 数字生命日常），别乱切赛道。

## 视频结构与节奏

- 15–45 秒；**前 3 秒钩子**（反常识结论或痛点提问），例：「我家 AI 昨晚把自己服务器搞挂了，然后它自己修好了」。
- 中段：一件具体的事 + 一个可视证据（日志/画面/前后对比），别空口讲道理。
- 结尾：一句互动引导（「你想让我下次拿哪个活儿练手？」）。
- 发布时段：18:00–19:00 最佳，12:00–13:00 次之；每周 3–5 条起步，别断更。

## 生产线（本机可全自动）

1. **脚本**：从真实日志/流水里挑一件小事（`$HERMES_HOME/scripts/PROGRESS.md` 是最好的素材库），写成 80–200 字口播稿。
2. **配音**：`text_to_speech` 工具（本机已设 `tts.edge.voice = zh-CN-XiaoyiNeural`，中文年轻女声；要换嗓音用 `hermes config set tts.edge.voice <voice>`）。导出 mp3。
3. **画面**：①`computer_use` 截图（真实桌面/终端）②PIL/HTML 生成的图卡（标题卡、数据卡）③`ffmpeg -f gdigrab` 录屏（Windows）。统一 1080×1920 竖屏。
4. **合成**（ffmpeg，示例）：
   ```bash
   ffmpeg -y -f concat -safe 0 -i imgs.txt -i voice.mp3 -i bgm.mp3 \
     -filter_complex "[0:v]scale=1080:-2,crop=1080:1920,subtitles=sub.srt:force_style='FontSize=16,Outline=2'[v];[1:a]volume=1.0[a1];[2:a]volume=0.2[a2];[a1][a2]amix=inputs=2:duration=first[a]" \
     -map "[v]" -map "[a]" -c:v libx264 -pix_fmt yuv420p -c:a aac -shortest out.mp4
   ```
   ffmpeg 在 `$HERMES_HOME/tools/ffmpeg-*/bin/ffmpeg`（不在默认 PATH，用绝对路径）。
5. **字幕**：把口播稿按句子切成 srt（时间轴按字数比例估），或先用 `ffprobe` 拿音频时长再均分。
6. **发布**：①人工上传（主人手机/网页版最稳）②或浏览器自动化上传后**人工确认再点发布**。发布时勾选 AI 标注，填 3–5 个精准话题（垂直词 + 场景词，别堆热门泛词）。

## 发布实操（抖音 PC 客户端，已实测跑通）

登录态在**客户端的 webview** 里，不在系统浏览器 —— 只能用 computer_use 驱动桌面客户端（后台点击对 webview 有效，中文输入必须 foreground/剪贴板）。

1. 顶栏右上「投稿」图标（坐标约 native (1669,33)）点一下 → 弹出菜单 → 点「**发布视频/图文**」→ 客户端内打开创作者中心上传页。
2. 点「**上传视频**」→ 弹 Windows 原生文件对话框。**填绝对路径用 `set_value`（UIA ValuePattern）而不是键盘输入**，然后 Enter：`action=set_value, element=<文件名(N) Edit 索引>, value='C:\\...\\v.mp4'`。
3. 上传完自动进表单。填标题（≤30 字）：**先 click 标题 Edit（foreground）→ ctrl+a → ctrl+v**；中文用剪贴板粘贴（`printf '%s' '文字' | clip.exe` 会乱码，要用 `powershell -NoProfile -Sta -Command "Set-Clipboard -Value ([IO.File]::ReadAllText('file.txt',[Text.Encoding]::UTF8))"`）。**SendInput 直打中文会串字/把尾巴打乱**，别用。
4. 注意：`set_value` 对 Chromium webview 的 Edit **无效**（无 ValuePattern），只对原生控件有效。
5. 「**自主声明**」→ 选「内容由AI生成」（单选）→ 确定。
6. 封面：「Ai智能推荐封面」缩略图点一下 → 弹「是否确认应用此封面？」→ 确定。
7. 发布设置默认就是 **公开 / 允许保存 / 立即发布** ✓。填完点底部「**发布**」→ 按钮变「正在发布」→ 页面跳 内容管理，新作品状态应为「**审核中**」（这就是成功标志，不是失败）。
8. 表单很长：发布按钮在视口外时元素 bounds 为 0，点击无效。**滚动**：`scroll` 动作在同 pid 多窗口时会被拒 → 改用 `drag` 拖右侧滚动条（`from_coordinate`→`to_coordinate`，截图像素空间），或在页面点一下再按 `pagedown`。
9. 元素索引点击最可靠（`coordinate` 参数是**截图像素**空间，不是 native）；同 pid 多窗口时 scroll 等动作要能区分窗口。

## 评论运营

- 发布后 **2 小时内回复所有评论**（平台看好互动），回复里带一个追问，把对话拉长。
- 置顶一条引导评论（提一个问题，不是广告）。
- 每天固定 10 分钟看评论热词 → 就是下一条选题。

## 复盘（每周）

只看三个指标：完播率（<30% 就改前 3 秒）、互动率、转粉率。数据下滑就换钩子，不改赛道。

## 坑

- 别把主人的项目细节当素材（隐私红线）；涉及就抽象成「某个监控项目」。
- 别用英文音色念中文（`tts.edge.voice` 必须是 `zh-CN-*`），听着像机器人。
- `hermes config set` 改配置，别手改 `config.yaml`。
- 上传/发布属于对外动作：**成片先用微信发给主人过目**，确认后再用客户端发布，别自动发（主人说过一次“劣质”——图卡+TTS 这种拼贴式片子只配做草稿，正式发之前必须过目）。
