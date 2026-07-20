# Claude Code launcher (always --permission-mode auto).
#
# Every interactive session carries a session ID in its argv, so the command
# tmux-resurrect saves and replays after a reboot resumes the same conversation
# instead of starting a fresh one.
#
#   claude                     new session under a minted ID (restart-proof)
#   claude -n <name>           named session: <name> maps to a fixed ID per
#                              directory, created once, resumed ever after
#   claude --session-id <id>   what a resurrect replay looks like: resumes
#                              <id> if it exists in this directory
#   everything else            passed through untouched (-r, -c, -p, ...)

unalias claude 2>/dev/null
claude() {
	# Named session: map <name> to a fixed session ID, bootstrapped on first use.
	if [[ $1 == -n && -n $2 ]]; then
		local name=$2 map="$HOME/.claude/named-sessions$PWD/$2" id
		shift 2
		if [[ -r $map ]]; then
			id=$(<"$map")
		else
			id=$(uuidgen | tr '[:upper:]' '[:lower:]')
			command claude --permission-mode auto --session-id "$id" -n "$name" -p "Bootstrap for session '$name'. Reply with just OK." >/dev/null || {
				print -u2 "claude: failed to bootstrap session '$name'"
				return 1
			}
			mkdir -p "${map:h}"
			print -r -- "$id" >"$map"
		fi
		command claude --permission-mode auto -r "$id" "$@"
		return
	fi

	local -a args=("$@")
	(( ${args[(I)--permission-mode]} )) || args=(--permission-mode auto "${args[@]}")

	# Resurrect replay: `--session-id <id>` for a session that already exists in
	# this directory must become `-r <id>` (claude errors on a reused ID).
	local i=${args[(I)--session-id]}
	if (( i )); then
		local id=${args[i+1]}
		[[ -n $id && -s "$HOME/.claude/projects/${PWD//[\/.]/-}/$id.jsonl" ]] && args[i]=-r
		command claude "${args[@]}"
		return
	fi

	# Plain interactive launch: mint a session ID so this pane's command line is
	# resumable. Skip resumes, one-shots, and subcommands.
	local a skip=0
	for a in "${args[@]}"; do
		case $a in -r|--resume|-c|--continue|-p|--print|-h|--help|-v|--version|update|mcp|agents|plugin|doctor|install|login|logout|setup-token|config|migrate-installer)
			skip=1; break ;;
		esac
	done
	(( skip )) || args+=(--session-id "$(uuidgen | tr '[:upper:]' '[:lower:]')")

	command claude "${args[@]}"
}
