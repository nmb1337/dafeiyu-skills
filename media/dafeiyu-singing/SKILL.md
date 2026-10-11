---
name: dafeiyu-singing
description: Use when 大肥鱼点歌/翻唱 (local singing pipeline).
---

# 大肥鱼翻唱（本地点歌）

用户说「唱《歌名》」/「唱首歌」→ 自动找歌 → 换成大肥鱼嗓 → 把 mp3 发回聊天。全程本地，不用任何 API。

> 换机器 / 给别人用：**代码已随技能打包在 `scripts/`**（sing.py / sing_service.py / fetch_bili.py …），从零搭建步骤见 `SETUP.md`。

## 位置
- 项目：`C:\Users\32672\Apps\dafeiyu-sing\`（`sing.py` 主流水线 / `sing_service.py` QQ 点歌服务 / `send_to_qq.py` 发文件 / `songs/` 曲库 / `output/` 成品 / `work/` 中间产物）
- 代码：`seed-vc-main/`（Plachtaa/Seed-VC，零样本歌声转换，**不用训练**）
- 独立 venv：`.venv`（torch 2.7.0+cu128），**不要**和 GPT-SoVITS 的 venv 混用
- 参考音：`refs/dafeiyu_ref20s.wav`（从 demucs 分离出的干净人声切 20 秒）
- 桥接侧：`qq-bridge.py` 里的 `_looks_like_song_request` / `_song_file_for` / `_start_singing`；日志 `logs/sing.log`

## 跑一条
```bash
cd /c/Users/32672/Apps/dafeiyu-sing
.venv/Scripts/python.exe sing.py --song "songs/xxx.mp3" --name my_out   # 成品 output/my_out.mp3
.venv/Scripts/python.exe sing_service.py "napcat-qq:FriendMessage:1568468" "唱《起风了》"   # 走完整点歌链路
```
实测《起风了》：demucs 分离 31 秒 + Seed-VC 转换约 2 分钟（5060 Ti 8G）；实测《原来》(232s 全曲)=整链 6.5 分钟（10:29:27 开跑 → 10:35:51 出成品）。

## 参考音：必须和说话(TTS)用同一段！
唱歌和说话的嗓"不是一个人"的根因就在这：
- TTS 用 `C:\Users\32672\Apps\GPT-SoVITS\refs\dafeiyu_voice.wav`（8 秒，中位 297Hz≈D4）
- 一开始唱歌用的是自己另切的 `refs/dafeiyu_ref20s.wav`（中位 243Hz≈B3）
- Seed-VC 的 `--auto-f0-adjust` 会把歌声往**参考音的音区**拽 → 输出比原唱低 6.6 个半音（216Hz A3），
  既听着像另一个人，也和伴奏不在一个调上。
- 换成同一段参考后：输出 307.9Hz≈D♯4，与原唱只差 -0.5 个半音，和说话嗓（301.7Hz）一致。

验证方法（别靠耳朵）：`librosa.yin` 量中位 F0，比同一句的中位音高；
`resemblyzer` 的 speaker embedding 余弦只能看"是不是同一个人"（都在 0.8 上下，不够分辨），**音高才是关键**。
混音时**不要**给伴奏乱移调：这个转换本身保调，`align_mix.py` 的 chroma 对齐会因为八度歧义给出 -11 这种值（错的），已弃用。

## 点歌规则（bridge 侧）
- **对所有人开放**：群里/私聊任何人的点歌都派单（曲库命中或发链接即唱）。
- **主人在玩 Steam 游戏时一律先不唱**：读 steam_monitor 的 `last_states.json`（兜底直连 SteamAPI），把具体游戏名塞进回合提示，让模型用幽默口语解释“显卡被游戏征用”、让来人过半小时再来。
- 曲库里没有的：主人 → 转带工具的回合去扒（提示里必须写 `C:/` 正斜杠路径，写 `/c/…` 会被原生程序拒）；外人 → 让他发链接。
- 桥接等 Hermes 的上限必须 ≥1800s：下载+分离+转换动辄几分钟，`request_timeout_s=300` 会报 `timed out` 并被回复成“Hermes 这边出错了”。

## 硬坑（都踩过）
- **`--song` 必须给绝对路径**（已修：`separate()` 开头 `song = os.path.abspath(song)`）。demucs 在 `cwd=work/` 下跑，相对路径会让它找不到文件、只报「找不到人声文件」。
- **B站视频常带首尾静音/节目片段**：下完先用 `librosa` 量每 10 秒的 RMS，找出真正在唱的区间再用 ffmpeg 裁掉首尾 —— 实测《野子》(我是歌手 Live) 全长 403s，只有 30~294s 有人声，裁完省一半转换时间。
- **群点歌的发送**：成品用 `upload_group_file`(group_id) / 私聊用 `upload_private_file`；开跑前想先吱一声，直接 `http_json(astrbot_base_url + '/api/v1/im/messages', {'umo':…, 'message':…}, headers=Bearer astrbot_api_key)` 发文字（别用 send_qq，它会调 TTS 抢 GPU）。
- **torch 必须 cu128**：5060 Ti 是 Blackwell(sm_120)，老 CUDA 跑不了。
- **装包要 unset 代理**：本机 shell 挂着 HTTP(S)_PROXY=127.0.0.1:7899，走它下大文件会 `cannot decrypt peer's message`（TLS 被掐）。走阿里云镜像 + `env -u HTTP_PROXY -u HTTPS_PROXY -u ALL_PROXY`：
  `uv pip install --python .venv/Scripts/python.exe --find-links https://mirrors.aliyun.com/pytorch-wheels/cu128/ torch==2.7.0+cu128 torchaudio==2.7.0+cu128`
