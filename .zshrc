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
export PYENV_ROOT="${HOME}/.pyenv"
export PATH="${PYENV_ROOT}/bin:${PATH}"
if command -v pyenv 1>/dev/null 2>&1; then eval "$(pyenv init -)"; fi

# Direnv setup
eval "$(direnv hook zsh)"

# To customize prompt, run `p10k configure` or edit ~/.p10k.zsh.
[[ ! -f ~/.p10k.zsh ]] || source ~/.p10k.zsh
