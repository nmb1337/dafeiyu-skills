"""QQ 生图流水线：确保本地 ComfyUI(8189) 在跑 → 生成 → 发回 QQ。

由 qq-bridge 派单（独立进程，和点歌 pipeline 一个套路）：
    <python> image_service.py <umo> "<提示词>"

设计要点
--------
* 端口 8189：8188 是主人的 MiniMax-H3 视频 ComfyUI，绝不能共用
  （见 start_comfyui.bat 里的说明：共用会让 run-ref-shot.ps1 以为视频服务器就绪）。
* 按需拉起：生图不常来，而 ComfyUI 空转要吃 4.5GB 显存 —— 来了才开。
* 空闲自关：画完再闲 image_idle_shutdown_s 秒就关掉，把显存还给主人。
* 借桥接的发送能力：import qq-bridge 用它现成的 send_qq/send_image
  （和 sing_service.py 一模一样的招数，避免再写一份 NapCat 通道）。
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import random
import shutil
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

HERMES_HOME = Path(r"C:\Users\32672\AppData\Local\hermes")
BRIDGE = HERMES_HOME / "scripts" / "qq-bridge.py"
LOG = HERMES_HOME / "logs" / "image.log"

ROOT = Path(r"C:\Users\32672\Apps\ComfyUI_windows_portable")
API = "http://127.0.0.1:8189"                     # 图片服务器专用端口
WORK = ROOT / "work"
LOCK = WORK / "image.lock"
LAST_USE = WORK / "last_use.txt"
WATCH = WORK / "watch.lock"                   # 空闲看护单例（心跳文件）

UNET = "z_image_turbo_nvfp4.safetensors"
CLIP_NAME = "qwen_3_4b_fp4_mixed.safetensors"
VAE_NAME = "ae.safetensors"

# 绝不走代理：loopback 经 net-relay 会乱套
OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))

ACK_TEXT = "在画了在画了，等本鱼一小会儿～"
ACK_IMG2IMG = "收到收到，本鱼照着这张改改～"
DONE_TEXT = "画好啦，看看像不像～"
DONE_IMG2IMG = "改好啦，看看这个版本～"


def log(*a) -> None:
    line = f"[{time.strftime('%H:%M:%S')}] " + " ".join(str(x) for x in a)
    print(line, flush=True)
    try:
        LOG.parent.mkdir(parents=True, exist_ok=True)
        with open(LOG, "a", encoding="utf-8") as fh:
            fh.write(line + "\n")
    except Exception:
        pass


# ---- 状态文件 --------------------------------------------------------------

def _touch() -> None:
    WORK.mkdir(parents=True, exist_ok=True)
    LAST_USE.write_text(str(time.time()), encoding="utf-8")


def _last_use() -> float:
    try:
        return float(LAST_USE.read_text(encoding="utf-8").strip() or 0)
    except Exception:
        return 0.0


def _lock_active() -> bool:
    """有别的生图任务正在跑吗（lock 文件还在且没陈旧）。"""
    try:
        return LOCK.exists() and (time.time() - LOCK.stat().st_mtime) < 7200
    except Exception:
        return False


# ---- 桥接借用 --------------------------------------------------------------

def load_bridge():
    """把 qq-bridge.py 当模块加载，用它的 send_qq / send_image。

    桥接有 __main__ 保护，加载它不会启动服务器（sing_service.py 同款用法）。
    """
    spec = importlib.util.spec_from_file_location("qq_bridge", str(BRIDGE))
    mod = importlib.util.module_from_spec(spec)
    sys.modules["qq_bridge"] = mod
    spec.loader.exec_module(mod)
    return mod


# ---- ComfyUI 生命周期 ------------------------------------------------------

def _up() -> bool:
    try:
        with OPENER.open(API + "/system_stats", timeout=5) as r:
            r.read(64)
        return True
    except Exception:
        return False


def ensure_comfyui(deadline_s: int = 240) -> bool:
    """没跑就通过 ComfyUI.vbs 拉起来（真 detached），然后等端口就绪。"""
    if _up():
        return True
    log("ComfyUI 没在跑，拉起…")
    flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
    try:
        subprocess.Popen(["wscript.exe", str(ROOT / "ComfyUI.vbs")], cwd=str(ROOT),
                         creationflags=flags, close_fds=True)
    except Exception as exc:
        log(f"启动失败：{exc}")
        return False
    t0 = time.time()
    while time.time() - t0 < deadline_s:
        time.sleep(3)
        if _up():
            log(f"ComfyUI 就绪（{time.time()-t0:.0f}s）")
            return True
    log(f"等 ComfyUI 超时（{deadline_s}s）")
    return False


def kill_comfyui() -> bool:
    """关掉 8189 上的 ComfyUI，把显存还回去。"""
    ps = ("$p=(Get-NetTCPConnection -LocalPort 8189 -State Listen -ErrorAction SilentlyContinue"
          " | Select-Object -First 1 -ExpandProperty OwningProcess);"
          "if($p){Stop-Process -Id $p -Force -ErrorAction SilentlyContinue; 'killed'}else{'none'}")
    try:
        r = subprocess.run(["powershell", "-NoProfile", "-Command", ps],
                           capture_output=True, text=True, timeout=90,
                           creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
        return "killed" in (r.stdout or "")
    except Exception as exc:
        log(f"关 ComfyUI 失败：{exc}")
        return False


def _watch_live() -> bool:
    """已经有别的看护在值班吗（心跳还新鲜）。"""
    try:
        return WATCH.exists() and (time.time() - WATCH.stat().st_mtime) < 45
    except Exception:
        return False


def spawn_watcher(idle_s: float) -> None:
    """起一个脱离当前进程的看护（单例）。任务进程送完图就退，不留尾巴。

    踩过的坑：原来让任务进程自己守空闲 —— 群里连着点几张就堆了十几个 python；
    而且任务被拦下/出错时提前 return，根本没走到守空闲那步，显存就永远不放了。
    """
    if idle_s <= 0 or _watch_live():
        return
    flags = 0
    if os.name == "nt":
        flags = subprocess.CREATE_NO_WINDOW | subprocess.DETACHED_PROCESS
    try:
        subprocess.Popen([sys.executable, str(Path(__file__).resolve()), "--watch", str(idle_s)],
                         cwd=str(ROOT), creationflags=flags, close_fds=True,
                         stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                         stderr=subprocess.DEVNULL)
    except Exception as exc:
        log(f"起看护失败：{exc}")


def idle_watch(idle_s: float) -> None:
    """画完别马上关 —— 再守一会儿，万一接着有人要画；到期且没人用才关。

    单例：谁先来谁值班（心跳文件），后来的直接退出 —— 否则群里连着点几张，
    每单都留一个看护，一会儿就堆出十几个 python 进程。
    """
    if idle_s <= 0:
        return
    if _watch_live():
        return                             # 已经有人在值班，别叠
    WORK.mkdir(parents=True, exist_ok=True)
    try:
        WATCH.write_text(str(os.getpid()), encoding="utf-8")
    except Exception:
        pass
    try:
        while True:
            time.sleep(15)
            try:
                WATCH.write_text(str(os.getpid()), encoding="utf-8")   # 心跳
            except Exception:
                pass
            if time.time() - _last_use() < idle_s:
                continue
            if _lock_active():
                continue                   # 有任务在跑，别断电
            log(f"空闲 {idle_s:.0f}s 到期，关掉 ComfyUI 释放显存")
            kill_comfyui()
            return
    finally:
        try:
            WATCH.unlink(missing_ok=True)
        except Exception:
            pass


# ---- 生成 ------------------------------------------------------------------

def _post(path: str, payload: dict) -> dict:
    req = urllib.request.Request(API + path, data=json.dumps(payload).encode(), method="POST")
    req.add_header("Content-Type", "application/json")
    with OPENER.open(req, timeout=60) as r:
        return json.loads(r.read().decode("utf-8", "replace"))


def _get(path: str) -> dict:
    with OPENER.open(API + path, timeout=60) as r:
        return json.loads(r.read().decode("utf-8", "replace"))


def build_workflow(prompt: str, w: int, h: int, seed: int,
                   image: str | None = None, denoise: float = 0.75) -> dict:
    """Z-Image-Turbo 文生图 / 图生图（8 步，cfg 1.0，和已验证的工作流一致）。

    image = 已放进 ComfyUI/input/ 的文件名 → 走图生图（LoadImage + VAEEncode）。
    denoise 参考：0.3~0.4 微调、0.5~0.65 明显变化、0.75~0.9 大改/换场景。
    """
    wf = {
        "1":  {"class_type": "UNETLoader", "inputs": {"unet_name": UNET, "weight_dtype": "default"}},
        "2":  {"class_type": "CLIPLoader", "inputs": {"clip_name": CLIP_NAME, "type": "lumina2"}},
        "3":  {"class_type": "VAELoader", "inputs": {"vae_name": VAE_NAME}},
        "11": {"class_type": "ModelSamplingAuraFlow", "inputs": {"model": ["1", 0], "shift": 3.0}},
        "4":  {"class_type": "CLIPTextEncode", "inputs": {"text": prompt, "clip": ["2", 0]}},
        "5":  {"class_type": "ConditioningZeroOut", "inputs": {"conditioning": ["4", 0]}},
    }
    if image:
        wf["10"] = {"class_type": "LoadImage", "inputs": {"image": image, "upload": "image"}}
        wf["12"] = {"class_type": "VAEEncode", "inputs": {"pixels": ["10", 0], "vae": ["3", 0]}}
        latent = ["12", 0]
    else:
        wf["6"] = {"class_type": "EmptySD3LatentImage",
                   "inputs": {"width": w, "height": h, "batch_size": 1}}
        latent = ["6", 0]
    wf["7"] = {"class_type": "KSampler", "inputs": {
        "model": ["11", 0], "seed": seed, "steps": 8, "cfg": 1.0,
        "sampler_name": "res_multistep", "scheduler": "simple",
        "positive": ["4", 0], "negative": ["5", 0],
        "latent_image": latent,
        "denoise": denoise if image else 1.0}}
    wf["8"] = {"class_type": "VAEDecode", "inputs": {"samples": ["7", 0], "vae": ["3", 0]}}
    wf["9"] = {"class_type": "SaveImage", "inputs": {"filename_prefix": "qq", "images": ["8", 0]}}
    return wf


def _fit_src(src: str, dst) -> None:
    """把底图适配到长边 ~1024（8 的倍数）：太大缩小、太小放大（最多 2 倍）。

    踩过的坑：QQ 里的截图/竖图（480×1384、65KB 那种）直接喂 VAEEncode →
    出图又小又糊，而且尺寸非标；配合高 denoise 几乎完全重画、和原图没关系。
    """
    try:
        from PIL import Image
    except Exception:
        shutil.copy2(src, dst)
        return
    im = Image.open(src).convert("RGB")
    w, h = im.size
    ms = max(w, h) or 1
    scale = min(1024.0 / ms, 2.0)
    if 0.92 <= scale <= 1.08 and ms >= 768:
        im.save(dst)
        return
    nw = max(64, int(w * scale) // 8 * 8)
    nh = max(64, int(h * scale) // 8 * 8)
    im.resize((nw, nh), Image.LANCZOS).save(dst)


def build_kontext_workflow(prompt: str, seed: int, image: str,
                           steps: int = 20, guidance: float = 2.5) -> dict:
    """FLUX.1-Kontext-dev（GGUF 量化）指令编辑：保人、按话改图。

    结构与官方示例（ComfyUI_examples/flux/flux_kontext_example）逐节点对齐 ——
    之前自己拼的简版缺 ModelSamplingFlux（shift）那一段，模型退化成"原图复印机"，
    任何指令都不生效（主人 2026-10-12 实测：棉花地/鞭子指令被无视）。
    """
    return {
        "12": {"class_type": "UnetLoaderGGUF", "inputs": {"unet_name": KONTEXT_UNET}},
        "11": {"class_type": "DualCLIPLoader", "inputs": {
            "clip_name1": "t5xxl_fp8_e4m3fn.safetensors",
            "clip_name2": "clip_l.safetensors", "type": "flux"}},
        "10": {"class_type": "VAELoader", "inputs": {"vae_name": KONTEXT_VAE}},
        "6":  {"class_type": "CLIPTextEncode", "inputs": {"text": prompt, "clip": ["11", 0]}},
        "26": {"class_type": "FluxGuidance", "inputs": {"guidance": guidance, "conditioning": ["6", 0]}},
        "41": {"class_type": "LoadImage", "inputs": {"image": image, "upload": "image"}},
        "40": {"class_type": "FluxKontextImageScale", "inputs": {"image": ["41", 0]}},
        "39": {"class_type": "VAEEncode", "inputs": {"pixels": ["40", 0], "vae": ["10", 0]}},
        "42": {"class_type": "ReferenceLatent", "inputs": {"conditioning": ["26", 0], "latent": ["39", 0]}},
        "27": {"class_type": "EmptySD3LatentImage",
               "inputs": {"width": 1024, "height": 1024, "batch_size": 1}},
        "30": {"class_type": "ModelSamplingFlux", "inputs": {
            "max_shift": 1.15, "base_shift": 0.5, "width": 1024, "height": 1024,
            "model": ["12", 0]}},
        "17": {"class_type": "BasicScheduler", "inputs": {
            "scheduler": "simple", "steps": steps, "denoise": 1.0, "model": ["30", 0]}},
        "16": {"class_type": "KSamplerSelect", "inputs": {"sampler_name": "euler"}},
        "22": {"class_type": "BasicGuider", "inputs": {"model": ["30", 0], "conditioning": ["42", 0]}},
        "25": {"class_type": "RandomNoise", "inputs": {"noise_seed": seed}},
        "13": {"class_type": "SamplerCustomAdvanced", "inputs": {
            "noise": ["25", 0], "guider": ["22", 0], "sampler": ["16", 0],
            "sigmas": ["17", 0], "latent_image": ["27", 0]}},
        "8":  {"class_type": "VAEDecode", "inputs": {"samples": ["13", 0], "vae": ["10", 0]}},
        "9":  {"class_type": "SaveImage", "inputs": {"filename_prefix": "qq", "images": ["8", 0]}},
    }


KONTEXT_UNET = "flux1-kontext-dev-Q4_K_M.gguf"
KONTEXT_VAE = "flux_ae.safetensors"


def _to_english_instruction(prompt: str) -> str:
    """Kontext 对中文指令几乎不理（T5 是英文脑子）→ 用 DeepSeek 先翻成英文再送。

    实测（2026-10-12）：中文「在棉花地里被鞭子抽」= 原图复印机；同样的意思写成英文
    = 棉花地、鞭子、保脸保衣服全部到位。翻译失败就退回原文。
    """
    import re as _re
    if not _re.search(r"[\u4e00-\u9fff]", prompt or ""):
        return prompt
    try:
        key = ""
        for line in (HERMES_HOME / ".env").read_text(encoding="utf-8", errors="replace").splitlines():
            if line.strip().startswith("DEEPSEEK_API_KEY"):
                key = line.split("=", 1)[1].strip().strip('"').strip("'")
                break
        if not key:
            return prompt
        body = json.dumps({
            "model": "deepseek-chat",
            "messages": [
                {"role": "system", "content": "Translate the image-editing instruction into concise, "
                                              "literal ENGLISH for a text-to-image model. "
                                              "Output ONLY the translation."},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.1, "max_tokens": 200,
        }).encode()
        req = urllib.request.Request(
            "https://api.deepseek.com/chat/completions", data=body,
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {key}"})
        with OPENER.open(req, timeout=25) as r:
            out = json.loads(r.read().decode("utf-8", "replace"))
        en = (((out.get("choices") or [{}])[0].get("message") or {}).get("content") or "").strip()
        if en:
            log(f"指令转英文：{prompt!r} → {en!r}")
            return en
    except Exception as exc:
        log(f"指令转英文失败（用原文）：{exc}")
    return prompt


def _to_detailed_prompt(prompt: str) -> str:
    """Z-Image 官方/社区指南：它喜欢长而具体的结构化提示词（80-250 词最佳），
    "你没说的它自己发挥"。所以先用 DeepSeek 把用户的短需求扩写成详细画面描述。
    """
    import re as _re
    try:
        key = ""
        for line in (HERMES_HOME / ".env").read_text(encoding="utf-8", errors="replace").splitlines():
            if line.strip().startswith("DEEPSEEK_API_KEY"):
                key = line.split("=", 1)[1].strip().strip('"').strip("'")
                break
        if not key:
            return prompt
        body = json.dumps({
            "model": "deepseek-chat",
            "messages": [
                {"role": "system", "content": "把用户的画图需求扩写成一段 80-150 词的详细中文画面描述："
                                              "保留原意与主体，补充镜头、光线、构图、材质与氛围细节；"
                                              "不要出现'高清/大师作品/最优质'这类空泛词；只输出描述本身。"},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.7, "max_tokens": 400,
        }).encode()
        req = urllib.request.Request(
            "https://api.deepseek.com/chat/completions", data=body,
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {key}"})
        with OPENER.open(req, timeout=25) as r:
            out = json.loads(r.read().decode("utf-8", "replace"))
        d = (((out.get("choices") or [{}])[0].get("message") or {}).get("content") or "").strip()
        if len(d) > len(prompt):
            log(f"文生图提示词扩写：{prompt!r} → {d[:80]!r}…")
            return d
    except Exception as exc:
        log(f"提示词扩写失败（用原文）：{exc}")
    return prompt


def generate(prompt: str, size: str, seed: int, image: str | None = None,
             denoise: float = 0.75, timeout_s: int = 600, engine: str = "zimage"):
    """提交并等结果，返回产物路径（失败返回 None）。

    size 形如 "1024x1024" / "896x1152"（竖图）/"1152x896"（横图）。
    engine：zimage = Z-Image-Turbo（文生图/轻改）；kontext = FLUX Kontext（指令编辑，要 image）。
    """
    t0 = time.time()
    try:
        _s = str(size).lower().replace("×", "x")
        w, h = ([int(x) for x in _s.split("x", 1)] if "x" in _s else (int(_s), int(_s)))
    except Exception:
        w = h = 1024
    if engine == "kontext" and image:
        # Kontext 天生保人，不需要提示词里的"保持…不变"尾巴（反而干扰指令）；
        # 而且它只吃英文指令（中文=原图复印机）→ 先翻英文
        prompt = prompt.replace("；务必保持原本人物的五官样貌和身上衣服不变", "").strip(" ；;")
        prompt = _to_english_instruction(prompt)
        # ComfyUI 官方提示技巧：明确写出"保持什么不变"效果最好（五官/发型/衣服）；
        # 别提"保持姿势"——那会把用户要的动作（被鞭子抽）也钉死
        if "unchanged" not in prompt.lower():
            prompt = (prompt.rstrip(".。!！?？ ")
                      + ". Keep the subject's facial features, hairstyle and clothing unchanged.")
        wf = build_kontext_workflow(prompt, seed, image)
    else:
        # Z-Image 指南：它喜欢长而具体的提示词，短了它自己发挥 → 先扩写
        prompt = _to_detailed_prompt(prompt)
        wf = build_workflow(prompt, w, h, seed, image, denoise)
    res = _post("/prompt", {"prompt": wf, "client_id": "qq-image"})
    pid = res.get("prompt_id")
    if not pid:
        log(f"提交失败：{json.dumps(res, ensure_ascii=False)[:400]}")
        return None
    log(f"已排队 {pid}（seed={seed}, {size}px）")
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        time.sleep(2)
        try:
            hist = _get(f"/history/{pid}")
        except Exception:
            continue
        if pid not in hist:
            continue
        entry = hist[pid] or {}
        status = entry.get("status", {})
        if status.get("status_str") == "error":
            for m in status.get("messages", []):
                if m and m[0] in ("execution_error", "execution_interrupted"):
                    log("执行出错：" + json.dumps(m[1], ensure_ascii=False)[:300])
            return None
        files = []
        for out in (entry.get("outputs") or {}).values():
            for im in out.get("images", []):
                files.append(ROOT / "ComfyUI" / im.get("type", "output")
                             / im.get("subfolder", "") / im["filename"])
        if files:
            log(f"出图 {files[0].name}（{time.time()-t0:.1f}s）")
            return files[0]
        # status 完成但没图 —— 没戏了
        if status.get("completed"):
            log("任务完成但没有图片输出")
            return None
    log("生成超时")
    return None


# ---- 主流程 ----------------------------------------------------------------

def main() -> int:
    # 内部模式：独立看护进程（空闲到期就关掉 ComfyUI 释放显存）
    if len(sys.argv) >= 3 and sys.argv[1] == "--watch":
        idle_watch(float(sys.argv[2]))
        return 0

    ap = argparse.ArgumentParser()
    ap.add_argument("umo", help="napcat-qq:FriendMessage:<uin> 或 :GroupMessage:<gid>")
    ap.add_argument("prompt")
    ap.add_argument("--size", default="1024x1024",
                    help="WxH 或单数字：1024x1024 / 896x1152（竖）/ 1152x896（横）")
    ap.add_argument("--seed", type=int, default=-1, help="-1 = 随机（每张都不一样）")
    ap.add_argument("--image", default="", help="图生图：源图路径（桥接把被引用的图落盘后传进来）")
    ap.add_argument("--denoise", type=float, default=0.55,
                    help="图生图重绘幅度（0.5 小改保留特征 / 0.6 大改换场景）")
    ap.add_argument("--engine", default="auto", choices=["auto", "zimage", "kontext"],
                    help="auto=图生图走 Kontext 编辑、文生图走 Z-Image")
    a = ap.parse_args()

    WORK.mkdir(parents=True, exist_ok=True)
    prompt = " ".join((a.prompt or "").split())[:400]
    if not prompt:
        print("没有提示词，退出")
        return 2

    # 串行化：一台显卡一次画一张。等一会儿拿不到就告诉对方前面还排着队。
    wait_s = 240
    t0 = time.time()
    while LOCK.exists() and (time.time() - LOCK.stat().st_mtime) < 7200:
        if time.time() - t0 > wait_s:
            break
        time.sleep(5)
    LOCK.write_text(f"{os.getpid()} {time.time()}\n", encoding="utf-8")
    _touch()

    try:
        bridge = load_bridge()
    except Exception as exc:
        log(f"加载桥接失败：{exc}")
        LOCK.unlink(missing_ok=True)
        return 1

    # 兜底内容闸门：桥接那边已经拦过一次；万一有别的调用方绕过它，这里再挡一道
    try:
        _hit = bridge._img_blocked(prompt)
    except Exception:
        _hit = ""
    if _hit:
        log(f"内容闸门拦下：{prompt[:60]!r} 命中={_hit!r}")
        try:
            bridge.send_qq(a.umo, "这个本鱼不画哦，换点别的吧～")
        except Exception:
            pass
        LOCK.unlink(missing_ok=True)
        return 3

    def tell(text: str) -> None:
        try:
            bridge.send_qq(a.umo, text)
        except Exception as exc:
            log(f"说话失败：{exc}")

    # 游戏/直播时的服务侧兜底：桥接派单前已经拦过一次，这里再挡一道 ——
    # 跑一张 Kontext 要占显卡约 2 分钟，主人打游戏/直播时绝不能开跑
    # （主人 2026-10-12：打游戏的时候委婉告诉他们并且停掉这个功能。跟唱歌同一套口径）
    try:
        if bridge._stream_mode_on():
            tell("主人正在直播玩 MC 呢——画图要占显卡、会把直播卡成 PPT，等播完本鱼马上给你画～")
            log("直播模式中：图片任务取消（服务侧兜底，未开工）")
            LOCK.unlink(missing_ok=True)
            return 0
        _g = bridge._steam_now()
        if _g:
            tell(f"主人现在正在玩《{_g}》——本地画图要借显卡，现在开画会把他卡掉线，过半小时再来喊本鱼～")
            log(f"游戏《{_g}》中：图片任务取消（服务侧兜底，未开工）")
            LOCK.unlink(missing_ok=True)
            return 0
    except Exception as exc:
        log(f"游戏/直播兜底检查失败（照常画）：{exc}")

    seed = a.seed if a.seed >= 0 else random.randint(1, 2**31 - 1)
    idle_s = float(os.environ.get("IMAGE_IDLE_SHUTDOWN_S") or 300)
    # 图生图：把桥接落盘的底图拷进 ComfyUI/input/（LoadImage 只认那里的文件，不认任意路径）
    # 先做尺寸适配：QQ 里的截图/竖图（480×1384 那种）直接喂会又糊又小
    src_name = ""
    engine = a.engine if a.engine != "auto" else (
        "kontext" if (a.image and os.path.isfile(a.image)) else "zimage")
    if a.image and os.path.isfile(a.image):
        try:
            inp = ROOT / "ComfyUI" / "input"
            inp.mkdir(parents=True, exist_ok=True)
            src_name = (f"qqsrc_{int(time.time())}_{os.getpid()}"
                        f"{os.path.splitext(a.image)[1] or '.png'}")
            if engine == "kontext":
                # Kontext 自带 FluxKontextImageScale 挑最优分辨率，别先缩（缩了丢细节）
                shutil.copy2(a.image, inp / src_name)
            else:
                _fit_src(a.image, inp / src_name)
        except Exception as exc:
            log(f"底图拷贝失败：{exc}")
            src_name = ""
    if src_name:
        log(f"开始图生图（denoise={a.denoise:.2f}）[{engine}]：{prompt!r} → {a.umo}")
    else:
        log(f"开始文生图[{engine}]：{prompt!r} → {a.umo}")
    tell(ACK_IMG2IMG if src_name else ACK_TEXT)

    try:
        if not ensure_comfyui():
            tell("本鱼这边画板没能支起来（本地服务没起来），等会儿再喊我试试～")
            return 1
        # 起了 ComfyUI 就挂个独立看护（单例）。任务进程送完图就退，空闲关火是它的事 ——
        # 这样任务被拦下/出错提前返回时，显存也照样会被释放。
        spawn_watcher(idle_s)
        out = generate(prompt, a.size, seed, src_name or None, a.denoise, engine=engine)
        if not out:
            tell("画到一半本鱼手滑了，没画出来…再喊我一次试试？")
            return 1
        try:
            ok = bridge.send_image(a.umo, str(out), caption=(DONE_IMG2IMG if src_name else DONE_TEXT))
        except Exception as exc:
            log(f"发图异常：{exc}")
            ok = False
        if not ok:
            tell("画是画好了，可本鱼发不出去…稍后再喊我一次吧")
            return 1
        # 记下"这个聊天最近一张出图"：下次「把刚才那张改成…」链式修改要用它当底图
        try:
            import re as _re
            _lo = HERMES_HOME / "cache" / "qq-images" / "last_out"
            _lo.mkdir(parents=True, exist_ok=True)
            (_lo / (_re.sub(r"[^A-Za-z0-9_.-]", "_", a.umo) + ".txt")).write_text(
                str(out), encoding="utf-8")
        except Exception:
            pass
        _touch()
        return 0
    finally:
        try:
            LOCK.unlink(missing_ok=True)
        except Exception:
            pass


if __name__ == "__main__":
    raise SystemExit(main())
