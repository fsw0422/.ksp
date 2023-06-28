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
alias pdb="python3 -m pudb"
alias v="view"
alias k="kubectl"
complete -F __start_kubectl k

# OS specific settings
if [[ ! -z ${WSL_DISTRO_NAME} ]]; then
	# Translation language (may change to another mapping later)
	export LANGUAGE=en_US.UTF-8

	# For X11 workaround in WSL2
	export DISPLAY=$(awk '/nameserver / {print $2; exit}' /etc/resolv.conf 2>/dev/null):0
	export LIBGL_ALWAYS_INDIRECT=1
elif [[ $OSTYPE == "darwin"* ]]; then
	# Linuxify (https://github.com/fabiomaia/linuxify)
	alias grep="grep --color=always"
	alias ls="ls --color=always"
	source ~/.linuxify
fi

# Git
grb() {
    if [ $# -ne 2 ]; then
        echo "Usage: git-rename-branch <old_branch_name> <new_branch_name>"
        return 1
    fi

    local old_branch=$1
    local new_branch=$2

    # Check if the branch exists on local
    if ! git rev-parse --verify --quiet $old_branch > /dev/null; then
        echo "Error: $old_branch does not exist."
        return 1
    fi

    # Rename the local branch
    git branch -m $old_branch $new_branch

    # Check if the branch exists on remote
    if git ls-remote --quiet | grep $old_branch > /dev/null; then
        # Push the new branch to remote and reset the upstream branch
        git push origin -u $new_branch

        # Delete the old branch on remote
        git push origin --delete $old_branch
    else
        echo "Warning: $old_branch does not exist on remote."
    fi
}

gcb() {
    local master_main_branch=""

    # Check if 'main' branch exists, else fall back to 'master'
    if git show-ref --quiet refs/heads/main; then
        master_main_branch="main"
    elif git show-ref --quiet refs/heads/master; then
        master_main_branch="master"
    else
        echo "Neither 'master' nor 'main' branch exists."
        return 1
    fi

    # Switch to 'master' or 'main' branch
    git checkout $master_main_branch

    # Prune remote branches
    git fetch --prune

    # Loop over all local branches
    for branch in $(git branch --format "%(refname:short)"); do
        # Skip 'master' or 'main' branch
        if [[ $branch == $master_main_branch ]]; then
            continue
        fi

        # Check if branch exists on remote
        if ! git rev-parse --abbrev-ref --symbolic-full-name $branch@{upstream} >/dev/null 2>&1; then
            # If branch does not exist on remote, delete it locally
            echo "Deleting branch $branch"
            git branch -d $branch
        fi
    done
}

# Direnv
eval "$(direnv hook zsh)"

# Pyenv
venv () {
	if [ -n "$1" ]; then
		pyenv local ${1}
		python3 -m venv venv
		echo "source venv/bin/activate" >> .envrc
		echo "unset PS1" >> .envrc
		direnv allow
	else
		echo "Python version not specified. Please choose from below versions"
		pyenv versions
	fi
}
export PYENV_ROOT="${HOME}/.pyenv"
export PATH="${PYENV_ROOT}/bin:${PATH}"
eval "$(pyenv init --path)"
eval "$(pyenv init -)"

# Remove all duplicate environmental variables
typeset -U path
