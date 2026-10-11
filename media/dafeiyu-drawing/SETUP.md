# 从零搭（换机器 / 给别人用）

整条链路：**提示词 → 本地 ComfyUI（Z-Image-Turbo）→ PNG → 发回聊天**。

## 硬件 / 系统
- NVIDIA GPU（本机 RTX 5060 Ti 8G；NVFP4 量化版在 Blackwell 上原生加速，显存占用小）
- Windows 可直接用 ComfyUI 的 portable 包；Linux/mac 用常规 ComfyUI 安装即可

## 装
1. **ComfyUI**：portable 包（github.com/comfyanonymous/ComfyUI releases，选 portable）
   —— 或你自己的 ComfyUI 环境。建议用新版（要认识 `lumina2` 的 CLIPLoader）。
2. **三个模型文件**（源自 HF `Comfy-Org/z_image_turbo` 的 split_files；国内可换 hf-mirror.com）：

   | 文件 | 放哪 |
   |---|---|
   | `z_image_turbo_nvfp4.safetensors`（约 4.5GB） | `ComfyUI/models/diffusion_models/` |
   | `qwen_3_4b_fp4_mixed.safetensors` | `ComfyUI/models/text_encoders/` |
   | `ae.safetensors` | `ComfyUI/models/vae/` |

3. 启动参数：**端口 8189**（避开别的 ComfyUI 实例）：
   ```bat
   python main.py --port 8189
   ```
4. `scripts/image_service.py` 头部三个常量改成你机器的：
   ```python
   HERMES_HOME = Path(r"...\AppData\Local\hermes")   # 你的 Hermes 目录
   BRIDGE     = HERMES_HOME / "scripts" / "qq-bridge.py"  # 或者删掉发送段，自己接
   ROOT       = Path(r"...\ComfyUI_windows_portable")
   ```
   —— 不接 QQ 的话：把 `import qq-bridge` 那段换成你自己的发送方式；纯出图只用 `build_workflow()` + `generate()`。

## 跑
```bash
<python> scripts/image_service.py <umo> "一只橘猫在屋顶看夕阳"
```
（`<umo>` 是发送目标标识；干跑/自己发图的话随便填。）

## 已知坑
- **别和视频 ComfyUI 共用端口/实例**：模型加载会互相挤显存，且视频脚本会误判就绪。
- 空转的 ComfyUI 吃 ~4.5GB 显存 → 一定要开「空闲自关」（`image_idle_shutdown_s`）。
- 图生图的原图要么本地文件要么先下载；放 `input/` 后用 `LoadImage` 文件名引用。
- 提示词先过内容闸门再排队（本地也要守规矩：别画违规内容）。
