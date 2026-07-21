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
	command -v tmux >/dev/null 2>&1 || return 1
	tmux has-session 2>/dev/null || return 1
	local manifest var line
	manifest=$(tmux show-environment -g OP_INJECTED_VARS 2>/dev/null)
	manifest=${manifest#OP_INJECTED_VARS=}
	[[ -n "$manifest" && "$manifest" != -* ]] || return 1
	# Drop vars that were in this shell's previous manifest but no longer exist.
	local stale
	for stale in ${(s: :)OP_INJECTED_VARS}; do
		[[ " $manifest " == *" $stale "* ]] || unset "$stale"
	done
	for var in ${(s: :)manifest}; do
		line=$(tmux show-environment -g "$var" 2>/dev/null)
		[[ "$line" == "$var="* && "$line" != "$var=-"* ]] && export "$var=${line#${var}=}"
	done
	export OP_INJECTED_VARS="$manifest"
	_op_secrets_complete
}

_op_secrets_tmux_publish() {
	local var epoch prev stale
	command -v tmux >/dev/null 2>&1 || return 0
	tmux has-session 2>/dev/null || return 0
	# Deleted secrets: mark them removed on the server (-r also blocks
	# inheritance into new panes); open shells unset them on import.
	prev=$(tmux show-environment -g OP_INJECTED_VARS 2>/dev/null)
	prev=${prev#OP_INJECTED_VARS=}
	if [[ -n "$prev" && "$prev" != -* ]]; then
		for stale in ${(s: :)prev}; do
			[[ " $* " == *" $stale "* ]] || tmux set-environment -gr "$stale" 2>/dev/null
		done
	fi
	for var in "$@"; do
		tmux set-environment -g "$var" "${(P)var}"
	done
	tmux set-environment -g OP_INJECTED_VARS "$*"
	epoch=$(date +%s)
	tmux set-environment -g OP_SECRETS_EPOCH "$epoch"
	print -r -- "$epoch"
}

refresh-op-secrets() {
	local rows var title template resolved epoch
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

	# Snapshot current values so the summary can report what changed.
	local -A prev_vals
	local stale prev_manifest="$OP_INJECTED_VARS"
	for var in ${(s: :)prev_manifest}; do
		prev_vals[$var]="${(P)var}"
	done

	resolved=$(print -r -- "$template" | op inject) || return 1
	[[ -n "$resolved" ]] || return 1
	source <(print -r -- "$resolved")

	local added=0 updated=0 removed=0
	for var in $names; do
		if [[ " $prev_manifest " == *" $var "* ]]; then
			[[ "${prev_vals[$var]}" != "${(P)var}" ]] && (( updated++ ))
		else
			(( added++ ))
		fi
	done
	# Unset vars from the previous manifest whose op item no longer exists.
	for stale in ${(s: :)prev_manifest}; do
		[[ " ${(j: :)names} " == *" $stale "* ]] || { unset "$stale"; (( removed++ )); }
	done
	export OP_INJECTED_VARS="${(j: :)names}"

	epoch=$(_op_secrets_tmux_publish $names)
	[[ -n "$TMUX" && -n "$epoch" ]] && _OP_SECRETS_SEEN_EPOCH=$epoch
	local -a changes
	(( added ))   && changes+=("$added new")
	(( updated )) && changes+=("$updated updated")
	(( removed )) && changes+=("$removed removed")
	local summary="no changes"
	(( ${#changes} )) && summary="${(j:, :)changes}"
	print -r -- "refresh-op-secrets: loaded ${#names} secrets from vault '$OP_SECRETS_VAULT' ($summary)."
}

_op_secrets_notify() {
	if [[ "$OSTYPE" == darwin* ]]; then
		command -v osascript >/dev/null 2>&1 && osascript -e "display notification \"$1\" with title \"op-secrets\"" 2>/dev/null
	elif command -v notify-send >/dev/null 2>&1; then
		notify-send "op-secrets" "$1" 2>/dev/null
	fi
	return 0
}

_op_secrets_launch_1password() {
	if [[ "$OSTYPE" == darwin* ]]; then
		pgrep -x 1Password >/dev/null 2>&1 && return 0
		open -gja 1Password 2>/dev/null && sleep 3
	elif command -v 1password >/dev/null 2>&1; then
		pgrep -x 1password >/dev/null 2>&1 && return 0
		1password --silent >/dev/null 2>&1 &!
		sleep 3
	fi
	return 0
}

_op_secrets_waiter() {
	local lock="${TMPDIR:-/tmp}/op-secrets-waiter.$UID.lock"
	mkdir "$lock" 2>/dev/null || return 0

	{
		local delay i
		_op_secrets_launch_1password
		for delay in ${(s: :)${OP_SECRETS_WAITER_DELAYS:-0 5 10 20 40}}; do
			sleep "$delay"
			if refresh-op-secrets >/dev/null 2>&1; then
				_op_secrets_notify "Secrets loaded into environment"
				# Secrets loaded before any tmux server exists: wait for one
				# so open shells get a bus to import from, then publish.
				if ! tmux has-session 2>/dev/null; then
					for i in {1..180}; do
						sleep 5
						if tmux has-session 2>/dev/null; then
							_op_secrets_tmux_publish ${(s: :)OP_INJECTED_VARS} >/dev/null
							break
						fi
					done
				fi
				return 0
			fi
		done
		return 1
	} always {
		rmdir "$lock" 2>/dev/null
	}
}

_load_op_secrets() {
	_op_secrets_complete && return 0
	_op_secrets_import && return 0

	[[ -o interactive && -t 0 ]] || return 0

	print -u2 "op-secrets: loading secrets in background (1Password may prompt)…"
	(_op_secrets_waiter >/dev/null 2>&1 &)
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

_op_secrets_outer_precmd() {
	if _op_secrets_complete || _op_secrets_import; then
		add-zsh-hook -d precmd _op_secrets_outer_precmd
	fi
	return 0
}

_load_op_secrets
unset -f _load_op_secrets
if [[ -o interactive ]]; then
	autoload -Uz add-zsh-hook
	if [[ -n "$TMUX" ]]; then
		_OP_SECRETS_SEEN_EPOCH=$(tmux show-environment -g OP_SECRETS_EPOCH 2>/dev/null)
		_OP_SECRETS_SEEN_EPOCH=${_OP_SECRETS_SEEN_EPOCH#OP_SECRETS_EPOCH=}
		add-zsh-hook precmd _op_secrets_precmd
	elif ! _op_secrets_complete; then
		add-zsh-hook precmd _op_secrets_outer_precmd
	fi
fi
