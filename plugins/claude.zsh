unalias claude 2>/dev/null
claude() {
	# Named session: map <name> to a fixed session ID. The first run creates the
	# session interactively (headless -p bootstraps never show in the --resume
	# picker); later runs resume it. A map entry without a transcript means the
	# first run was quit before any message - create again with the same ID.
	if [[ $1 == -n && -n $2 ]]; then
		local name=$2 map="$HOME/.claude/named-sessions$PWD/$2" id
		shift 2
		if [[ -r $map ]]; then
			id=$(<"$map")
		else
			id=$(uuidgen | tr '[:upper:]' '[:lower:]')
			mkdir -p "${map:h}"
			print -r -- "$id" >"$map"
		fi
		if [[ -s "$HOME/.claude/projects/${PWD//[\/.]/-}/$id.jsonl" ]]; then
			command claude --permission-mode auto -r "$id" "$@"
		else
			command claude --permission-mode auto --session-id "$id" -n "$name" "$@"
		fi
		return
	fi

	# Add `permission-mode` params
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
