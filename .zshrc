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

# OS specific settings
if [ -d "/run/WSL" ]; then
	export LANGUAGE=en_US.UTF-8
	export XCURSOR_SIZE=16
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

# SDKMAN
export SDKMAN_DIR="$HOME/.sdkman"
[[ -s "$HOME/.sdkman/bin/sdkman-init.sh" ]] && source "$HOME/.sdkman/bin/sdkman-init.sh"

# Load all functions
autoload -U add-zsh-hook

# Remove all duplicate environmental variables
typeset -U path
