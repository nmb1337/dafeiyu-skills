# Inbound text encoding: recognising and recovering a mangled message

## Symptom
A message arrives as garbage: visible in the bridge log as `text='\ufffd\u053c\uc8fa\ufffd\ufffd\ufffd\u02f2\ufffd@\u04b2\u04aa\ufffd\u0734\ufffd\ufffd\ufffd'`,
and the same string appears in the Hermes turn line (`logs/agent.log`, `conversation turn:`). The sender's own client
showed it correctly — only the bytes that reached the bot are broken.

## Mechanism
The classic fault is a GBK (cp936) encoding read as UTF-8 with `errors="replace"`: every byte that is not valid UTF-8
becomes `U+FFFD`, so those bytes are **lost**, not recoverable. Only the surrounding valid sequences survive.

Confirm the direction first. A Chinese character's GBK byte pair often happens to be a valid 2–3 byte UTF-8 sequence
landing in a rare block (Armenian / Cyrillic / Hangul / Syriac / Tibetan):
`也` = `D2 B2` → `Ҳ` (U+04B2), `要` = `D2 AA` → `Ҫ`, `人` = `C8 CB`, `不` = `B2 BB`.
High-plane single characters mixed with `U+FFFD`, plus an occasional plain ASCII byte, means
**GBK-bytes-read-as-UTF-8** — not Shift-JIS, not UTF-16 damage. Check the tail first: the readable fragment usually sits there
(`也要能处理` decodes cleanly out of that pattern) and anchors everything else.

## Recovery procedure
1. **Get the exact bytes from the log.** The log file is UTF-8, so slice raw bytes in Python rather than trusting a text reader:
   ```python
   data = open('logs/qq-bridge.log','rb').read()
   i = data.find(b'999999901 self=')          # any stable anchor on that line
   print(data[i:i+260]); print(data[i:i+260].hex(' '))
   ```
   Runs of `EF BF BD` are the destroyed bytes, roughly one per bad byte.
2. **Rebuild the original byte stream**: for each visible character take its UTF-8 encoding (that *is* the pair/triple that
   survived) and put one placeholder byte where each `U+FFFD` sits.
3. **Split into GBK pairs** — `byte < 0x81` is a single ASCII byte, `>= 0x81` starts a lead+trail pair — and solve the
   placeholders: anchor on the readable tail, then per position enumerate only bytes that decode to a hanzi common in
   Chinese chat **and** occur in the vocabulary this profile actually uses. Build that vocabulary from the logs, notes and
   memory files (several MB is plenty). Resolve the whole sentence; never report a fragment as the message.
4. **Prove it byte-for-byte before reporting.** Re-encode the candidate to GBK and re-render it exactly as the bridge saw it:
   ```python
   obs = bytes.fromhex('<hex of the observed line bytes>')
   cand = '自检：别人不@也要能处理'
   print(cand.encode('gbk').decode('utf-8','replace').encode('utf-8') == obs)
   ```
   Only candidates that reproduce the observed byte string are admissible. Note that **different** bytes in the destroyed
   positions render identically, so state which characters were inferred ("I read it out of the bytes as …, tell me if a
   character is off") instead of asserting the text as certain — and say it in one line, not as an essay about encodings.
5. **Do not brute force with substring scans.** `for ...: if (c+d) in big_text` over a multi-MB corpus runs for minutes and
   gets killed. Precompute `bigrams = set(zip(txt, txt[1:]))` (and a `set` of the chars) once, then intersect.

## Where the bytes are destroyed
`qq-bridge.py` has two ingresses with different decode behaviour:
- **WS feed** — `json.loads(raw)`: strict UTF-8, so if `U+FFFD` shows up here it was produced *upstream* (the sender's tool or NapCat).
- **HTTP `POST /qq`** — `raw.decode("utf-8", "replace")`: this is where a non-UTF-8 body gets silently destroyed. Fix the
  ingress instead of patching around it:
  ```python
  try:    body = raw.decode('utf-8')
  except UnicodeDecodeError: body = raw.decode('gbk', 'replace')   # log which branch ran
  ```
- A bridge-side "repair the mojibake" step can never be more than a guess (the bytes are already gone); only an ingress that
  decodes correctly preserves the option to recover.

## Working diagnostics around this
- Listener → PID: `netstat -ano | grep LISTENING | grep -E ':(3001|6185|8790|9880|8642|7899) '`, then `tasklist | grep <pid>`.
  `QQ.exe` on `127.0.0.1:3001` is NapCat in-process; the bridge, bot framework, relay and TTS servers each have their own port.
- `curl -s --noproxy '*' http://127.0.0.1:8790/health` gives `ws_connected` + `last_event_at`, which separates "the bridge is
  dead" from "no events are coming" in one call.
- A group whose events arrive but whose sends fail (`retcode 1200`, `HTTP Error 400`) is fabricated/test traffic, not a broken
  send path — see the debugging section of SKILL.md.
