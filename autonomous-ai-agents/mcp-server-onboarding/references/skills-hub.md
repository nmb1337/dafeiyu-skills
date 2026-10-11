# The Skills Hub — the sibling registry to MCP servers

Same class of work as an MCP server: add an external capability, verify it for real, then tell the
user when it becomes usable. Only the commands differ.

## Discover
- `hermes skills browse --source official` — the curated catalog (hundreds of skills, official first).
- `hermes skills search <kw> --source official --json --limit N` — `--json` is the only clean way to
  read identifiers; the human table wraps long names/identifiers mid-token and mangles them.
- Other sources exist (`skills-sh`, `well-known`, `github`, `clawhub`, `lobehub`, `browse-sh`) and
  `hermes skills inspect <id>` previews before installing — use it on anything not `official`.

## Install / verify
- `printf 'y\n' | hermes skills install <source>/<category>/<name>` — the `Confirm [y/N]` prompt
  reads an empty line as *cancelled*. A batch of installs can exceed the foreground timeout and get
  promoted to a background process; that is fine, just re-read the state afterwards.
- Installed hub skills land in `$HERMES_HOME/skills/<category>/<name>/` (SKILL.md plus its
  `scripts/`, `references/`); confirm with `hermes skills list --source hub`.
- Read the new skill's `scripts/` before promising it works: a helper that fetches templates or
  models over the network fails the first time the user tries it on a host where that CDN is
  unreachable. Prefer skills that are pure-stdlib/Pillow (no GPU, no credentials) for an instant demo,
  and say plainly which ones need the new GPU before they are worth installing.

## Hygiene
- Do not bulk-install: an enabled skill's description is loaded into sessions, so a large library
  costs context and dilutes triggers. Install the two or three that match the request, demo one
  immediately, and offer the rest by name.
- Hub skills are not yours to edit: if one is wrong for this host, record the workaround in your own
  curator-managed skill (e.g. the meme template fetcher needs a working proxy — draw locally instead)
  rather than patching the hub copy.
- When a new skill needs a one-line pointer or a pointer file, put it in the curator-owned skill that
  governs the *task*, not in the hub skill. Hub skills are overwritten on update.
