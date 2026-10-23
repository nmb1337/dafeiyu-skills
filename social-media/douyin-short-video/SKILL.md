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

- **游戏高光/击杀集锦/卡点 montage 不走本技能**——那是 `video-montage-editing`（ffmpeg 卡点流水线：光流慢镜、节拍对齐、字幕/转场、60fps 验收）。本技能只管大肥鱼账号的口播/图文片。
- 15–45 秒；**前 3 秒钩子**（反常识结论或痛点提问），例：「我家 AI 昨晚把自己服务器搞挂了，然后它自己修好了」。
- 中段：一件具体的事 + 一个可视证据（日志/画面/前后对比），别空口讲道理。
- 结尾：一句互动引导（「你想让我下次拿哪个活儿练手？」）。
- 发布时段：18:00–19:00 最佳，12:00–13:00 次之；每周 3–5 条起步，别断更。

## 剪映草稿自动化（本机已打通，2026-10-14 实测）

**优先用剪映出片，不要纯 ffmpeg 拼贴**（图卡+TTS 拼贴被主人说过「劣质」）。

> 例外：**游戏高光/卡点 montage 用 `video-montage-editing` 的 ffmpeg 流水线**（帧级精度、光流慢镜、节拍对齐），剪映 11.6 只用来当「可手改的工程」附加物。

- 工具：`C:\Users\32672\Apps\jianying-editor-skill`（GitHub luoluoluo22，v1.7.0，内嵌 pyJianYingDraft）。
  独立 venv：`.venv`（uv 建的 Python 3.12；装依赖必须用清华镜像 + `NO_PROXY=*` 直连，
  走 7899 中转下 playwright/opencv 这种大包会 TLS 断流）。uv 在 `C:\Users\32672\.astrbot_launcher\components\uv\uv.exe`。
- **跑它的脚本前必须把 ffmpeg/ffprobe 加进 PATH**（它用 ffprobe 解析媒体，缺了会 FileNotFoundError）：
  `export PATH="/c/Users/32672/AppData/Local/hermes/tools/ffmpeg-9.0.1-win32-x64/bin:$PATH"`
- 入口：`sys.path.insert(0, "<skill>/scripts"); from jy_wrapper import JyProject`；
  草稿根目录 `C:\Users\32672\AppData\Local\JianyingPro\User Data\Projects\com.lveditor.draft`。
- **剪映 11.6 兼容性已实测通过**：生成的草稿是明文 `draft_info.json`（没加密），剪映能列出来、双击能进编辑器，
  视频/字幕/轨道全部正常。竖屏项目初始化时要显式传 1080x1920（默认是横屏 1920x1080）。
- **剪映不会自动刷新草稿列表**：生成草稿后必须重启剪映（或进出一次旧草稿）才看得到。
- 驱动剪映 GUI：用 computer_use 按 `window_id` 抓窗口（**能抓被遮挡的窗口**，不用 bring-to-front）；
  双击草稿用 `coordinate=` 传**截图/窗口像素**（driver 自己换算屏幕坐标，实测 `window-pixel → screen-point` 正确）。
  注意编辑器开新窗后旧 window_id 失效，要重新 list_windows。
- 官方自检 `scripts/api_validator.py` 会真生成一个 Diagnostic_Test 草稿——这是最快的环境体检方式。
- **API 速查（v1.7）**：`JyProject(name, width=1080, height=1920, overwrite=True)`（竖屏必须显式传宽高）；
  `add_media_safe(path, start_time, duration, track_name, source_start)`（视频/音频，会自动把素材拷进草稿目录）；
  `add_text_simple(text, start_time, duration, track_name)` —— **默认字号 5 + 黑描边；传 font_size/color_rgb/transform_y 会被静默丢掉**，
  样式要走 `style=`/`clip_settings=`；`add_transition_simple(名字, video_segment, duration)` 给片尾加转场。
  时间字符串 `"3.5s"` 或微秒 int 都行；每步返回值非空即成功，末尾必须 `project.save()`。
- **图片不被支持**（media_ops 只认视频/音频扩展名）→ 先把图转成 mp4 再用：
  `ffmpeg -loop 1 -i x.png -t 4 -r 30 -filter_complex "[0:v]split[bg][fg];[bg]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,gblur=sigma=40[b];[fg]scale=1000:-2[f];[b][f]overlay=(W-w)/2:(H-h)/2,format=yuv420p[v]" -map "[v]" …`
 （模糊背景+居中，竖屏不露黑边）。
