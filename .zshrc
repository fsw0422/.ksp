export LC_ALL=en_US.UTF-8
export LANG=en_US.UTF-8
export TERM="xterm-256color"

# Start TMUX
if [[ -z "${TMUX}" && "${TERMINAL_EMULATOR}" != "JetBrains-JediTerm" && "${TERM_PROGRAM}" != "vscode" ]]; then tmux; fi

# Disable Vim in IDEs
if [[ "$TERMINAL_EMULATOR" == "JetBrains-JediTerm" || "$TERM_PROGRAM" == "vscode" ]]; then
	vim() {
		echo "Error: vim should be executed in a dedicated terminal." >&2
		return 1
	}

	nano() {
		echo "Error: nano should be executed in a dedicated terminal." >&2
		return 1
	}
fi

# Oh-My-ZSH
export ZSH="${HOME}/.oh-my-zsh"
ZSH_THEME="powerlevel10k/powerlevel10k"
[[ ! -f ~/.p10k.zsh ]] || source ~/.p10k.zsh
plugins=(docker docker-compose kubectl zsh-autosuggestions)
source ${ZSH}/oh-my-zsh.sh
autoload -Uz compinit; compinit

# Alias
alias del_swp="find . -type f -name '*.swp' -exec rm -f {} \\;"
alias v="view"

# OS specific settings
if [ -d "/run/WSL" ]; then
	# Translation language (may change to another mapping later)
	export LANGUAGE=en_US.UTF-8

	# For X11 workaround in WSL2
	export DISPLAY=$(ip route list default | awk '{print $3}'):0
	export LIBGL_ALWAYS_INDIRECT=1
	export XCURSOR_SIZE=16

	# Intellij
	export PATH=$PATH:~/.local/share/JetBrains/Toolbox/apps/intellij-idea-community-edition/bin
elif [[ $OSTYPE == "darwin"* ]]; then
	# Linuxify (https://github.com/fabiomaia/linuxify)
	alias grep="grep --color=always"
	alias ls="ls --color=always"
	source ~/.linuxify
	export CPPFLAGS="-I$(brew --prefix)/include"
	export LDFLAGS="-L$(brew --prefix)/lib"
fi

# Git
get_base_branch() {
	local base_branch=""
	if git show-ref --quiet refs/heads/main; then
		base_branch="main"
	elif git show-ref --quiet refs/heads/master; then
		base_branch="master"
	else
		echo "Neither 'master' nor 'main' branch exists."
		return 1
	fi
	echo "$base_branch"
}

get_current_branch() {
	local current_branch
	current_branch=$(git branch --show-current)
	if [ -z "$current_branch" ]; then
		echo "Error: Unable to determine the current branch."
		return 1
	fi
	echo "$current_branch"
}

gpb() {
	local base_branch
	base_branch=$(get_base_branch) || return 1

	# Switch to base branch
	git checkout "$base_branch"

	git push origin --delete "$1"
	git branch -D "$1"
}

grb() {
	local old_branch="$1"
	local new_branch="$2"

	git branch -m "$old_branch" "$new_branch"
	git push origin --delete "$old_branch"
	git push --set-upstream origin "$new_branch"

	echo "Branch renamed from '$old_branch' to '$new_branch' successfully."
}

gcb() {
	local base_branch
	base_branch=$(get_base_branch) || return 1

	# Switch to base branch and update
	git checkout "$base_branch"
	git pull

	# Prune remote branches
	git fetch --prune

	# Loop over all local branches
	for branch in $(git branch --format "%(refname:short)"); do
		# Skip base branch
		if [[ $branch == "$base_branch" ]]; then
			continue
		fi

		# Check if branch exists on remote
		if ! git rev-parse --abbrev-ref --symbolic-full-name "$branch@{upstream}" >/dev/null 2>&1; then
			# Delete branch locally if it doesn't exist on remote
			echo "Deleting branch $branch"
			git branch -D "$branch"
		fi
	done
}

