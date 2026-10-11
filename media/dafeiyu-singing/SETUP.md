# 从零搭（换机器 / 给别人用）

代码都在 `scripts/`。整条链路：**歌曲音频 → demucs 分离人声 → Seed-VC 换成「大肥鱼」嗓 → 与伴奏混音 → mp3**。

## 硬件 / 系统
- NVIDIA GPU（本机 RTX 5060 Ti 8G；Blackwell 是 sm_120 → **torch 必须 cu128**）
- ffmpeg / ffprobe 在 PATH（或改 `sing.py` 里的路径）
- Python 3.11+ → **独立 venv**（别和别的 torch 环境混用）

## 装
1. 拿 Seed-VC 源码：`github.com/Plachtaa/Seed-VC`（clone 或下 zip，放 `seed-vc-main/`）
2. 建 venv 并装依赖：照 `setup_env2.sh` 的写法 —— torch 走阿里云镜像
   `https://mirrors.aliyun.com/pytorch-wheels/cu128/`；**装的时候去掉代理**（走代理 TLS 会摔：`cannot decrypt peer's message`）。
3. 下模型（放 `checkpoints/hf_cache/` 下对应目录；国内把 huggingface.co 换 hf-mirror.com）：
   - `DiT_seed_v2_uvit_whisper_base_f0_44k_bigvgan_pruned_ft_ema_v2.pth`（约 782MB，源自 HF `Plachta/Seed-VC`）
   - `rmvpe.pt`（约 172MB，源自 HF `lj1995/VoiceConversionWebUI`）
   - campplus（HF `funasr/campplus`，首次跑会自动下；网络差就手动放进去）
4. 参考音 `refs/<名字>.wav`：一段**干净人声** 8~20 秒。
   **要点：唱歌和说话（TTS）必须用同一段参考音** —— 音区不一致就会出现「唱的和说话不像同一个人」。

## 跑
```bash
.venv/Scripts/python.exe sing.py --song "C:/path/to/song.mp3" --name my_out
# 成品 → output/my_out.mp3
```
- `--song` **必须绝对路径**（别用 `/c/...` 这种 MSYS 路径，原生程序不认）。

## 接到聊天里（可选）
本机是 `sing_service.py` + qq-bridge.py 的 `_start_singing` 派单（对所有人开放；主人在打游戏时先劝退）。
换个 Hermes/平台：让 agent 直接把 `sing.py` 当普通脚本调即可；`send_to_qq.py` 演示了成品怎么发进 NapCat，
换成自己的发送通道就行。

## 已知坑（详细见 SKILL.md）
- B 站下的歌常带首尾静音/节目片段：先用 librosa 量 RMS 找真正在唱的区间再裁（`fetch_bili.py` 里已有）。
- demucs 没有 `--name` 参数；输出固定在 `<work>/htdemucs/<歌名>/`。
- 转换**保调**，别再给伴奏移调（chroma 对齐会因八度歧义给出错的 -11 半音，已弃用）。
- 长曲子全程 5~7 分钟很正常（分离 ~30s + 转换 ~2min/首）；调用方等待上限要给足（≥1800s）。
