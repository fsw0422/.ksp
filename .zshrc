export TERM="xterm-256color"

# Path to your oh-my-zsh installation.
export ZSH="$HOME/.oh-my-zsh"

# Theme to load
ZSH_THEME="powerlevel9k/powerlevel9k"

source $ZSH/oh-my-zsh.sh

# Common System config
stty -ixon
alias schlaf="systemctl suspend -i"
alias open="xdg-open"
if [[ -z "${TMUX}" && "${TERMINAL_EMULATOR}" != "JetBrains-JediTerm" ]]; then tmux; fi
source /usr/local/bin/activate.sh
