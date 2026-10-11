# Hermes runtime layout

Where things actually live when you need to run Python against Hermes' own packages.

- `$HERMES_HOME` — config, `.env`, `logs/`, `sessions/`, `skills/`. Always resolve it from the env
  var; never assume `~/.hermes`, because profiles and Windows installs relocate it.
- `<home>/hermes-agent/` — the source checkout (git installs). `cd` here before importing `pm`,
  `gateway.*`, or `agent.*`.
- `<home>/installs/<install-id>/environments/<env-hash>/venv/` — the runtime venv that `hermes`
  itself executes.
- `<home>/installs/<install-id>/facts.json` — names the **currently active** env hash. A
  `pm.sync_venv` run writes a new hash directory and repoints this file, so a hardcoded venv path goes
  stale after any dependency change.
- `<home>/hermes-agent/.hermes/bin/hermes` — the launcher on `PATH`; it is a shim, not a script.

## Which interpreter

Use the runtime venv's python for anything that needs Hermes' dependencies (`pm`, `gateway.*`,
`agent.*`, adapter libraries). Spell the path out rather than relying on a bare `python`:

- A bare `python` may resolve to an interpreter with none of the venv's site-packages, and on Windows
  PowerShell it resolves to the Microsoft Store alias stub and fails outright.
- Re-read `facts.json`, or run `hermes pm status`, after any dependency change, instead of reusing a
  path captured earlier.

## Probes worth running

| Command | Tells you |
|---|---|
| `hermes pm status` | Last sync receipt: enabled extras, `venv_rebuild.ok` |
| `hermes pm doctor` | Installed tools/packages against the lockfile |
| `hermes gateway status` / `list` | Gateway PID, served profiles |
| `hermes gateway restart` | Stop + respawn; adapters are rebuilt, so this is how a newly enabled platform starts |
| `$HERMES_HOME/logs/gateway.log` | The authoritative reason a platform was skipped or refused |
| `<home>/.env` | Platform credentials (protected file — edit via terminal, see SKILL.md) |
