export LC_ALL=C.UTF-8
export LANG=C.UTF-8
export TERM="xterm-256color"

# Path to your oh-my-zsh installation.
export ZSH="${HOME}/.oh-my-zsh"

# Theme to load
ZSH_THEME="powerlevel10k/powerlevel10k"

# Load plugins
plugins=(docker docker-compose)

# Source all oh-my-zsh settings
source ${ZSH}/oh-my-zsh.sh
autoload -Uz compinit; compinit

# Common System config
alias schlaf="systemctl suspend -i"
if [[ -z "${TMUX}" && "${TERMINAL_EMULATOR}" != "JetBrains-JediTerm" && "${TERM_PROGRAM}" != "vscode" ]]; then tmux; fi

# Pyenv setup
export PATH="${HOME}/.pyenv/bin:${PATH}"
eval "$(pyenv init -)"

# Direnv setup
eval "$(direnv hook zsh)"

# To customize prompt, run `p10k configure` or edit ~/.p10k.zsh.
[[ ! -f ~/.p10k.zsh ]] || source ~/.p10k.zsh
