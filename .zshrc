export LC_ALL=en_US.UTF-8
export LANG=en_US.UTF-8
export TERM="xterm-256color"

# Start TMUX
if [[ -z "${TMUX}" && "${TERMINAL_EMULATOR}" != "JetBrains-JediTerm" && "${TERM_PROGRAM}" != "vscode" ]]; then tmux; fi

# Disable Vim in IDEs
if [[ "$TERMINAL_EMULATOR" == "JetBrains-JediTerm" || "$TERM_PROGRAM" == "vscode" ]]; then
	view() {
		echo "Error: vim should be executed in a dedicated terminal." >&2
		return 1
	}
	vi() {
		echo "Error: vim should be executed in a dedicated terminal." >&2
		return 1
	}
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
alias cs="gh copilot suggest"
alias ce="gh copilot explain"

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
_git_complete() {
	if [[ $CURRENT -eq 2 ]]; then
		local -a branches
		branches=($(git branch --list | sed 's/^[* ]*//'))
		compadd -a branches
	fi
}

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
	git checkout "$base_branch"
	git pull
	git fetch --prune
	for branch in $(git branch --format "%(refname:short)"); do
		if [[ $branch == "$base_branch" ]]; then
			continue
		fi
		if ! git rev-parse --abbrev-ref --symbolic-full-name "$branch@{upstream}" >/dev/null 2>&1; then
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
	if [ "$current_branch" = "$base_branch" ]; then
		echo "Only branches that are NOT main/master is allowed to perform soft rebase. Aborting"
		return 1
	fi
	git reset --soft "$(git merge-base "$base_branch" "$current_branch")"
	git commit -m "$commit_message"
	echo "Branch '$current_branch' squashed with the commit message: '$commit_message'."
}

grm() {
	local base_branch
	base_branch=$(get_base_branch) || return 1
	local current_branch
	current_branch=$(get_current_branch) || return 1
	if [ "$current_branch" = "$base_branch" ]; then
		echo "Error: You are already on the base branch ('$base_branch'). Rebasing is not allowed."
		return 1
	fi
	git fetch origin "$base_branch":"$base_branch"
	git rebase "$base_branch"
	echo "Branch '$current_branch' rebased on top of '$base_branch'."
}

gsbrmfp() {
	gsb "$1" && grm && git push --force origin
}

compdef _git_complete gpb grb

# Pyenv
export PYENV_ROOT="${HOME}/.pyenv"
export PATH="${PYENV_ROOT}/bin:${PATH}"
eval "$(pyenv init --path)"
eval "$(pyenv init -)"

typeset -g PREV_DIR_HAD_VENV=0
typeset -g PREV_DIR_HAD_PYTHON_VERSION=0
typeset -g LAST_PYENV_LOGGED=""

find_nearest_file() {
	local file="$1"
	local dir="$PWD"
	while [[ "${dir}" != "/" ]]; do
		if [[ -f "${dir}/${file}" && -r "${dir}/${file}" ]]; then
			echo "${dir}"
			return 0
		fi
		dir=$(dirname "${dir}")
	done
	return 1
}

load_pyenv_version() {
	local pyenv_dir=$(find_nearest_file ".python-version")
	if [[ -n "${pyenv_dir}" ]]; then
		PREV_DIR_HAD_PYTHON_VERSION=1
		local pyenv_version=$(< "${pyenv_dir}/.python-version")
		if pyenv versions --bare | grep -qx "${pyenv_version}"; then
			if [[ "${LAST_PYENV_LOGGED}" != "${pyenv_dir}" || "$(pyenv version-name)" != "${pyenv_version}" ]]; then
				pyenv shell "${pyenv_version}" 2>/dev/null
				echo "pyenv) ✅ Switched to local Python ${pyenv_version} (from ${pyenv_dir}/.python-version)"
				LAST_PYENV_LOGGED="${pyenv_dir}"
			fi
		else
			echo "pyenv) ❌ Python version ${pyenv_version} is not installed or valid."
			PREV_DIR_HAD_PYTHON_VERSION=0
			LAST_PYENV_LOGGED=""
		fi
	elif [[ ${PREV_DIR_HAD_PYTHON_VERSION} -eq 1 ]]; then
		pyenv shell --unset 2>/dev/null
		echo "pyenv) 🔄 Switched to global Python $(pyenv global)"
		PREV_DIR_HAD_PYTHON_VERSION=0
		LAST_PYENV_LOGGED=""
	fi
}

