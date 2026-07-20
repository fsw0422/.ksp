OP_SECRETS_VAULT=${OP_SECRETS_VAULT:-Employee}

_op_secret_rows() {
	op item list --vault "$OP_SECRETS_VAULT" --categories "API Credential" --format json | jq -r 'sort_by(.title)[] | [(.title | ascii_upcase | gsub("[^A-Z0-9]+"; "_") | gsub("^_+|_+$"; "")), .title] | @tsv'
}

_op_secrets_complete() {
	[[ -n "$OP_INJECTED_VARS" ]] || return 1
	local var
	for var in ${(s: :)OP_INJECTED_VARS}; do
		[[ -n "${(P)var}" ]] || return 1
	done
	return 0
}

_op_secrets_import() {
	[[ -n "$TMUX" ]] || return 1
	local manifest var line
	manifest=$(tmux show-environment -g OP_INJECTED_VARS 2>/dev/null)
	manifest=${manifest#OP_INJECTED_VARS=}
	[[ -n "$manifest" && "$manifest" != -* ]] || return 1
	for var in ${(s: :)manifest}; do
		line=$(tmux show-environment -g "$var" 2>/dev/null)
		[[ "$line" == "$var="* && "$line" != "$var=-"* ]] && export "$var=${line#${var}=}"
	done
	export OP_INJECTED_VARS="$manifest"
	_op_secrets_complete
}

refresh-op-secrets() {
	local rows var title template resolved
	local -a names
	rows=$(_op_secret_rows) || return 1
	if [[ -z "$rows" ]]; then
		print -u2 "refresh-op-secrets: no API Credential items in vault '$OP_SECRETS_VAULT'."
		return 1
	fi

	template=""
	while IFS=$'\t' read -r var title; do
		names+=("$var")
		template+="export $var=\"{{ op://$OP_SECRETS_VAULT/$title/credential }}\""$'\n'
	done <<< "$rows"

	resolved=$(print -r -- "$template" | op inject) || return 1
	[[ -n "$resolved" ]] || return 1
	source <(print -r -- "$resolved")
	export OP_INJECTED_VARS="${(j: :)names}"

	if [[ -n "$TMUX" ]]; then
		for var in $names; do
			tmux set-environment -g "$var" "${(P)var}"
		done
		tmux set-environment -g OP_INJECTED_VARS "$OP_INJECTED_VARS"

		# Bump the epoch: open panes re-import at their next prompt (precmd hook).
		_OP_SECRETS_SEEN_EPOCH=$(date +%s)
		tmux set-environment -g OP_SECRETS_EPOCH "$_OP_SECRETS_SEEN_EPOCH"
	fi
	print -r -- "refresh-op-secrets: loaded ${#names} secrets from vault '$OP_SECRETS_VAULT'."
}

_load_op_secrets() {
	_op_secrets_complete && return 0
	_op_secrets_import && return 0

	[[ -o interactive && -t 0 ]] || return 0

	refresh-op-secrets >/dev/null 2>&1 || return 0
}

_op_secrets_precmd() {
	local line epoch
	line=$(tmux show-environment -g OP_SECRETS_EPOCH 2>/dev/null) || return 0
	epoch=${line#OP_SECRETS_EPOCH=}
	[[ -z "$epoch" || "$epoch" == "$_OP_SECRETS_SEEN_EPOCH" ]] && return 0
	_OP_SECRETS_SEEN_EPOCH=$epoch
	_op_secrets_import
	return 0
}

_load_op_secrets
unset -f _load_op_secrets
if [[ -n "$TMUX" && -o interactive ]]; then
	_OP_SECRETS_SEEN_EPOCH=$(tmux show-environment -g OP_SECRETS_EPOCH 2>/dev/null)
	_OP_SECRETS_SEEN_EPOCH=${_OP_SECRETS_SEEN_EPOCH#OP_SECRETS_EPOCH=}
	autoload -Uz add-zsh-hook
	add-zsh-hook precmd _op_secrets_precmd
fi
