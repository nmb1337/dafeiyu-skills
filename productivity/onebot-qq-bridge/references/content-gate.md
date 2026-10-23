# Content gate — layers, reload timing, false positives, manual re-dispatch

One gate function, `_img_blocked(prompt)` in `scripts/qq-bridge.py`, evaluated by TWO call sites
that reload at different times. Debug and deploy accordingly.

## The two layers
- **Message layer** — the bridge's own handler, before dispatch. Log line:
  `[image] 内容闸门拦下（<uin>）命中='<word>' prompt='<first 50 chars>'`. On a hit the bridge does
  NOT dispatch; it rewrites the turn's content with an instruction for the model to compose the
  refusal in persona. Nothing canned reaches the chat from this layer.
- **Service layer** — `image_service.py` (the spawned worker) re-checks the prompt as defence in
  depth (it can be spawned by anything, not only the bridge). Log line:
  `内容闸门拦下：'<prompt>' 命中='<word>'`, then it sends its own canned line
  「这个本鱼不画哦，换点别的吧～」 and exits without rendering.
- Triage: read the `命中=` value — it names the exact word that fired. Do not infer from the prompt.

## Reload timing (why edits behave asymmetrically)
- The service imports the bridge module **fresh at every spawn** → a gate edit in the file is live
  for new jobs immediately.
- The **running** bridge holds the old function in memory → message-layer retries keep blocking
  until the bridge restarts. Do not hot-restart to force it mid-chat (a restart aborts in-flight
  turns, including the one that would carry your report); record the pending restart for the
  co-managing session in `INBOX.md` and fulfil the order through the service layer instead.

## False positives — context rules for ambiguous words
The list is substring matching, so any word with an innocent second sense over-triggers
(seen live: 「裸露」 inside 「裸露的齿轮传动结构」 refused a pure industrial-mecha order).
Pattern:
- Strong words (裸体 / 全裸 / 不穿衣服 / 生殖器 / 未成年 …) stay plain substrings in `_IMG_BLOCK`.
- Double-meaning words leave the tuple and are gated by proximity: fire only when the word sits
  within a few characters of a person/body word, on either side, and NOT across sentence punctuation
  — so a distant 「少女」 earlier in the same sentence cannot drag it in.

Working example (`裸露`):

```python
import re as _re          # module-level: the file's own helpers import re locally per function

_NUDE_NEAR = _re.compile(
    r"(少女|女生|女孩|女人|身体|肉体|上身|胸部|胸|臀|大腿|腿|肌肤)[^。！？；，,]{0,5}裸露"
    r"|裸露[^。！？；，,]{0,5}(少女|女生|女孩|女人|身体|肉体|上身|胸部|胸|臀|大腿|腿|肌肤)")

# in _img_blocked, after the tuple loop:
if "裸露" in low and _NUDE_NEAR.search(low):
    return "裸露（贴人/身体）"
```

A module-level regex needs its own module-level import — most helpers in that file do
`import re as _re` inside the function, and an import-time NameError would take the whole bridge down.

## Proving a gate edit (both directions, plus policy regressions)
Table-test with the same importlib probe the routing tests use (load the module by path; nothing
starts at import):
- the actual misfiring prompt → passes;
- other innocent uses (裸露的岩石) → pass;
- person forms (裸露的少女 / 少女裸露的肩膀) → blocked;
- strong words unchanged (裸体 / 全裸 / 不穿衣服 / 儿童) → blocked;
- owner's policy cases unchanged (比基尼女孩 → passes; 涩涩/色图 deliberately pass).
Then commit + PROGRESS line as usual. The fix must not move the owner's line — it only stops an
innocent class from being eaten by it.

## Fulfilling a blocked-but-benign order NOW (no restart)
1. Confirm the false positive against the standing policy (explicit red lines only; 擦边 renders).
2. Apply the file fix FIRST. Re-dispatching before the fix makes the worker re-import the OLD file
   and emit a second refusal to the chat — the exact wobble you are trying to avoid.
3. Re-dispatch through the same call the bridge would have made: load `scripts/qq-bridge.py` by path
   with a working interpreter and call `_start_image_gen(umo, prompt)` — same `[:400]` prompt cap as
   the message layer; run `_expand_self_prompt` first for self-referential orders. The worker acks
   「在画了在画了…」, boots ComfyUI itself if the idle watcher shut it down (expect ~15–60 s extra),
   renders, posts 「画好啦…」 + the image, and exits — the visible trail equals a normal dispatch.
4. If a refusal already went out, close with ONE short persona line naming the false alarm
   (「小检查把『裸露的齿轮』当成脱衣服了」) and confirming the image — no jargon, no lecture.
5. PROGRESS + INBOX (pending message-layer restart), commit, release the lease.
