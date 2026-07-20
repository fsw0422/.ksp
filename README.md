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
KSP_PLUGIN_CLAUDE=1       # Claude Code launcher (restart-proof sessions)
OP_SECRETS_VAULT=Employee # vault op-secrets reads from
```

A switch that is unset or `0` skips that plugin. Details and all config knobs
are documented in each plugin's header comment.

### plugins/claude.zsh

Wrapper around Claude Code so every session's command line carries a session
ID — tmux-resurrect replays it after a reboot and the conversation resumes
instead of starting fresh.

- `claude` — new session under a minted ID (restart-proof automatically)
- `claude -n <name>` — named session pinned per directory; rerunning resumes it
- `-r`, `-c`, `-p`, subcommands — pass through untouched

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
