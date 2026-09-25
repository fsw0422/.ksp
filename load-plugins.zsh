# Check-and-load for optional ~/.ksp/plugins.
#
# Sourced from .zshrc (every interactive shell). Per-machine switches are set
# in .zprofile — login shells run it before .zshrc, so they're visible here.
# A switch that is unset or 0 skips the plugin.
#
#   KSP_PLUGIN_OP_SECRETS=1   # 1Password → tmux-cached secrets loader

(( KSP_PLUGIN_OP_SECRETS )) && [[ -r ~/.ksp/plugins/op-secrets.zsh ]] && source ~/.ksp/plugins/op-secrets.zsh
return 0
