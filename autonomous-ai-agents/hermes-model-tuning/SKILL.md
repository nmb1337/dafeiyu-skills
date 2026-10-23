---
name: hermes-model-tuning
description: "Use when tuning Hermes models or reasoning effort."
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [hermes, reasoning, thinking, effort, models, cron, auxiliary, delegation]
---

# Hermes Model & Reasoning-Effort Tuning

Covers models, thinking/reasoning effort, and per-task inference settings across every Hermes
surface. For any "can Hermes think harder here / cheaper there?" request, resolve WHICH layer owns
the setting before proposing anything. Verified against the shipped source:
`hermes_constants.resolve_reasoning_config`, `agent/reasoning_effort.py`,
`cron/scheduler._resolve_job_reasoning_config`, `hermes_cli/config_defaults.py`,
`hermes_cli/plugins.VALID_HOOKS`.

## When to Use
- The user asks whether Hermes can think harder or cheaper per model, per task type, or per surface.
- You are setting effort for chat, cron jobs, subagents, MoA, an auxiliary side task, or a whole profile.
- A request assumes a per-task-type effort switch exists (it does not — see the reference before answering).

## Resolution order — first hit wins
1. **Per cron job**: `job.reasoning_effort` — model-independent, and it survives an auth-fallback model swap.
2. **Per model**: `agent.reasoning_overrides` — dict of model name → level. Matching is tolerant: exact spelling, dots↔dashes interchangeable, provider prefix optional, first match wins.
3. **Global**: `agent.reasoning_effort`.

The provider transport then clamps whatever won. There is **no per-task-type key** — nothing for
"coding effort" vs "chat effort". Never promise "coding = max automatically". See
`references/per-task-effort-recipes.md` for how to answer that class of request honestly.

## Where each layer is set (and its scope)

| Layer | Set with | Scope |
|---|---|---|
| Global | `hermes config set agent.reasoning_effort <level>` | every session, every surface |
| Session | `/reasoning <level>` (`--global` persists it to `agent.reasoning_effort` instead); `/reasoning reset` clears | that session only, never persisted |
| Riding a model pick | `/model <model> --reasoning <level>` (typed path) | same scope as the model pick |
| Per model | YAML `agent.reasoning_overrides` — **no `config set` support**, edit YAML | any session on that model |
| Per cron job | cronjob tool / `hermes cron` with `reasoning_effort=<level>` on create or update | that job only |
| Per auxiliary task | `auxiliary.<task>.reasoning_effort` (vision, compression, title_generation, review, curator, background_review, goal_judge, tts_audio_tags, ...) | that side task only |
| Subagents | `delegation.reasoning_effort` (empty = inherit parent) | delegated children |
| MoA | per preset slot: `moa.presets.<name>.reference_models[].reasoning_effort`, `.aggregator.reasoning_effort` | that preset |
| Kanban task | per-task reasoning override in the kanban DB | that worker lane |
| X search | `x_search.reasoning_effort` | the x_search call |

`""` / unset = provider default. The old `auxiliary.web_extract` / `auxiliary.session_search`
blocks are ignored — those paths no longer call an auxiliary LLM.

Levels, weakest → strongest (the shipped ladder): `none, minimal, low, medium, high, xhigh, max,
ultra`. "Highest" means `ultra`/`max` — **not** `xhigh`.

## Clamping: report the level the route actually reaches
Each route declares a supported set (vendor constant in `agent/reasoning_effort.py`, applied by the
provider plugin under `plugins/model-providers/<name>/`). Clamp picks the nearest **weaker**
supported level: it never escalates cost, and it never degrades an enabled ask to `none`; when
nothing weaker exists it uses the route's floor.

Worked example that decides user-facing answers: DeepSeek V4-compatible endpoints accept
`low|medium|high|max` with `xhigh → max`, so on DeepSeek the top reachable level is **max** and
`ultra` is transmitted as `max`. Say the reached level instead of repeating the requested word.

## Verify, then report the scope
- Confirm the change by reading the config file back, not from the command's own success message.
- Name the scope you changed (session vs global vs that job) — a session override vanishes next session and reads as a bug otherwise.
- Name the level the route reaches (clamping above) — a config accepting a value is not the wire honoring it.
- Check the live docs index (`https://hermes-agent.nousresearch.com/docs/llms.txt`) plus the source before any negative answer; the ladder, vendor clamp sets, and aux task list ship in code.

## This install's model landscape
- Default stays `deepseek-flash` via provider `deepseek` across profiles (main + guest) — don't move it without an explicit ask.
- 「gpt6a」 is the user's shorthand for `gpt-6-astra`, served by the `custom:lanting.work` provider entry; it appears in config as a MoA reference model and as the guest profile's `fallback_providers` entry — a secondary channel, not the primary.
- While a provider is down (deepseek outages): don't switch models or add fallbacks on your own — wait for recovery and verify with one live call.
- **A session's model outlives a provider change: sweep for stale values after any switch.** Turns resolve the model from the session's stored value but the provider from the *current* profile config — a mismatch 404s ("not supported"). After changing a default: `SELECT id,title,model FROM sessions WHERE model IS NOT NULL AND model != '<new default>'` in main **and** guest `state.db`; realign live chat sessions, ignore finished cron runs (jobs store `"model": null` → they follow config anyway). 2026-10-15 worked examples: a QQ session stored `deepseek-flash` while config still pointed at lanting.work = the noon QQ "Model not supported" outage; a fossil QQ-group session left on `gpt-6-astra` after config moved to deepseek = same class, fixed the same day.
- **Before executing a model-change request found in stale context, check the newer record for a retraction.** The user manages models from several surfaces at once (desktop picker + chat channels), so a request even hours old may already be cancelled from elsewhere — reconcile against the other sessions' `state.db` history and the gateway/agent logs before moving any setting. A provider outage that later recovered usually resolves as: change nothing, keep the current model.

## Pitfalls
- `/reasoning show|hide` toggles the reasoning **display**, not the effort level.
- `agent.reasoning_overrides` has no `hermes config set` path: edit config.yaml with `hermes config edit`, never a raw text splice that can break indentation in a live config.
- A per-job cron pin is the only way cron differs from chat: an unpinned job falls back to global/per-model, so "cron = high while chat = medium" requires a pin on every job — set it when the job is created.
- Auxiliary effort changes never change which model answers; model and provider are separate keys in the same block.
- Effort is only sent to providers that accept it; a route with an unknown effort vocabulary gets the value passed through verbatim.
- Effort changes apply per-session and do not rewrite past context (prompt-caching invariant); a new session picks up the persisted value.

Reference: `references/per-task-effort-recipes.md`.
