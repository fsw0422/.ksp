unalias claude 2>/dev/null
claude() {
	# Add `permission-mode` params
	local -a args=("$@")
	(( ${args[(I)--permission-mode]} )) || args=(--permission-mode auto "${args[@]}")

	# Resurrect replay: `--session-id <id>` for a session that already exists in this directory must become `-r <id>` (claude errors on a reused ID).
	local i=${args[(I)--session-id]}
	if (( i )); then
		local id=${args[i+1]}
		[[ -n $id && -s "$HOME/.claude/projects/${PWD//[\/.]/-}/$id.jsonl" ]] && args[i]=-r
		command claude "${args[@]}"
		return
	fi

	# Resolve it to a concrete `-r <id>`
	local ci=${args[(I)-c]}; (( ci )) || ci=${args[(I)--continue]}
	if (( ci )) && ! (( ${args[(I)-p]} + ${args[(I)--print]} )); then
		local -a sess=( "$HOME/.claude/projects/${PWD//[\/.]/-}"/*.jsonl(N.om) )
		if (( ${#sess} )); then
			args[ci]=-r
			args[ci+1,ci]=("${sess[1]:t:r}")
		fi
	fi

	# Plain interactive launch: mint a session ID so this pane's command line is resumable.
	# Skip resumes, one-shots, and subcommands.
	local a skip=0
	for a in "${args[@]}"; do
		case $a in -r|--resume|-c|--continue|-p|--print|-h|--help|-v|--version|update|mcp|agents|plugin|doctor|install|login|logout|setup-token|config|migrate-installer)
			skip=1; break ;;
		esac
	done
	(( skip )) || args+=(--session-id "$(uuidgen | tr '[:upper:]' '[:lower:]')")

	command claude "${args[@]}"
}
