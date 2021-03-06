export LC_ALL=en_US.UTF-8
export LANG=en_US.UTF-8
export TERM="xterm-256color"

# Path to your oh-my-zsh installation.
export ZSH="${HOME}/.oh-my-zsh"

# Theme to load
ZSH_THEME="powerlevel10k/powerlevel10k"

# Load plugins
plugins=(docker docker-compose kubectl zsh-autosuggestions)

# Source all oh-my-zsh settings
source ${ZSH}/oh-my-zsh.sh
autoload -Uz compinit; compinit

# Pyenv setup
export PYENV_ROOT="${HOME}/.pyenv"
export PATH="${PYENV_ROOT}/bin:${PATH}"
if command -v pyenv 1>/dev/null 2>&1; then eval "$(pyenv init -)"; fi

# Direnv setup
eval "$(direnv hook zsh)"

# To customize prompt, run `p10k configure` or edit ~/.p10k.zsh.
[[ ! -f ~/.p10k.zsh ]] || source ~/.p10k.zsh

# Alias
alias dswap="find . -type f -name '*.swp' -exec rm -f {} \\;"
alias gdiff="git difftool -y --tool=vimdiff"
alias v="view"
alias k="kubectl"
complete -F __start_kubectl k

# OS specific settings
if [[ "$OSTYPE" == "darwin"* ]]; then
	# Java version change shortcut (Assumes using AdoptOpenJDK)
	# For Linux (Ubuntu), use 'update-alternatives --config java'
	export JAVA_HOME=`/usr/libexec/java_home -v 1.8`
	alias j11="export JAVA_HOME=`/usr/libexec/java_home -v 11`"
	alias j8="export JAVA_HOME=`/usr/libexec/java_home -v 1.8`"

        # Use GNU Grep
	alias grep="ggrep --color=auto"
elif [[ -z ${WSLENV} ]]; then
	# Translation language (may change to another mapping later)
	export LANGUAGE=en_US.UTF-8

	# For X11 workaround in WSL2
	export DISPLAY=$(awk '/nameserver / {print $2; exit}' /etc/resolv.conf 2>/dev/null):0
	export LIBGL_ALWAYS_INDIRECT=1

	# Ruby virtual environment (Used for Jekyll)
	source /etc/profile.d/rvm.sh
fi

# Start TMUX
if [[ -z "${TMUX}" && "${TERMINAL_EMULATOR}" != "JetBrains-JediTerm" && "${TERM_PROGRAM}" != "vscode" ]]; then tmux; fi
