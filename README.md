# Customized Shell Config for Productivity

[Install script](https://github.com/fsw0422/ksp-setup)

## Plugin system

Reusable shell tooling lives in this repo; machine-specific choices live in
untracked dotfiles in `$HOME`. Startup order is the contract:

| File | Runs | Role |
|---|---|---|
| `~/.zshenv` (untracked) | every shell, before `.zshrc` | per-machine plugin switches + plugin config |
| `~/.zshrc` (this repo) | every interactive shell | sources `load-plugins.zsh` |
| `~/.zlogin` (untracked) | login, after `.zshrc` | machine-local env vars — can't use op-secrets values, which arrive at the first command |

New machine setup: clone this repo to `~/.ksp`, create `~/.zshenv` with the
switches you want, and put machine-local exports in `~/.zlogin`:

```zsh
# ~/.zshenv
KSP_PLUGIN_OP_SECRETS=1              # 1Password secrets loader for tmux panes and IDE terminals
KSP_PLUGIN_OP_SECRETS_VAULT=Employee # vault op-secrets reads from
```

A switch that is unset or `0` skips that plugin. Details and all config knobs
are documented in each plugin's header comment.

Set the switches in `~/.zshenv`, not `~/.zprofile`: only login shells run
`.zprofile`, so a plain `zsh` or `exec zsh` would start without the plugins.

### plugins/op-secrets.zsh

Templateless 1Password secrets loader. Every **API Credential** item in
`$KSP_PLUGIN_OP_SECRETS_VAULT` becomes an env var named after its title
(`"Grafana API Key"` → `GRAFANA_API_KEY`), read from the item's built-in
`credential` field. Every tmux pane and IDE terminal (VS Code, JetBrains)
loads its own copy from 1Password at startup; other shells never touch
1Password. Nothing is shared through tmux, and a change in one shell does not
reach the others.

Loading runs in the background, so the prompt appears at once, and the first
command waits until the secrets are in. It keeps trying for
`$KSP_PLUGIN_OP_SECRETS_BOOT_WAIT` seconds (default 120), for example while
1Password is locked. If it still fails, the shell says so, and
`refresh-op-secrets` loads them later.

- Add a secret: create an API Credential item in the vault, run
  `refresh-op-secrets`. That shell gets it now, and new shells from then on.
- Rotate a secret: change it in 1Password. New shells read the new value; an
  open shell gets it when you run `refresh-op-secrets` there.
  Long-running processes keep the env they started with; restart them if they
  cache the value.
- Item titles are load-bearing: renaming an item renames the env var. Run
  `refresh-op-secrets` after a rename.
- Only the item list (variable names and titles, never values) is cached, in
  `~/.cache/op-secrets/`. Values are read from 1Password every time.

## AI agent configs

Personal base settings for Claude Code and Codex, shared by every machine.
Shared user instructions, personal skills, and the Playwright browser config
live under [`skills/`](skills/). Work extras live in `~/projects`
(`.claude/settings.json`, `.mcp.json`, `.codex/config.toml`, `AGENTS.md`) and
layer on top of these.

| Live file | Links to |
|---|---|
| `~/.claude/settings.json` | `claude/settings.json` |
| `~/.claude/CLAUDE.md` | `skills/AGENTS.md` |
| `~/.codex/AGENTS.md` | `skills/AGENTS.md` |
| `/etc/codex/config.toml` | `codex/config.toml` |

Codex reads `/etc/codex/config.toml` as its system layer, below the user file
`~/.codex/config.toml`. The user file stays a plain local file for what Codex
writes on its own: trust for new folders, app-managed paths, and update stamps.
Nothing writes to `codex/config.toml`, so it stays as clean as
`claude/settings.json`, the counterpart of `~/.claude.json` holding Claude's
machine state. A setting changed in the Codex app lands in the user file and
overrides the base; copy it into `codex/config.toml` to keep it everywhere.

Project trust is machine state too, so it lives only in the user file. On a new
machine, trust `~/projects` once when Codex asks, or the work layer there does not
load. Linking into `/etc` needs `sudo` once (ksp-setup does this).

`ksp-setup` links each `skills/<name>` directory into the installed platforms.
Both Claude Code and Codex therefore read the same files from this checkout.
