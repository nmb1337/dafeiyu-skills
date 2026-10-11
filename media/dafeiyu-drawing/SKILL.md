---
name: dafeiyu-drawing
description: Use when 大肥鱼画图/生图 (local ComfyUI Z-Image-Turbo pipeline).
---

# 大肥鱼画图（本地生图）

QQ 里说「画一张…」/「生成…图」/「把这张图改成…」→ 本地 ComfyUI 出图 → 发回聊天。全程本地，不用任何 API。

## 关键设定
- **端口 8189**（图片专用）。8188 是视频 ComfyUI（MiniMax-H3）的端口，**绝不能共用**（视频脚本靠「8188 有应答」判断自己就绪）。
- **按需拉起**：生图不常来，而 ComfyUI 空转吃 ~4.5GB 显存 → 来了才开；画完闲 `image_idle_shutdown_s` 秒自动关，把显存还给主人。
- **图生图**：「把这张图改成…」→ 原图放进 `ComfyUI/input/`，`denoise` 控制改动幅度。
- **内容闸门**：`qq-bridge._img_blocked(prompt)` 先拦（敏感词表），命中直接拒绝、不画。
- **发送**：`import qq-bridge` 借它的 `send_image` 发回 QQ（换平台就换这一处）。
- 冷却：同一个人 `image_cooldown_s` 秒内只画一张（防刷屏）。
- 模型：**Z-Image-Turbo（NVFP4）** —— `z_image_turbo_nvfp4.safetensors`（unet/diffusion_models）+ `qwen_3_4b_fp4_mixed.safetensors`（text_encoders）+ `ae.safetensors`（vae）；
  工作流 8 步、cfg 1.0、`ModelSamplingAuraFlow(shift=3.0)`、CLIP type `lumina2`（上面全写死在 `scripts/image_service.py` 里）。

## 跑一条
```bash
<python> scripts/image_service.py <umo> "一只橘猫在屋顶看夕阳"
# 完成后自动把图发进聊天
```

## 换机器 / 给别人用
见 `SETUP.md`：改 `image_service.py` 头部的三个常量（HERMES_HOME / ROOT / BRIDGE），并照 SETUP 装 ComfyUI + 下三个模型文件。
