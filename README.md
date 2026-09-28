# Customized Shell Config for Productivity

[Install script](https://github.com/fsw0422/ksp-setup)

## Plugin system

Reusable shell tooling lives in this repo; machine-specific choices live in
untracked dotfiles in `$HOME`. Startup order is the contract:

| File | Runs | Role |
|---|---|---|
| `~/.zprofile` (untracked) | login, before `.zshrc` | per-machine plugin switches + plugin config |
| `~/.zshrc` (this repo) | every interactive shell | sources `load-plugins.zsh` |
| `~/.zlogin` (untracked) | login, after `.zshrc` | machine-local env vars — may rely on plugin-provided values (e.g. secrets) |

New machine setup: clone this repo to `~/.ksp`, create `~/.zprofile` with the
switches you want, and put machine-local exports in `~/.zlogin`:

```zsh
# ~/.zprofile
KSP_PLUGIN_OP_SECRETS=1   # 1Password → tmux-cached secrets loader
KSP_PLUGIN_AI_PURGE=1     # purge-ai-sessions: wipe Claude Code / Codex session data
OP_SECRETS_VAULT=Employee # vault op-secrets reads from
```

A switch that is unset or `0` skips that plugin. Details and all config knobs
are documented in each plugin's header comment.

### plugins/op-secrets.zsh

Templateless 1Password secrets loader. Every **API Credential** item in
`$OP_SECRETS_VAULT` becomes an env var named after its title
(`"Grafana API Key"` → `GRAFANA_API_KEY`), read from the item's built-in
`credential` field. Values resolve once per tmux server and are published to
the tmux global environment; panes inherit without re-authenticating.

- Add a secret: create an API Credential item in the vault, run
  `refresh-op-secrets`.
- Rotate a secret: change it in 1Password, run `refresh-op-secrets` once —
  every open pane re-imports at its next prompt (epoch + precmd hook).
  Long-running processes keep the env they started with; restart them if they
  cache the value.
- Item titles are load-bearing: renaming an item renames the env var.

### plugins/ai-purge.zsh

`purge-ai-sessions` wipes Claude Code and Codex session data: transcripts,
tool outputs, logs, caches, prompt history, and the session details kept in
`~/.claude.json` and `~/.codex/config.toml`. Settings, logins, skills, plugins,
and memory stay.

- `purge-ai-sessions` — dry run: lists what would go, with sizes.
- `purge-ai-sessions --yes` — deletes permanently. Refuses while Claude Code,
  `claude agents`, the Claude app, or Codex is running.
- `--claude-only` / `--codex-only` — limit to one tool.