load_venv() {
	local base_dir=$(find_nearest_file ".venv/bin/activate")
	if [[ -n "${base_dir}" ]]; then
		local venv_dir="${base_dir}/.venv"
		if [[ -d "${venv_dir}" && -f "${venv_dir}/bin/activate" ]]; then
			if [[ "${VIRTUAL_ENV}" != "${venv_dir}" ]]; then
				[[ -n "${VIRTUAL_ENV}" ]] && deactivate 2>/dev/null
				source "${venv_dir}/bin/activate"
				echo "venv) ✅ Activated virtual environment at ${venv_dir}"
				PREV_DIR_HAD_VENV=1
			fi
		fi
	elif [[ ${PREV_DIR_HAD_VENV} -eq 1 && -n "${VIRTUAL_ENV}" ]]; then
		deactivate 2>/dev/null
		echo "venv) 🔄 Deactivated virtual environment"
		PREV_DIR_HAD_VENV=0
	fi
}

venv() {
	echo "Removing existing '.venv' directory if present..."
	rm -rf .venv
	if [[ -f .python-version ]]; then
		local pyenv_version=$(< .python-version)
		if pyenv versions --bare | grep -qx "${pyenv_version}"; then
			echo "pyenv) ✅ Using Python ${pyenv_version} (from .python-version)"
		else
			echo "pyenv) ❌ Python version ${pyenv_version} is not installed or valid."
			return 1
		fi
		python3 -m venv .venv
		local venv_dir="${PWD}/.venv"
		source "${venv_dir}/bin/activate"
		echo "venv) ✅ Activated virtual environment at ${venv_dir}"
		echo "Upgrading pip..."
		pip install --upgrade pip

		if [[ -f pyproject.toml ]]; then
			echo "Found 'pyproject.toml'. Installing project package..."
			pip install .
		elif [[ -f requirements.txt ]]; then
			echo "Found 'requirements.txt' (no pyproject.toml). Installing dependencies..."
			pip install -r requirements.txt
		else
			echo "No 'pyproject.toml' or 'requirements.txt' found. No dependencies installed."
		fi
	else
		echo "pyenv) ❌ '.python-version' not found in current directory. Please create one."
		pyenv versions
		return 1
	fi
}

# NVM
typeset -g PREV_DIR_HAD_NVM_VERSION=0
typeset -g LAST_NVM_LOGGED=""

export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"
[ -s "$NVM_DIR/bash_completion" ] && \. "$NVM_DIR/bash_completion"

load_nvm_version() {
	local nvm_dir=$(find_nearest_file ".nvmrc")
	if [[ -n "${nvm_dir}" ]]; then
		PREV_DIR_HAD_NVM_VERSION=1
		local nvmrc_version=$(< "${nvm_dir}/.nvmrc")
		if nvm ls "${nvmrc_version}" >/dev/null 2>&1; then
			if [[ "${LAST_NVM_LOGGED}" != "${nvm_dir}" || "$(nvm current)" != "$(nvm version "${nvmrc_version}")" ]]; then
				nvm use "${nvmrc_version}" >/dev/null 2>&1
				echo "nvm) ✅ Switched to local Node $(nvm current) (from ${nvm_dir}/.nvmrc)"
				LAST_NVM_LOGGED="${nvm_dir}"
			fi
		else
			echo "nvm) ❌ Node version ${nvmrc_version} is not installed or valid."
			PREV_DIR_HAD_NVM_VERSION=0
			LAST_NVM_LOGGED=""
		fi
	elif [[ ${PREV_DIR_HAD_NVM_VERSION} -eq 1 ]]; then
		nvm use default >/dev/null 2>&1
		echo "nvm) 🔄 Switched to default Node $(nvm current)"
		PREV_DIR_HAD_NVM_VERSION=0
		LAST_NVM_LOGGED=""
	fi
}

# SDKMAN
export SDKMAN_DIR="$HOME/.sdkman"
[[ -s "$HOME/.sdkman/bin/sdkman-init.sh" ]] && source "$HOME/.sdkman/bin/sdkman-init.sh"

# Load all functions
autoload -U add-zsh-hook

add-zsh-hook chpwd load_pyenv_version
add-zsh-hook chpwd load_venv
add-zsh-hook chpwd load_nvm_version

load_pyenv_version
load_venv
load_nvm_version

# Remove all duplicate environmental variables
typeset -U path
