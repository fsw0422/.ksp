# Self-contained secrets: refresh-op-secrets is the single source of truth.
# Every tmux pane and IDE terminal (VS Code, JetBrains) loads secrets from
# 1Password at startup; other shells never touch 1Password. Nothing is shared
# through tmux and nothing propagates between shells.
#
# Startup is asynchronous so the prompt appears instantly: a background job
# fetches the values while a one-shot preexec hook makes the first command
# wait for it, so no command ever runs without the secrets. The item list
# (variable names and titles — never values) is cached on disk to skip the
# ~3s `op item list`; new or renamed items are picked up by running
# refresh-op-secrets, which relists live and rewrites the cache.
OP_SECRETS_VAULT=${OP_SECRETS_VAULT:-Employee}
_OP_SECRETS_ROWS_CACHE="$HOME/.cache/op-secrets/rows.tsv"

_op_secret_rows_live() {
	setopt localoptions pipefail
	op item list --vault "$OP_SECRETS_VAULT" --categories "API Credential" --format json | jq -r 'sort_by(.title)[] | [(.title | ascii_upcase | gsub("[^A-Z0-9]+"; "_") | gsub("^_+|_+$"; "")), .title] | @tsv'
}

_op_secrets_rows() {
	if [[ -s "$_OP_SECRETS_ROWS_CACHE" ]]; then
		cat -- "$_OP_SECRETS_ROWS_CACHE"
		return 0
	fi
	local rows
	rows=$(_op_secret_rows_live) || return 1
	[[ -n "$rows" ]] || return 1
	_op_secrets_write_cache "$rows"
	print -r -- "$rows"
}

