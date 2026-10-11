#!/usr/bin/env python
"""B站音频下载：view -> wbi 签名 playurl -> dash 音频流（匿名）"""
import hashlib, json, os, sys, time, urllib.parse, urllib.request

BV = "BV1P24y1a7Lt"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")
REF = f"https://www.bilibili.com/video/{BV}/"

opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))  # 脱代理直连


def get_json(url, referer=REF):
    req = urllib.request.Request(url, headers={
        "User-Agent": UA, "Referer": referer, "Accept": "application/json, text/plain, */*",
        "Accept-Language": "zh-CN,zh;q=0.9", "Origin": "https://www.bilibili.com",
    })
    with opener.open(req, timeout=30) as r:
        return json.loads(r.read().decode("utf-8"))


MIXIN_TAB = [46, 47, 18, 2, 53, 8, 23, 32, 15, 50, 10, 31, 58, 3, 45, 35, 27, 43, 5, 49,
             33, 9, 42, 19, 29, 28, 14, 39, 12, 38, 41, 13, 37, 48, 7, 16, 24, 55, 40, 61,
             26, 17, 0, 1, 60, 51, 30, 4, 22, 25, 54, 21, 56, 59, 6, 63, 57, 62, 11, 36,
             20, 34, 44, 52]


def wbi_sign(params: dict, img_key: str, sub_key: str) -> dict:
    raw = img_key + sub_key
    mixin = "".join(raw[i] for i in MIXIN_TAB)[:32]
    p = dict(params)
    p["wts"] = int(time.time())
    items = sorted(p.items())
    q = urllib.parse.urlencode(
        [(k, "".join(c for c in str(v) if c not in "!'()*")) for k, v in items])
    p["w_rid"] = hashlib.md5((q + mixin).encode()).hexdigest()
    return p


def main():
    v = get_json(f"https://api.bilibili.com/x/web-interface/view?bvid={BV}")
    assert v["code"] == 0, v
    pages = v["data"]["pages"]
    cid = pages[0]["cid"]
    title = v["data"]["title"]
    print("title:", title, "| cid:", cid, "| dur:", v["data"]["duration"], "s", flush=True)

    nav = get_json("https://api.bilibili.com/x/web-interface/nav", "https://www.bilibili.com/")
    img = nav["data"]["wbi_img"]["img_url"].rsplit("/", 1)[-1].split(".")[0]
    sub = nav["data"]["wbi_img"]["sub_url"].rsplit("/", 1)[-1].split(".")[0]

    q = wbi_sign({"bvid": BV, "cid": cid, "fnval": 4048, "fnver": 0, "fourk": 1,
                  "qn": 127, "otype": "json", "platform": "pc"}, img, sub)
    url = "https://api.bilibili.com/x/player/wbi/playurl?" + urllib.parse.urlencode(q)
    pu = get_json(url)
    if pu.get("code") != 0:
        print("playurl failed:", pu.get("code"), pu.get("message"))
        # 退化：试试非 wbi 端点
        return 2
    dash = pu["data"].get("dash") or {}
    audios = sorted(dash.get("audio") or [],
                    key=lambda a: a.get("bandwidth", 0), reverse=True)
    if not audios:
        print("no dash audio:", json.dumps(pu["data"])[:400])
        return 3
    a = audios[0]
    print("picked audio: id=%s bw=%s codecs=%s" % (a.get("id"), a.get("bandwidth"), a.get("codecs")), flush=True)
    src = a.get("baseUrl") or a.get("base_url")
    out = sys.argv[1] if len(sys.argv) > 1 else "bili_audio.m4s"
    req = urllib.request.Request(src, headers={
        "User-Agent": UA, "Referer": REF, "Origin": "https://www.bilibili.com",
        "Accept": "*/*", "Accept-Language": "zh-CN,zh;q=0.9",
    })
    with opener.open(req, timeout=60) as r, open(out, "wb") as f:
        n = 0
        while True:
            b = r.read(1 << 20)
            if not b:
                break
            f.write(b)
            n += len(b)
    print("downloaded", n, "bytes ->", os.path.abspath(out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
