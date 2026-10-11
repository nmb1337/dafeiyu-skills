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


def build_workflow(prompt: str, size: int, seed: int,
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
                   "inputs": {"width": size, "height": size, "batch_size": 1}}
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


def generate(prompt: str, size: int, seed: int, image: str | None = None,
             denoise: float = 0.75, timeout_s: int = 600):
    """提交并等结果，返回产物路径（失败返回 None）。"""
    t0 = time.time()
    res = _post("/prompt", {"prompt": build_workflow(prompt, size, seed, image, denoise),
                            "client_id": "qq-image"})
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
    ap.add_argument("--size", type=int, default=1024)
    ap.add_argument("--seed", type=int, default=-1, help="-1 = 随机（每张都不一样）")
    ap.add_argument("--image", default="", help="图生图：源图路径（桥接把被引用的图落盘后传进来）")
    ap.add_argument("--denoise", type=float, default=0.75, help="图生图重绘幅度")
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

    seed = a.seed if a.seed >= 0 else random.randint(1, 2**31 - 1)
    idle_s = float(os.environ.get("IMAGE_IDLE_SHUTDOWN_S") or 300)
    # 图生图：把桥接落盘的底图拷进 ComfyUI/input/（LoadImage 只认那里的文件，不认任意路径）
    src_name = ""
    if a.image and os.path.isfile(a.image):
        try:
            inp = ROOT / "ComfyUI" / "input"
            inp.mkdir(parents=True, exist_ok=True)
            src_name = (f"qqsrc_{int(time.time())}_{os.getpid()}"
                        f"{os.path.splitext(a.image)[1] or '.png'}")
            shutil.copy2(a.image, inp / src_name)
        except Exception as exc:
            log(f"底图拷贝失败：{exc}")
            src_name = ""
    log(f"开始{'图生图（denoise=%.2f）' % a.denoise if src_name else '文生图'}：{prompt!r} → {a.umo}")
    tell(ACK_IMG2IMG if src_name else ACK_TEXT)

    try:
        if not ensure_comfyui():
            tell("本鱼这边画板没能支起来（本地服务没起来），等会儿再喊我试试～")
            return 1
        # 起了 ComfyUI 就挂个独立看护（单例）。任务进程送完图就退，空闲关火是它的事 ——
        # 这样任务被拦下/出错提前返回时，显存也照样会被释放。
        spawn_watcher(idle_s)
        out = generate(prompt, a.size, seed, src_name or None, a.denoise)
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
        _touch()
        return 0
    finally:
        try:
            LOCK.unlink(missing_ok=True)
        except Exception:
            pass


if __name__ == "__main__":
    raise SystemExit(main())
