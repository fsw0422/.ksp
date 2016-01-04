py-venv () {
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