gsb() {
	local base_branch
	base_branch=$(get_base_branch) || return 1

	local commit_message="$1"
	if [ -z "$commit_message" ]; then
		echo "Usage: gsb <commit-message>"
		return 1
	fi

	local current_branch
	current_branch=$(get_current_branch) || return 1

	# Check if the current branch is the base branch
	if [ "$current_branch" = "$base_branch" ]; then
		echo "Only branches that are NOT main/master is allowed to perform soft rebase. Aborting"
		return 1
	fi

	# Squash commits
	git reset --soft "$(git merge-base "$base_branch" "$current_branch")"
	git commit -m "$commit_message"

	echo "Branch '$current_branch' squashed with the commit message: '$commit_message'."
}

grm() {
	local base_branch
	base_branch=$(get_base_branch) || return 1

	local current_branch
	current_branch=$(get_current_branch) || return 1

	# Check if the current branch is the base branch
	if [ "$current_branch" = "$base_branch" ]; then
		echo "Error: You are already on the base branch ('$base_branch'). Rebasing is not allowed."
		return 1
	fi

	# Pull the latest changes on the base branch without checking it out
	git fetch origin "$base_branch":"$base_branch"

	# Rebase onto base branch
	git rebase "$base_branch"

	echo "Branch '$current_branch' rebased on top of '$base_branch'."
}

gsbrmfp() {
	gsb "$1" && grm && git push --force origin
}

# Direnv
eval "$(direnv hook zsh)"

# Pyenv
export PYENV_ROOT="${HOME}/.pyenv"
export PATH="${PYENV_ROOT}/bin:${PATH}"
eval "$(pyenv init --path)"
eval "$(pyenv init -)"

PREV_DIR_HAD_PYTHON_VERSION=0
autoload -U add-zsh-hook
load_pyenv_version() {
	if [[ -f .python-version && -r .python-version ]]; then
		PREV_DIR_HAD_PYTHON_VERSION=1
		local pyenv_version=$(cat .python-version)
		if pyenv versions --bare | grep -qx "$pyenv_version"; then
			echo "✅ Switched to Python $pyenv_version (from .python-version)"
		else
			echo "❌ Python version $pyenv_version is not installed. Install it with: pyenv install $pyenv_version"
		fi
	else
		if [[ $PREV_DIR_HAD_PYTHON_VERSION -eq 1 ]]; then
			echo "🔄 Switched back to the global Python version $(pyenv global)"
			PREV_DIR_HAD_PYTHON_VERSION=0
		fi
	fi
}
add-zsh-hook chpwd load_pyenv_version
load_pyenv_version

venv() {
	rm -rf venv
	rm -f .envrc
	if [ -f ".python-version" ]; then
		PYTHON_VERSION=$(pyenv version-name)
		echo "${PYTHON_VERSION} Found. Setting as local version.."

		# Install virtual environment
		python3 -m venv venv
		echo "source venv/bin/activate" >> .envrc
		echo "unset PS1" >> .envrc
		direnv allow
		venv/bin/pip install --upgrade pip

		# Install requirements if exists
		if [ -f "requirements.txt" ]; then
			echo "Installing dependencies from requirements.txt..."
			venv/bin/pip install -r requirements.txt
		else
			echo "No 'requirements.txt' found. Installing no dependencies."
		fi
	else
		echo "'.python-version' not found. Please create one."
		pyenv versions
		return 1
	fi
}

# NVM
export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"
[ -s "$NVM_DIR/bash_completion" ] && \. "$NVM_DIR/bash_completion"

autoload -U add-zsh-hook
load_nvmrc() {
	if [[ -f .nvmrc && -r .nvmrc ]]; then
		local nvmrc_version=$(cat .nvmrc)
		nvm use
	elif [[ $(nvm version) != $(nvm version default) ]]; then
		nvm use default
	fi
}
add-zsh-hook chpwd load_nvmrc
load_nvmrc

# SDKMAN
export SDKMAN_DIR="$HOME/.sdkman"
[[ -s "$HOME/.sdkman/bin/sdkman-init.sh" ]] && source "$HOME/.sdkman/bin/sdkman-init.sh"

# Remove all duplicate environmental variables
typeset -U path
