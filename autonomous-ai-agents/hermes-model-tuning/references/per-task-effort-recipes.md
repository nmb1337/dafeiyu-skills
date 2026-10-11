# Answering "a different effort level per kind of task"

Request shape: "chat medium, coding highest, scheduled jobs high". One global knob cannot express
that, because resolution is per-job → per-model → global, with per-session overrides on top.
Pick a mechanism and state its setup cost instead of pretending a per-task switch exists.

| Ask | Mechanism | Trade-off |
|---|---|---|
| One level everywhere | global `agent.reasoning_effort` | simplest; no split |
| Differ by model | `agent.reasoning_overrides` + switch model per activity | the model switch IS the task switch; needs a distinct model per activity |
| Differ by session | `/reasoning <level>` in that session | zero setup, manual, lost on the next session |
| Differ by cron job | `reasoning_effort` pin on each job | required for any cron/chat split; set at creation |
| Differ by profile | separate profile with its own config | strongest isolation; own sessions/memory/skills and its own gateway binding |
| Automatic by workspace/task | plugin hook (`pre_api_request`) inspecting cwd/workspace | custom code, fuzzy detection |

Ask what the "task" physically is before offering any of these: a different chat session, a repo
opened in another tool, a scheduled job, or the same chat. If the work happens OUTSIDE Hermes (an
editor, an external coding agent), Hermes effort settings do not apply at all — drop the request
from the plan rather than configuring a level nothing will use.

When one model serves both roles, a per-model override cannot split them — say so and offer the
session, profile, or per-job mechanism instead.

Prefer the lowest-setup mechanism that actually satisfies the ask, and record standing conventions
("chat = medium", "every cron job gets a high pin") outside the skill so future sessions honour
them without re-deriving this table.
