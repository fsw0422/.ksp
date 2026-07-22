# Self-contained secrets: refresh-op-secrets is the single source of truth.
# Every tmux pane and IDE terminal (VS Code, JetBrains) runs it at startup —
# fetching straight from 1Password (one unlock prompt if locked) and exporting
# values as plain data; other shells never touch 1Password. Nothing is shared
# through tmux and nothing propagates between shells: restored/resurrected
# panes fetch fresh at spawn, and after rotating a credential you run
# refresh-op-secrets in the shells that need the new value.
OP_SECRETS_VAULT=${OP_SECRETS_VAULT:-Employee}

_op_secret_rows() {
	op item list --vault "$OP_SECRETS_VAULT" --categories "API Credential" --format json | jq -r 'sort_by(.title)[] | [(.title | ascii_upcase | gsub("[^A-Z0-9]+"; "_") | gsub("^_+|_+$"; "")), .title] | @tsv'
}

# Only accept variable names the row mapper could have produced (uppercase
# alnum/underscore) and never shell-critical names: item titles come from the
# vault, and a title like "path" must not clobber PATH.
_op_secrets_var_ok() {
	[[ $1 =~ '^[A-Z0-9][A-Z0-9_]*$' ]] || return 1
	case $1 in
	PATH|FPATH|CDPATH|MANPATH|MODULE_PATH|HOME|SHELL|ZDOTDIR|IFS|ENV|TMPDIR|PS1|PS2|PS3|PS4|PROMPT|RPROMPT|LD_*|DYLD_*) return 1 ;;
	esac
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

refresh-op-secrets() {
	setopt localoptions pipefail
	local rows var title value fd attempt
	local -a names fds fvars
	local -A new_vals seen

	# The app may still be starting (boot): give the listing a few tries.
	for attempt in 1 2 3; do
		rows=$(_op_secret_rows) && break
		(( attempt == 3 )) && return 1
		sleep 2
	done
	if [[ -z "$rows" ]]; then
		print -u2 "refresh-op-secrets: no API Credential items in vault '$OP_SECRETS_VAULT'."
		return 1
	fi

	# Fetch values with `op read` and export them as plain data: secret
	# material is never sourced/evaluated, so values containing quotes or
	# $(…) cannot execute as shell code. The first read runs alone to absorb
	# the single unlock prompt; the rest run in parallel through process
	# substitution (pipes, not files). Everything is fetched before anything
	# is exported, so a mid-list failure leaves the environment untouched.
	local first=1
	while IFS=$'\t' read -r var title; do
		if ! _op_secrets_var_ok "$var"; then
			print -u2 "refresh-op-secrets: skipping '$title' (unsafe variable name '$var')."
			continue
		fi
		# Two titles can normalize to the same name ("my api-key"/"my api key");
		# silently overwriting would export the wrong credential.
		if [[ -n "${seen[$var]}" ]]; then
			print -u2 "refresh-op-secrets: skipping '$title' ('$var' collides with '${seen[$var]}')."
			continue
		fi
		seen[$var]=$title
		names+=("$var")
		if (( first )); then
			first=0
			value=$(op read "op://$OP_SECRETS_VAULT/$title/credential" 2>/dev/null) || return 1
			[[ -n "$value" ]] || return 1
			new_vals[$var]=$value
		else
			exec {fd}< <(op read "op://$OP_SECRETS_VAULT/$title/credential" 2>/dev/null)
			fds+=("$fd")
			fvars+=("$var")
		fi
	done <<< "$rows"
	(( ${#names} )) || return 1

	local i ok=1
	for (( i = 1; i <= ${#fds}; i++ )); do
		fd=${fds[i]}
		value=$(cat <&$fd)
		exec {fd}<&-
		if [[ -n "$value" ]]; then
			new_vals[${fvars[i]}]=$value
		else
			ok=0
		fi
	done
	(( ok )) || return 1

	# Snapshot current values so the summary can report what changed.
	local -A prev_vals
	local stale prev_manifest="$OP_INJECTED_VARS"
	for var in ${(s: :)prev_manifest}; do
		prev_vals[$var]="${(P)var}"
	done

	local added=0 updated=0 removed=0
	for var in $names; do
		export "$var=${new_vals[$var]}"
		if [[ " $prev_manifest " == *" $var "* ]]; then
			[[ "${prev_vals[$var]}" != "${new_vals[$var]}" ]] && (( updated++ ))
		else
			(( added++ ))
		fi
	done
	# Unset vars from the previous manifest whose op item no longer exists.
	for stale in ${(s: :)prev_manifest}; do
		[[ " ${(j: :)names} " == *" $stale "* ]] || { unset "$stale"; (( removed++ )); }
	done
	export OP_INJECTED_VARS="${(j: :)names}"

	local -a changes
	(( added ))   && changes+=("$added new")
	(( updated )) && changes+=("$updated updated")
	(( removed )) && changes+=("$removed removed")
	local summary="no changes"
	(( ${#changes} )) && summary="${(j:, :)changes}"
	print -r -- "refresh-op-secrets: loaded ${#names} secrets from vault '$OP_SECRETS_VAULT' ($summary)."
}

# Fetch only where secrets belong: tmux panes and IDE terminals. Skip VS
# Code's headless env-probe shell so opening the app never prompts.
_op_secrets_wanted_env() {
	[[ -n "$TMUX" ]] && return 0
	[[ "$TERM_PROGRAM" == vscode && -z "$VSCODE_RESOLVING_ENVIRONMENT" ]] && return 0
	[[ "$TERMINAL_EMULATOR" == JetBrains-JediTerm ]] && return 0
	return 1
}

if [[ -o interactive ]] && _op_secrets_wanted_env; then
	_op_secrets_launch_1password
	# Boot race: shells (and resurrect's restored programs, which run after
	# zshrc) spawn before the vault is unlocked, and unlocking takes human
	# time. Keep retrying until the unlock lands so everything started from
	# this shell inherits the secrets. Ctrl-C skips; the deadline keeps a
	# walked-away boot from hanging shells forever.
	_op_secrets_deadline=$(( $(date +%s) + ${OP_SECRETS_BOOT_WAIT:-120} ))
	while ! refresh-op-secrets >/dev/null 2>&1; do
		if (( $(date +%s) >= _op_secrets_deadline )); then
			print -u2 "op-secrets: secrets not loaded (1Password locked?); run refresh-op-secrets."
			break
		fi
		sleep 3
	done
	unset _op_secrets_deadline
fi
