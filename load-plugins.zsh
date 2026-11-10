# Check-and-load for optional ~/.ksp/plugins.
#
# Sourced from .zshrc (every interactive shell). Per-machine switches are set
# in .zshenv — every shell runs it before .zshrc, so they're visible here.
# Not .zprofile: only login shells run it, so a plain `zsh` would miss them.
# A switch that is unset or 0 skips the plugin.
#
#   KSP_PLUGIN_OP_SECRETS=1   # 1Password secrets loader for tmux panes and IDE terminals

(( KSP_PLUGIN_OP_SECRETS )) && [[ -r ~/.ksp/plugins/op-secrets.zsh ]] && source ~/.ksp/plugins/op-secrets.zsh
return 0