- **ffmpeg 9.0.1 这个构建没有 `-filter_complex_script`**：长滤镜串（带中文 drawtext）写进文件再用
  `-filter_complex "$(cat file)"` 内联传。drawtext 中文字体：`fontfile='C\:/Windows/Fonts/msyh.ttc'`。
- **网页素材录制**（面板/网页演示）：自己写 playwright 脚本（自带 web_recorder 是等 `window.animationFinished` 信号的，
  不适合实时页面）。**viewport=540x960 + device_scale_factor=2 + record_video_size=540x960** 录下来最稳
  （把 record_video_size 填成大画布会变成灰底 padding，playwright 不缩放），再用 lanczos 升到 1080x1920；录完 webm→mp4。
  浏览器内核装法：`PLAYWRIGHT_DOWNLOAD_HOST=https://npmmirror.com/mirrors/playwright/ .venv/Scripts/python.exe -m playwright install chromium`
  （官方 CDN 在国内慢/易断，镜像快很多）。
- **导出环节（2026-10-14 实测）：11.6 的自动导出走不通 → 导出请主人手动点**。
  剪映 11.6 是 QML 界面，UIA 控件树完全为空（uiautomation 遍历=0 节点），pyJianYingDraft 的
  `JianyingController.export_draft` 必报「未找到名为X的剪映草稿」（它靠 `HomePageDraftTitle:`
  AutomationId 找草稿，11.6 不暴露）；Ctrl+E 等合成快捷键也被 QML 无视。**成片导出=人工：
  右上角蓝色「导出」→ 设置全默认 → 确认**。这条只影响导出，草稿生成/打开不受影响。
- **cua 截图降采样**：编辑器窗口宽 >1456px 时 cua 返回的截图是缩小过的（1920x1032 → 1456x782），
  `coordinate=` 换算要乘回比例（≈1.32，看 som 的 bounds 与截图尺寸比值）。主页窗口 <1456px 时 1:1，
  直接传截图像素。**同 pid 出现第二个窗口（如编辑器+助手窗）后，后台点击可能投到非目标窗口**，
  点击前先 list_windows 确认，或只在单窗口状态下操作。
- **生成草稿后剪映看不到？重启剪映**（它不实时刷草稿列表）；用 computer_use 按 window_id 截草稿列表确认，双击打开验证。
- **时间轴按旁白实测时长排（先定音、后配画）**：先把口播稿逐句合成、`ffprobe` 量出每句真实长度，再拿这些数字摆画面/字幕的起止——改稿只重录那一句，画面跟着挪。旁白做完先做一条连播样片给主人听（本地播一遍 + 附文件，见 `voice-cloning`），过了再往下做，不然白排一遍时间轴。
- **演示素材（真实聊天/操作画面）外拍**：机器人不能自己触发自己，得请主人本人按脚本发指令；QQ 客户端的窗口怎么从托盘调出来、录哪一块、什么时候开录，见 `onebot-qq-bridge` 技能。

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

## AI 漫剧生产线（2026-10-17 跑通：MiniMax-H3 本地视频管线）
- **视频 ComfyUI 在盘根 `C:\ComfyUI_windows_portable`**（不是 Apps 那套生图的）：MiniMax-H3 模型 + `h3-studio` 一键出片服务（`python_embeded\python.exe h3-studio\server.py`，端口 **8799**；API：`POST /api/start`{global_prompt, seconds, width, height, crossfade, steps, enhance, fps60, segments:[{prompt, image(dataURL base64), image_name, chain}]}、`GET /api/status?job=`、`GET /api/video?job=`）。8188 由服务自动拉起、勿用于生图；成片自动存 Downloads。
- **分工**：Hermes 备物料（剧本/分镜/角色立绘/完整提示词/接口参数）→ **VS Code agent 全程自动制作**（实测成片 30.3s / 1080×1920 / 60fps / 烤字幕）。项目模板 `Documents\AI漫剧三姐妹\`（docs/需求书.md、refs 立绘、out 成片+结果.txt）。
- **流程**：① 关键帧＝角色立绘过 FLUX Kontext 换场景（英文指令＋保持人物不变），多角色同框用 Z-Image-Turbo 长提示词；② 5 段竖屏 544×960（清晰档），逐段挂关键帧（chain=true 图=段尾 / false=段首）；③ **坑：链式段会裁 56 帧**——seconds=6 只能出 ~24s，要 30s 用 seconds=8＋crossfade=16；④ 后期 ASS/libass 烧字幕＋片尾＋AI生成标记＋lanczos 升 1080×1920。
- **完成播报**：monitor 模式 cron 盯 out/ 产物出现即唤醒发微信（模板 `scripts/manga-done-watch.py`）。
