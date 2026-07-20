# 1Password secrets loader — publishes secrets to the tmux global environment.
#
# Every "API Credential" item in $OP_SECRETS_VAULT becomes an environment
# variable, named after the item title (upcased, non-alphanumerics → _):
#   "Atlassian API Key" → ATLASSIAN_API_KEY
# No template file and no manual mapping — 1Password is the single source of
# truth. Adding a secret = create an API Credential item in the vault, then
# run `refresh-op-secrets`.
#
# Values are resolved once by an authenticated pane and published (plus a
# manifest of names in OP_INJECTED_VARS) to the tmux global environment, so
# every (re)spawned pane — including tmux-resurrect restored ones — inherits
# them without re-authenticating against op. (Restore is manual via
# prefix+C-r, so an authenticated pane publishes first.)
#
# Configuration (set before sourcing to override):
#   OP_SECRETS_VAULT   1Password vault to read from (default Employee)

OP_SECRETS_VAULT=${OP_SECRETS_VAULT:-Employee}

# "<VAR_NAME>\t<item title>" for every API Credential item in the vault.
_op_secret_rows() {
	op item list --vault "$OP_SECRETS_VAULT" --categories "API Credential" --format json | jq -r '
		sort_by(.title)[] |
		[(.title | ascii_upcase | gsub("[^A-Z0-9]+"; "_") | gsub("^_+|_+$"; "")),
		 .title] | @tsv'
}

# Succeeds only when every variable in the manifest is set and non-empty.
_op_secrets_complete() {
	[[ -n "$OP_INJECTED_VARS" ]] || return 1
	local var
	for var in ${(s: :)OP_INJECTED_VARS}; do
		[[ -n "${(P)var}" ]] || return 1
	done
	return 0
}

# Discover the vault's API Credential items, resolve them with op, export the
# results, and publish them (plus the name manifest) to the tmux global env so
# sibling/restored panes inherit them without calling op themselves. Run after
# adding an item or rotating a key in 1Password.
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
	fi
	print -r -- "refresh-op-secrets: loaded ${#names} secrets from vault '$OP_SECRETS_VAULT'."
}

_load_op_secrets() {
	# Everything from the manifest is already set and non-empty — nothing to do.
	_op_secrets_complete && return 0

	# Prefer values already published to the tmux global environment by an earlier,
	# authenticated pane — no op call (and no auth prompt) needed.
	if [[ -n "$TMUX" ]]; then
		local manifest var line
		manifest=$(tmux show-environment -g OP_INJECTED_VARS 2>/dev/null)
		manifest=${manifest#OP_INJECTED_VARS=}
		if [[ -n "$manifest" && "$manifest" != -* ]]; then
			for var in ${(s: :)manifest}; do
				line=$(tmux show-environment -g "$var" 2>/dev/null)
				[[ "$line" == "$var="* && "$line" != "$var=-"* ]] && export "$var=${line#${var}=}"
			done
			export OP_INJECTED_VARS="$manifest"
			_op_secrets_complete && return 0
		fi
	fi

	# Still missing or empty variables. Only invoke op where its auth prompt can
	# actually be satisfied (a real interactive TTY). During an unattended restore
	# there's no one to approve the prompt, so skip silently and inherit later.
	[[ -o interactive && -t 0 ]] || return 0

	refresh-op-secrets >/dev/null 2>&1 || return 0
}
_load_op_secrets
unset -f _load_op_secrets