# Owner-only and written via rename so concurrent shells never read a torn file.
_op_secrets_write_cache() {
	local tmp="$_OP_SECRETS_ROWS_CACHE.$$"
	mkdir -p "${_OP_SECRETS_ROWS_CACHE:h}"
	chmod 700 "${_OP_SECRETS_ROWS_CACHE:h}" 2>/dev/null
	print -r -- "$1" >| "$tmp" || return 1
	chmod 600 "$tmp" 2>/dev/null
	mv -f -- "$tmp" "$_OP_SECRETS_ROWS_CACHE"
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

# Read every secret for the rows on stdin and print them framed by $1 (a
# per-run random sentinel a value cannot forge): "SEP VAR" then the raw value
# lines, ending with "SEP ." only after every read succeeded — a partial
# fetch prints nothing. Values are plain data end to end: never sourced or
# evaluated, so quotes or $(…) inside a credential cannot execute. The first
# read runs alone to absorb the single unlock prompt; the rest run in
# parallel through process substitution (pipes, not files).
_op_secrets_read_all() {
	local sep=$1 var title value fd first=1 i ok=1
	local -a names fds fvars
	local -A vals seen
	while IFS=$'\t' read -r var title; do
		if ! _op_secrets_var_ok "$var"; then
			print -u2 "op-secrets: skipping '$title' (unsafe variable name '$var')."
			continue
		fi
		# Two titles can normalize to the same name ("my api-key"/"my api key");
		# silently overwriting would export the wrong credential.
		if [[ -n "${seen[$var]}" ]]; then
			print -u2 "op-secrets: skipping '$title' ('$var' collides with '${seen[$var]}')."
			continue
		fi
		seen[$var]=$title
		names+=("$var")
		if (( first )); then
			first=0
			value=$(op read "op://$OP_SECRETS_VAULT/$title/credential" 2>/dev/null) || return 1
			[[ -n "$value" ]] || return 1
			vals[$var]=$value
		else
			exec {fd}< <(op read "op://$OP_SECRETS_VAULT/$title/credential" 2>/dev/null)
			fds+=("$fd")
			fvars+=("$var")
		fi
	done
	(( ${#names} )) || return 1
	for (( i = 1; i <= ${#fds}; i++ )); do
		fd=${fds[i]}
		value=$(cat <&$fd)
		exec {fd}<&-
		if [[ -n "$value" ]]; then
			vals[${fvars[i]}]=$value
		else
			ok=0
		fi
	done
	(( ok )) || return 1
	for var in $names; do
		print -r -- "$sep $var"
		print -r -- "${vals[$var]}"
	done
	print -r -- "$sep ."
}

# Background half of the async startup fetch: keep trying until the vault
# unlocks or the deadline passes. A read failure with a cache present usually
# means a renamed/deleted item — drop the cache so the retry lists live.
_op_secrets_emit() {
	local sep=$1 deadline=$2 rows
	_op_secrets_launch_1password
	while :; do
		if rows=$(_op_secrets_rows) && [[ -n "$rows" ]] && _op_secrets_read_all "$sep" <<< "$rows"; then
			return 0
		fi
		rm -f -- "$_OP_SECRETS_ROWS_CACHE"
		(( $(date +%s) >= deadline )) && return 1
		sleep 3
	done
}

# Parse sentinel-framed secrets from stdin and export them. Nothing is
# exported unless the end marker arrived, so a truncated fetch leaves the
# environment untouched. Sets _OP_SECRETS_SUMMARY for the caller.
_op_secrets_apply() {
	local sep=$1 line cur="" complete=0 first_line=1
	local -a names
	local -A new_vals
	while IFS= read -r line; do
		if [[ "$line" == "$sep ." ]]; then
			complete=1
			break
		elif [[ "$line" == "$sep "* ]]; then
			cur=${line#"$sep "}
			if ! _op_secrets_var_ok "$cur"; then
				cur=""
				continue
			fi
			names+=("$cur")
			new_vals[$cur]=""
			first_line=1
		elif [[ -n "$cur" ]]; then
			if (( first_line )); then
				new_vals[$cur]="$line"
				first_line=0
			else
				new_vals[$cur]+=$'\n'"$line"
			fi
		fi
	done
	(( complete && ${#names} )) || return 1

	# Snapshot current values so the summary can report what changed.
	local -A prev_vals
	local var stale prev_manifest="$OP_INJECTED_VARS"
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
	_OP_SECRETS_SUMMARY="loaded ${#names} secrets from vault '$OP_SECRETS_VAULT' ($summary)"
	return 0
}

# One-shot preexec hook: block until the background fetch finishes so the
# first command never runs without the secrets, then export and unhook.
_op_secrets_drain() {
	[[ -n "$_OP_SECRETS_FD" ]] || return 0
	local fd=$_OP_SECRETS_FD sep=$_OP_SECRETS_SEP
	unset _OP_SECRETS_FD _OP_SECRETS_SEP
	whence add-zsh-hook >/dev/null && add-zsh-hook -d preexec _op_secrets_drain
	if ! _op_secrets_apply "$sep" <&$fd; then
		exec {fd}<&-
		print -u2 "op-secrets: secrets not loaded (1Password locked?); run refresh-op-secrets."
		return 0
	fi
	exec {fd}<&-
	return 0
}

refresh-op-secrets() {
	# Cancel any pending async startup fetch: this run supersedes it.
	if [[ -n "$_OP_SECRETS_FD" ]]; then
		exec {_OP_SECRETS_FD}<&-
		unset _OP_SECRETS_FD _OP_SECRETS_SEP
		whence add-zsh-hook >/dev/null && add-zsh-hook -d preexec _op_secrets_drain
	fi
	local rows sep out
	rows=$(_op_secret_rows_live) || return 1
	if [[ -z "$rows" ]]; then
		print -u2 "refresh-op-secrets: no API Credential items in vault '$OP_SECRETS_VAULT'."
		return 1
	fi
	_op_secrets_write_cache "$rows"
	sep=$(uuidgen)
	if ! out=$(_op_secrets_read_all "$sep" <<< "$rows"); then
		print -u2 "refresh-op-secrets: failed to load secrets (is 1Password unlocked?)."
		return 1
	fi
	_op_secrets_apply "$sep" <<< "$out" || return 1
	print -r -- "refresh-op-secrets: $_OP_SECRETS_SUMMARY."
}

# Load only where secrets belong: tmux panes and IDE terminals. Skip VS
# Code's headless env-probe shell so opening the app never prompts.
_op_secrets_wanted_env() {
	[[ -n "$TMUX" ]] && return 0
	[[ "$TERM_PROGRAM" == vscode && -z "$VSCODE_RESOLVING_ENVIRONMENT" ]] && return 0
	[[ "$TERMINAL_EMULATOR" == JetBrains-JediTerm ]] && return 0
	return 1
}

if [[ -o interactive ]] && _op_secrets_wanted_env; then
	autoload -Uz add-zsh-hook
	_OP_SECRETS_SEP=$(uuidgen)
	exec {_OP_SECRETS_FD}< <(_op_secrets_emit "$_OP_SECRETS_SEP" $(( $(date +%s) + ${OP_SECRETS_BOOT_WAIT:-120} )) 2>/dev/null)
	add-zsh-hook preexec _op_secrets_drain
fi
