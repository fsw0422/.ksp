# Check-and-load for optional ~/.ksp/plugins.
#
# Sourced from .zshrc (every interactive shell). Per-machine switches are set
# in .zshenv — every shell runs it before .zshrc, so they're visible here.
# Not .zprofile: only login shells run it, so a plain `zsh` would miss them.
# A switch that is unset or 0 skips the plugin.
#
#   KSP_PLUGIN_OP_SECRETS=1   # 1Password secrets loader for tmux panes and IDE terminals
#   KSP_PLUGIN_AI_PURGE=1     # purge-ai-sessions: wipe Claude Code / Codex session data

(( KSP_PLUGIN_OP_SECRETS )) && [[ -r ~/.ksp/plugins/op-secrets.zsh ]] && source ~/.ksp/plugins/op-secrets.zsh
(( KSP_PLUGIN_AI_PURGE ))   && [[ -r ~/.ksp/plugins/ai-purge.zsh ]]   && source ~/.ksp/plugins/ai-purge.zsh
return 0
