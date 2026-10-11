r"""
Generate an image on the local ComfyUI (Z-Image-Turbo nvfp4) and save the result.

Usage:
  python comfyui_generate.py txt2img "提示词" [--size 1024] [--seed 42] [--out PATH]
  python comfyui_generate.py img2img "提示词" --image <已在 ComfyUI/input/ 里的文件名或本地路径> [--denoise 0.75] [--seed 42] [--out PATH]

Run it with the ComfyUI embedded python:
  C:\Users\32672\Apps\ComfyUI_windows_portable\python_embeded\python.exe comfyui_generate.py ...

ComfyUI must already be running on 127.0.0.1:8188 (see start_comfyui.bat); this script
does not launch it. img2img with --image pointing at a local path copies the file into
ComfyUI/input/ first.
"""
from __future__ import annotations

import argparse
import json
import shutil
import time
import urllib.request
from pathlib import Path

API = "http://127.0.0.1:8188"
COMFY_ROOT = Path(r"C:\Users\32672\Apps\ComfyUI_windows_portable")
INPUT_DIR = COMFY_ROOT / "ComfyUI" / "input"
OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))  # never proxy loopback

UNET = "z_image_turbo_nvfp4.safetensors"
CLIP_NAME = "qwen_3_4b_fp4_mixed.safetensors"
VAE_NAME = "ae.safetensors"


def post(path: str, payload: dict) -> dict:
    req = urllib.request.Request(API + path, data=json.dumps(payload).encode(), method="POST")
    req.add_header("Content-Type", "application/json")
    with OPENER.open(req, timeout=60) as r:
        return json.loads(r.read().decode("utf-8", "replace"))


def get(path: str) -> dict:
    with OPENER.open(API + path, timeout=60) as r:
        return json.loads(r.read().decode("utf-8", "replace"))


def build_workflow(prompt: str, *, image: str | None, denoise: float, size: int, seed: int) -> dict:
    wf = {
        "1":  {"class_type": "UNETLoader", "inputs": {"unet_name": UNET, "weight_dtype": "default"}},
        "2":  {"class_type": "CLIPLoader", "inputs": {"clip_name": CLIP_NAME, "type": "lumina2"}},
        "3":  {"class_type": "VAELoader", "inputs": {"vae_name": VAE_NAME}},
        "11": {"class_type": "ModelSamplingAuraFlow", "inputs": {"model": ["1", 0], "shift": 3.0}},
        "4":  {"class_type": "CLIPTextEncode", "inputs": {"text": prompt, "clip": ["2", 0]}},
        "5":  {"class_type": "ConditioningZeroOut", "inputs": {"conditioning": ["4", 0]}},
    }
    if image is None:
        wf["6"] = {"class_type": "EmptySD3LatentImage",
                   "inputs": {"width": size, "height": size, "batch_size": 1}}
        latent = ["6", 0]
    else:
        wf["10"] = {"class_type": "LoadImage", "inputs": {"image": image, "upload": "image"}}
        wf["12"] = {"class_type": "VAEEncode", "inputs": {"pixels": ["10", 0], "vae": ["3", 0]}}
        latent = ["12", 0]
    wf["7"] = {"class_type": "KSampler", "inputs": {
        "model": ["11", 0], "seed": seed, "steps": 8, "cfg": 1.0,
        "sampler_name": "res_multistep", "scheduler": "simple",
        "positive": ["4", 0], "negative": ["5", 0],
        "latent_image": latent, "denoise": denoise}}
    wf["8"] = {"class_type": "VAEDecode", "inputs": {"samples": ["7", 0], "vae": ["3", 0]}}
    wf["9"] = {"class_type": "SaveImage", "inputs": {"filename_prefix": "hermes", "images": ["8", 0]}}
    return wf


def main() -> int:
    ap = argparse.ArgumentParser(description="Generate an image on local ComfyUI (Z-Image-Turbo).")
    ap.add_argument("mode", choices=["txt2img", "img2img"])
    ap.add_argument("prompt")
    ap.add_argument("--image", help="img2img source: a file already in ComfyUI/input/, or a local path to copy in")
    ap.add_argument("--denoise", type=float, default=0.75)
    ap.add_argument("--size", type=int, default=1024)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--out", help="copy the result here")
    args = ap.parse_args()

    src = None
    if args.mode == "img2img":
        if not args.image:
            print("img2img needs --image")
            return 2
        p = Path(args.image)
        if p.exists():
            INPUT_DIR.mkdir(parents=True, exist_ok=True)
            dest = INPUT_DIR / p.name
            shutil.copy2(p, dest)
            src = p.name
            print(f"copied source -> {dest}")
        else:
            src = args.image  # assume it is already inside ComfyUI/input/

    wf = build_workflow(args.prompt, image=src, denoise=args.denoise, size=args.size, seed=args.seed)
    t0 = time.time()
    res = post("/prompt", {"prompt": wf, "client_id": "hermes-cli"})
    pid = res.get("prompt_id")
    if not pid:
        print("submit failed:", json.dumps(res, ensure_ascii=False)[:600])
        return 1
    print("queued:", pid)

    deadline = time.time() + 900
    while time.time() < deadline:
        time.sleep(3)
        hist = get(f"/history/{pid}")
        if pid in hist:
            e = hist[pid]
            st = e.get("status", {})
            print("status:", st.get("status_str"), "| completed:", st.get("completed"))
            for m in st.get("messages", []):
                if m and m[0] in ("execution_error", "execution_interrupted"):
                    print("  !!", json.dumps(m[1], ensure_ascii=False)[:600])
            out_files = []
            for _, out in (e.get("outputs") or {}).items():
                for im in out.get("images", []):
                    fp = COMFY_ROOT / "ComfyUI" / im.get("type", "output") / im.get("subfolder", "") / im["filename"]
                    out_files.append(fp)
                    print("IMAGE:", fp)
            if args.out and out_files:
                dest = Path(args.out)
                shutil.copy2(out_files[0], dest)
                print("SAVED:", dest.resolve())
            print(f"elapsed: {time.time()-t0:.1f}s")
            return 0
    print("TIMEOUT")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