- **hf 模型也脱代理**：`HF_ENDPOINT=https://hf-mirror.com` 且 unset 代理（模型在 `seed-vc-main/checkpoints`）。
- **demucs 没有 `--name`**：写成 `--name X` 会被当模型名报 `is neither a single pre-trained model`。输出固定是 `<out>/htdemucs/<歌名不含扩展名>/{vocals,no_vocals}.wav`。
- **resemblyzer 装不上**：它依赖要编译的 `webrtcvad` → 先装 `webrtcvad-wheels`，再 `--no-deps resemblyzer`。
- **B站搜索走不通**：`yt-dlp bilisearch` 匿名 412，`--cookies-from-browser` 被 Chrome 加密挡回。**知道 BV 号后先试 yt-dlp**（2026-10-08 实测 `env -u HTTP_PROXY -u HTTPS_PROXY -u ALL_PROXY uvx yt-dlp -f bestaudio -x --audio-format  mp3 <BV完整链接>` 成功下到《原来》7.4MB/3:52，yt-dlp 2026.08.19，无需 cookie）；若报 `[BiliBili] Unable to extract initial state`（部分视频会踩），改走项目里的 `fetch_bili.py`：`x/web-interface/view?bvid=` 拿 cid → `x/web-interface/nav` 拿 wbi img/sub key → 自算 mixin_key（64 位乱序表）签 `x/player/wbi/playurl?fnval=4048` → 取 `dash.audio` 里 bandwidth 最大的 `baseUrl` 下载（必须带 UA + `Referer: https://www.bilibili.com/video/<BV>/`）。非 wbi 的 `player/playurl` 全返回 `-404 啥都木有`。下完 ffmpeg 转 320k mp3 丢 `songs/`（文件名带完整歌名，点歌按子串匹配）。
- **找 BV 号**：`web_search`「歌名 bilibili」拿视频页链接，认准原曲那一期（合唱/新春会等场景官方投稿最干净）。快捷法：用 browser 开 `search.bilibili.com/all?keyword=<歌名>&order=click`，从 `.bili-video-card` 抓标题/BV/时长/播放量；**别选标题带「伴奏」的**（Seed-VC 要人声），选完整原唱版。
- **歌名歧义先定版本**（如《原来》有南征北战NZBZ《青春派》插曲、林俊杰、林东/程佳佳/赵乃吉等版本）：curl（`--noproxy '*'`，带 UA）打网易云 `music.163.com/api/search/get/web?s=歌名&type=1&limit=15` + QQ音乐 `c.y.qq.com/soso/fcgi-bin/client_search_cp?w=歌名&format=json&n=15`（带 `-H 'Referer: https://y.qq.com/'`）看版本，再按 B站播放量 + 曲库里已有的歌手口味取舍；拿不准就在回复里点一句版本名（一句带过，不逼用户选）。
- **兜底源**：网易云外链 `https://music.163.com/song/media/outer/url?id=<songid>.mp3` 可匿名直连（302 到 CDN，约 128k，带 `-e https://music.163.com/`），只当备份/验证用。
- **验证下到的真是这首歌**（不能靠耳朵）：拿兜底源做指纹 —— `librosa.feature.chroma_cqt` 逐帧 z-score 后在 ±40s 搜最大相关，0.9x 即同一录音。另外 0.5s 窗口 RMS 扫首尾，实测这首是「0~11s 微弱环境音、11~18s 全静音、18.5s 起才是音乐、246s 后静音」，所以 `-ss 18.2 -to 246.5` 裁完才 228s。
- **成品只发 QQ 不发微信**（用户明确要求）。群用 `upload_group_file`，私聊用 `upload_private_file`。
- **必须后台跑**：整链 >3 分钟，用 `terminal(background=true)` 起（前台默认 180s 就掐断）。被掐断后会残留 `work/sing.lock`，下次跑被「已有任务在跑，跳过」挡住 → 开跑前先 `rm -f work/sing.lock`。
- **交付验证（别只信脚本的 `上传: True`）**：NapCat 不支持 `get_group_file_list`/`get_group_files`（retcode 1404），改用 `napcat_call('get_group_msg_history', {'group_id':…, 'count':30})` 回读，看到自己那条 `type=file` 的 `[CQ:file,file=…mp3]` + 紧跟着的语音才算真发出去；最后再 `.venv/Scripts/python.exe f0_cmp.py` 量音高（唱歌输出应≈TTS 语音输出，都在 D4 附近，否则就是参考音/音区又跑了）。

## 加歌
把音频（mp3/flac/wav）丢进 `songs/`，文件名带歌名即可 —— 点歌时按歌名子串匹配，命中就直接唱（跳过下载）。
