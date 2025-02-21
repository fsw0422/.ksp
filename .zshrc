export LC_ALL=en_US.UTF-8
export LANG=en_US.UTF-8
export TERM="xterm-256color"

# Start TMUX
if [[ -z "${TMUX}" && "${TERMINAL_EMULATOR}" != "JetBrains-JediTerm" && "${TERM_PROGRAM}" != "vscode" ]]; then tmux; fi

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
alias k="kubectl"
complete -F __start_kubectl k

# OS specific settings
if [ -d "/run/WSL" ]; then
	# Translation language (may change to another mapping later)
	export LANGUAGE=en_US.UTF-8

	# For X11 workaround in WSL2
	export DISPLAY=$(ip route list default | awk '{print $3}'):0
	export LIBGL_ALWAYS_INDIRECT=1
	export XCURSOR_SIZE=16

	# VSCode
	export DONT_PROMPT_WSL_INSTALL=1
	export IJ_LAUNCHER_DEBUG=true
	alias code="code --wait"

	# Intellij
	export PATH=$PATH:~/.local/share/JetBrains/Toolbox/apps/intellij-idea-community-edition/bin
elif [[ $OSTYPE == "darwin"* ]]; then
	# Linuxify (https://github.com/fabiomaia/linuxify)
	alias grep="grep --color=always"
	alias ls="ls --color=always"
	source ~/.linuxify
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

grr() {
	gsb "$1" && grm && git push --force origin
}

grh() {
	git reset HEAD~
}

# Direnv
eval "$(direnv hook zsh)"

# Pyenv
export PYENV_ROOT="${HOME}/.pyenv"
export PATH="${PYENV_ROOT}/bin:${PATH}"
eval "$(pyenv init --path)"
eval "$(pyenv init -)"

venv() {
	if [ -f ".python-version" ]; then
		PYTHON_VERSION=$(pyenv version-name)
		echo "${PYTHON_VERSION} Found. Setting as local version.."

		# Install virtual environment
		python3 -m venv venv
		echo "source venv/bin/activate" >> .envrc
		echo "unset PS1" >> .envrc
		direnv allow

		# Install requirements if exists
		if [ -f "requirements.txt" ]; then
			echo "Installing dependencies from requirements.txt..."
			pip3 install -r requirements.txt
		else
			echo "No 'requirements.txt' found. Installing no dependencies."
		fi
	else
		echo "'.python-version' not found. Please create one."
		pyenv versions
		return 1
	fi
}

# Conda
export CONDA_HOME="${PYENV_ROOT}/versions/miniconda3-latest"
__conda_setup="$("${CONDA_HOME}/bin/conda" shell.bash hook 2>/dev/null)" || true
if [ $? -eq 0 ]; then
	eval "$__conda_setup"
else
	if [ -f "${CONDA_HOME}/etc/profile.d/conda.sh" ]; then
		. "${CONDA_HOME}/etc/profile.d/conda.sh"
	else
		export PATH="${CONDA_HOME}/bin:${PATH}"
	fi
fi
unset __conda_setup
eval "$(direnv hook zsh)"

cenv() {
	conda create --prefix ./cenv python="${1}" -y
	echo "layout_conda ./cenv" >> .envrc
	echo "unset PS1" >> .envrc
	direnv allow
}

# Remove all duplicate environmental variables
typeset -U path
