---
name: dafeiyu-singing
description: Use when 大肥鱼点歌/翻唱 (local singing pipeline).
---

# 大肥鱼翻唱（本地点歌）

用户说「唱《歌名》」/「唱首歌」→ 自动找歌 → 换成大肥鱼嗓 → 把 mp3 发回聊天。全程本地，不用任何 API。

> 换机器 / 给别人用：**代码已随技能打包在 `scripts/`**（sing.py / sing_service.py / fetch_bili.py …），从零搭建步骤见 `SETUP.md`。

## 位置
- 项目：`C:\Users\32672\Apps\dafeiyu-sing\`（`sing.py` 主流水线 / `sing_service.py` QQ 点歌服务 / `send_to_qq.py` 发文件 / `songs/` 曲库 / `output/` 成品 / `work/` 中间产物；**项目无 git——改完把改动文件同步到本技能 `scripts/` 副本**）
- 代码：`seed-vc-main/`（Plachtaa/Seed-VC，零样本歌声转换，**不用训练**）
- 独立 venv：`.venv`（torch 2.7.0+cu128），**不要**和 GPT-SoVITS 的 venv 混用
- 参考音：`refs/dafeiyu_ref20s.wav`（从 demucs 分离出的干净人声切 20 秒）
- 桥接侧：`qq-bridge.py` 里的 `_looks_like_song_request` / `_song_file_for` / `_start_singing`；日志 `logs/sing.log`

## 点歌语法（2026-10-12 扩充）
- 触发词：`唱(首歌|首|一首|个歌|一个|一下|支|曲|情歌|老歌|快歌|慢歌|甜歌|伤感歌|英文歌|日语歌|粤语歌|儿歌|歌|这个|这首|这首歌|下这个)` / `翻唱(《|“|"|「|这个|这首|一下)` / `来(一首|首歌|首)` / `给本?鱼唱`。（2026-10-15 按群友大白话扩——之前「可以唱这个吗」「翻唱这个」全漏识别，机器人只能念歌词假唱）
- **抠歌名时只吞量词、不吞题材词**：`_CONSUME`（无题材词版）负责裁掉「唱/唱首/唱一首」，否则「唱情歌」会把「情歌」当量词吃掉→变成随机点歌。
- **题材词**（情歌/老歌/伤感…）靠 B站 打分随便挑一首；名字≤8字才当题材，否则当歌名。
- **裸歌名不触发（接自然语序点歌要当心）**：「唱江南style」「唱《X》」这类**唱后直接跟歌名、没有量词**的写法不在触发词内——bridge 不会派单；服务收到这种文本会 **rc=2 静默退出**（`parse_request` 返回 None → `return 2`、零日志——是「这不是点歌请求」的正常应答，不是崩溃）。**替人代跑时在命令里补量词**：`sing_service.py <umo> "唱一首江南style"`（→ kind=name）。**rc 语义**：0=唱完 / 1=已排队 / 2=非点歌请求 / 3=闸门拦——看到 2 别再换写法反复找 bug。
  （想支持裸名得在 bridge 和 service 两处同时加触发词、并防「唱得不错」这类误触的回归；没做之前按上面的补量词法走。）
- 服务启动时清代理环境变量（本机 shell 代理指向自建中转，中转挂了会掐死 B站搜索）。

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
- **主人在玩 Steam 游戏时一律先不唱**：读 steam_monitor 的 `last_states.json`（兜底直连 SteamAPI），把具体游戏名塞进回合提示，让模型用幽默口语解释“显卡被征用”、让来人过半小时再来。**只认主人自己的号（76561199857219177）**——另一个号（冀C）在别人的电脑上，它玩不玩都不算、不拦（2026-10-12 修：之前把冀C的游戏误判成主人在玩，挨过骂）。
- 曲库里没有的：**谁点都转带工具的回合去扒**（搜 B 站+下载；主人 2026-10-08：外人点没有的歌也开放下载、但只限唱歌这一条路）；提示里必须写 `C:/` 正斜杠路径，写 `/c/…` 会被原生程序拒。
- 桥接等 Hermes 的上限必须 ≥1800s：下载+分离+转换动辄几分钟，`request_timeout_s=300` 会报 `timed out` 并被回复成“Hermes 这边出错了”。

## 硬坑（都踩过）
- **控制台是 GBK，歌名带 emoji 会把流水线整崩/整冻**（`🥳` 让 service 的 print 直接 UnicodeEncodeError；demucs 的 tqdm 块字符让 pipe 解码抛错）。已在 `sing.py` / `sing_service.py` 修：开头 `sys.stdout/stderr.reconfigure(encoding='utf-8', errors='replace')`；所有 `subprocess.run(text=True)` 加 `encoding='utf-8', errors='replace'`；`_clean_env()` 与 `run()` 给子进程塞 `PYTHONUTF8=1` + `PYTHONIOENCODING=utf-8`。
- **demucs 在“服务链子（service→sing.py→demucs）里”可能冻死**：2026-10-14 晚实测两次——进程活着但 CPU 不涨、无输出、无子进程，杀后再跑又冻；而**前台单跑同一条 demucs 命令 17 秒成功**。根因未定。快速恢复：① 前台手工 `GSV_PY -m demucs --two-stems=vocals -n htdemucs -o .../work/separated "<歌>"`（约十几秒）；② `sing.py --song "<歌>" --name xxx` 复跑——`separate()` 见 `vocals.wav` 已存在会跳过 demucs，直进 Seed-VC+混音；③ 手工 `upload_group_file` 上传成品。遇冻别硬等（服务端 timeout=3600 会挂一小时），**但先确认是不是真冻再动手**：看 `work/separated/htdemucs/<歌>/` 有没有新产物、隔半分钟再看一次；慢 ≠ 冻——3 分半的歌分离跑 4~5 分钟也正常（阶段切换时 GPU 采样会跌到个位数 %，会误导）。把健康的慢跑杀掉重启等于白等一场；判冻至少两条都成立：产物目录长时间无文件更新 + 进程 CPU 时间不涨。 **杀这类链子只按列出来的显式 PID 杀**（先 `Get-CimInstance … Select ProcessId,CommandLine` 列表，再逐个 `Stop-Process -Id`）——**别把 `*dafeiyu-sing*` 这种路径模式交给 Stop-Process：你自己热 shell 的命令行里也含这条路径，会连坐把自己杀掉**（实测命令半路暴毙）。
- **yt-dlp 的 `--audio-format mp3` 转换失败会静默留下 m4a**（ffmpeg 不在 PATH 时）→ demucs 读 m4a 报 `no channel` → 整链崩。已修（2026-10-15）：下载指定 `--ffmpeg-location` + 下完兜底硬转 mp3 + demucs 前预转 wav。别只信下载返回码，看 `songs/` 里落的是不是 mp3。
- **用户直发视频/音频（非 B站链）**：先 `ffmpeg -y -i <file> -vn -ac 2 -ar 44100 -c:a pcm_s16le <wav>` 抽成 wav 再走链路（mp4/m4a 别直接喂 demucs，同一个 no-channel 坑）；顺手 `-b:a 320k` 存一份进 `songs/`（带歌名，以后点歌可命中）；成品发群后必须回读 `get_group_msg_history` 验证文件+语音。复用脚本：`scripts/cover_local.py`（抽 wav → demucs 含 CPU 兜底 → sing.py 跳过 demucs → 发群 + 收尾语音 + 回读；用桥接 venv 跑，参数=输入文件 输出名 [群号]）。
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
- **网易云分享链接救急直下（2026-10-16 实战《她去美国买了骚猪》）**：163cn.tv 短链先 `curl -sIL` 解出 song id（y.music.163.com/m/song?id=…）；再 `curl -sL --noproxy '*' -e https://music.163.com/ -o "…mp3" "https://music.163.com/song/media/outer/url?id=<id>.mp3"` 匿名下到完整 128k 全曲（实测 1.9MB/119s）——没上B站的梗歌走这条比搜B站快；下完量 duration/电平，确认不是试听片段。
- **手工直跑 sing_service 时输出不进 logs/sing.log**（那是桥接的重定向）；别因为 sing.log 没新行就以为没跑——看 `output/` 新文件 + 进程列表为准。
- **待修缺口（2026-10-16）**：网易云「分享卡片」消息（文本含 163cn.tv 链接但无「唱」字）不会被 bridge 认成点歌单；qqguest 会嘴答「本鱼去学」但不真排单 → 已记 scripts/INBOX.md。
- **验证下到的真是这首歌**（不能靠耳朵）：拿兜底源做指纹 —— `librosa.feature.chroma_cqt` 逐帧 z-score 后在 ±40s 搜最大相关，0.9x 即同一录音。另外 0.5s 窗口 RMS 扫首尾，实测这首是「0~11s 微弱环境音、11~18s 全静音、18.5s 起才是音乐、246s 后静音」，所以 `-ss 18.2 -to 246.5` 裁完才 228s。
- **成品只发 QQ 不发微信**（用户明确要求）。群用 `upload_group_file`，私聊用 `upload_private_file`。
- **必须后台跑**：整链 >3 分钟，用 `terminal(background=true)` 起（前台默认 180s 就掐断）。任务被掐断会残留 `work/sing.lock`，之后所有点歌都被「已有任务在跑，跳过」**静默吞掉**（连 ack 都不发；2026-10-15 因此被主人投诉「让唱歌都不听了」）→ 快速恢复 `rm -f work/sing.lock`；锁现在 30min 过期自动清（同日补）。群抱怨「点了没反应」先查 `logs/sing.log` 有没有「跳过」。**忙时已不再吞单**（2026-10-15）：新单写进 `work/sing_queue.txt` + 回一句「先排上」，当前唱完自动接力（DETACHED 拉起，不连坐）。**取消排队中的单**：杀「编排脚本」本体即可（`taskkill /F /PID <pid>`，**别加 /T**——/T 会把正在唱的那首也连坐杀掉）；`work/sing_queue.txt` 里的待唱条目直接删行。
- **进程形态别数错**：同一阶段常见成对进程（`.venv\Scripts\python.exe` 壳 + 它拉起的 uv 基础解释器，命令行相同、父子串联）=**一个**逻辑进程；一次完整点歌=service→sing.py→demucs 三层链，全是正常形态，别当重复进程去「清理」。怀疑重复时看 ParentProcessId 的串联关系，不要凭数量下结论。
- **重启桥接会连坐杀掉正在唱的的唱歌**：sing_service 曾是桥接的子进程，`taskkill /T` 重启桥接时被一起杀 → 死锁 + 点的那首歌永远没下文（2026-10-15 踩）。已修（唱歌进程 DETACHED_PROCESS）；重启桥接前仍建议先瞄 `logs/sing.log` 有没有歌在跑。
- **交付验证（别只信脚本的 `上传: True`）**：NapCat 不支持 `get_group_file_list`/`get_group_files`（retcode 1404），改用 `napcat_call('get_group_msg_history', {'group_id':…, 'count':30})` 回读，看到自己那条 `type=file` 的 `[CQ:file,file=…mp3]` + 紧跟着的语音才算真发出去；最后再 `.venv/Scripts/python.exe f0_cmp.py` 量音高（唱歌输出应≈TTS 语音输出，都在 D4 附近，否则就是参考音/音区又跑了）。**收尾语「唱好了…」可能在上传成功后丢失**——结尾 `say` 在 `_make_voice` 抛错时只记日志、不落文字兜底；回读历史时连它一起核对，缺了就用桥接 venv 手工补一条语音（或文字）。

## 加歌
把音频（mp3/flac/wav）丢进 `songs/`，文件名带歌名即可 —— 点歌时按歌名子串匹配，命中就直接唱（跳过下载）。

## 语音条双发（2026-10-16 定）
- 每首歌唱完：**语音条 + 文件 都发**。sing_service 在 upload 后新增：`b.send_voice(umo, mp3)`（NapCat 收到音频文件后**内置 ffmpeg/silk 自动转码后再发**，直接传 mp3 路径即可；桥接的 `send_voice` 会把它转成 `file:///` URI 再塞 record 段）。
- **时长放心（实测到底）**：2/5/6/**10 分钟** 语音条全部原样送达（反解时长 119.0/300.0/359.9/**599.9s**，retcode 均 0）——「5分钟上限」传言不成立（那是官方客户端录音的事，NapCat 发送无此限）。流水线无需加限；真遇超长（>10min）再测再议。
- **验证姿势**（别只信 retcode）：`napcat_call('get_record', {'file': '<消息里的file>', 'out_format': 'mp3'})` 拿回本地 mp3 → `ffprobe` 量 duration/bit_rate；或用 `get_group_msg_history`/`get_friend_msg_history` 回读历史看 record 消息在不在。
- 私聊测试可用 `send_private_msg` 到 1568468；发送脚本模式 = 载入 qq-bridge 模块（exec_module）+ `mod.napcat_call(...)`，用桥接 venv 跑。
