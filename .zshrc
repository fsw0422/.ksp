export TERM="xterm-256color"

# Path to your oh-my-zsh installation.
export ZSH="$HOME/.oh-my-zsh"

# Theme to load
ZSH_THEME=""

source $ZSH/oh-my-zsh.sh

# Common System config
stty -ixon
alias schlaf="systemctl suspend -i"

