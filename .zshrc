export TERM="xterm-256color"

# Path to your oh-my-zsh installation.
export ZSH="$HOME/.oh-my-zsh"

# Theme to load
ZSH_THEME="powerlevel9k/powerlevel9k"

source $ZSH/oh-my-zsh.sh
autoload -Uz compinit; compinit

# Common System config
stty -ixon
alias schlaf="systemctl suspend -i"
alias open="xdg-open"
if [[ -z "${TMUX}" && "${TERMINAL_EMULATOR}" != "JetBrains-JediTerm" && "${TERM_PROGRAM}" != "vscode" ]]; then tmux; fi
eval "$(direnv hook zsh)"

# For Session logging in Chrome and Firefox (make sure to open browser in command line to pickup the environmental variable)
export SSLKEYLOGFILE=~/sslkeylog.log

source ~/.careem
