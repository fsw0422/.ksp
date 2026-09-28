# Check-and-load for optional ~/.ksp/plugins.
#
# Sourced from .zshrc (every interactive shell). Per-machine switches are set
# in .zprofile — login shells run it before .zshrc, so they're visible here.
# A switch that is unset or 0 skips the plugin.
#
#   KSP_PLUGIN_OP_SECRETS=1   # 1Password → tmux-cached secrets loader
#   KSP_PLUGIN_AI_PURGE=1     # purge-ai-sessions: wipe Claude Code / Codex session data

(( KSP_PLUGIN_OP_SECRETS )) && [[ -r ~/.ksp/plugins/op-secrets.zsh ]] && source ~/.ksp/plugins/op-secrets.zsh
(( KSP_PLUGIN_AI_PURGE ))   && [[ -r ~/.ksp/plugins/ai-purge.zsh ]]   && source ~/.ksp/plugins/ai-purge.zsh
return 0
