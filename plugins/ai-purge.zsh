# purge-ai-sessions: delete Claude Code and Codex session data — transcripts,
# tool outputs, logs, caches, prompt history, and the session details kept in
# their config files — while keeping settings, logins, skills, plugins, and
# memory. Dry run by default; --yes deletes permanently (no Trash). Deleting
# refuses to start while either tool is running: open sessions would corrupt
# their SQLite databases or simply write the files back.
#
#   purge-ai-sessions [--yes] [--claude-only | --codex-only]

# Each target line is "<label>\t<path>". Paths sharing a label are summed into
# one row of the report.
_ai_purge_claude_targets() {
	setopt localoptions extendedglob nullglob
	local c=$HOME/.claude app="$HOME/Library/Application Support/Claude" p
	# Per-project transcripts plus each session's subagents/ and tool-results/;
	# memory/ is the only per-project directory that survives.
	for p in $c/projects/*/*.jsonl* $c/projects/*/^memory(/); do
		print -r -- "~/.claude/projects/*/ (transcripts, subagents, tool outputs)"$'\t'$p
	done
	for p in \
		$c/{file-history,plans,debug,paste-cache,image-cache,uploads,session-env,sessions,named-sessions,jobs,tasks,todos,shell-snapshots,backups,feedback-bundles,usage-data,statsig,logs} \
		$c/feedback/drafts $c/history.jsonl $c/daemon.log \
		$app/{claude-code-sessions,local-agent-mode-sessions}; do
		print -r -- "${p/#$HOME/~}"$'\t'$p
	done
}

_ai_purge_codex_targets() {
	setopt localoptions extendedglob nullglob
	local x=$HOME/.codex p
	for p in $HOME/Documents/Codex/*(D); do
		print -r -- "~/Documents/Codex/* (thread output folders)"$'\t'$p
	done
	for p in \
		$x/{sessions,archived_sessions,sqlite,shell_snapshots,generated_images,visualizations,attachments,dictation-history,process_manager,thread-writer-locks,.tmp,tmp} \
		$x/{session_index.jsonl,history.jsonl,transcription-history.jsonl} \
		$x/.codex-global-state.json.(bak|backup)*; do
		print -r -- "${p/#$HOME/~}"$'\t'$p
	done
	# Versioned databases (state_5, logs_2, ...) with their -wal/-shm files, one
	# row per database. memories_*.sqlite is deliberately not listed.
	for p in $x/{thread_history,state,logs,queue,goals}_<->.sqlite*; do
		print -r -- "${${p%%.sqlite*}/#$HOME/~}.sqlite*"$'\t'$p
	done
	for p in $HOME/Library/Caches/{Codex,com.openai.codex} $HOME/Library/Logs/com.openai.codex; do
		print -r -- "${p/#$HOME/~}"$'\t'$p
	done
}

# Prints one line per running app that blocks deletion.
_ai_purge_running() {
	local claude=$1 codex=$2
	if (( claude )); then
		pgrep -qf '^([^ ]*/)?claude( |$)' && print "Claude Code (a session, claude agents, or its background daemon)"
		pgrep -qx Claude && print "Claude desktop app"
	fi
	if (( codex )); then
		{ pgrep -qx ChatGPT || pgrep -qf '/codex( .*)? app-server' || pgrep -qx codex } && print "Codex (the ChatGPT app or the codex CLI)"
	fi
	return 0
}

# Drops per-project last-session details (lastSessionId, lastSessionFirstPrompt,
# lastCost, ...) from ~/.claude.json. $1=1 writes the file; prints the key count.
_ai_purge_scrub_claude_json() {
	python3 - "$HOME/.claude.json" "$1" <<'EOF'
import json, os, sys
path, apply = sys.argv[1], sys.argv[2] == "1"
if not os.path.exists(path):
    print(0); sys.exit(0)
with open(path) as f:
    data = json.load(f)
n = 0
for proj in data.get("projects", {}).values():
    for k in [k for k in proj if k.startswith("last") or k == "activeWorktreeSession"]:
        del proj[k]
        n += 1
if apply and n:
    tmp = path + ".purge-tmp"
    with open(tmp, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    os.chmod(tmp, 0o600)
    os.replace(tmp, path)
print(n)
EOF
}

# Drops [projects."~/Documents/Codex/..."] sections (trust entries for thread
# folders, named after the chats) from ~/.codex/config.toml. $1=1 writes the
# file; prints the section count.
_ai_purge_scrub_codex_toml() {
	python3 - "$HOME/.codex/config.toml" "$1" "$HOME/Documents/Codex/" <<'EOF'
import os, re, sys
path, apply, prefix = sys.argv[1], sys.argv[2] == "1", sys.argv[3]
# If the config is a link, write its target so the link survives.
path = os.path.realpath(path)
if not os.path.exists(path):
    print(0); sys.exit(0)
with open(path) as f:
    lines = f.readlines()
header = re.compile(r'^\s*\[')
project = re.compile(r'^\s*\[projects\."([^"]+)"(\]|\.)')
out, skip, n = [], False, 0
for line in lines:
    if header.match(line):
        m = project.match(line)
        skip = bool(m and m.group(1).startswith(prefix))
        n += skip and m.group(2) == "]"
    if not skip:
        out.append(line)
if apply and n:
    tmp = path + ".purge-tmp"
    with open(tmp, "w") as f:
        f.writelines(out)
    os.chmod(tmp, 0o600)
    os.replace(tmp, path)
print(n)
EOF
}

_ai_purge_human() {
	local kb=$1
	if (( kb >= 1048576 )); then printf '%.1fG' $(( kb / 1048576.0 ))
	elif (( kb >= 1024 )); then printf '%.0fM' $(( kb / 1024.0 ))
	else printf '%dK' $kb
	fi
}

purge-ai-sessions() {
	emulate -L zsh
	local yes=0 claude=1 codex=1 arg
	for arg; do
		case $arg in
		--yes) yes=1 ;;
		--claude-only) codex=0 ;;
		--codex-only) claude=0 ;;
		-h|--help)
			print -r -- "usage: purge-ai-sessions [--yes] [--claude-only | --codex-only]"
			print -r -- "Dry run unless --yes. Quit Claude Code, claude agents, the Claude app, and Codex first."
			return 0 ;;
		*) print -u2 -r -- "purge-ai-sessions: unknown option: $arg"; return 2 ;;
		esac
	done
	if (( ! claude && ! codex )); then
		print -u2 "purge-ai-sessions: --claude-only and --codex-only exclude each other."
		return 2
	fi

	local -a running
	running=("${(@f)$(_ai_purge_running $claude $codex)}")
	running=(${running:#})
	if (( yes && ${#running} )); then
		print -u2 "purge-ai-sessions: quit these first, then rerun:"
		print -u2 -rl -- "  - "${^running}
		return 1
	fi

	local -A size count
	local -a order targets
	local tool label p kb total=0 line
	for tool in claude codex; do
		(( ${(P)tool} )) || continue
		while IFS=$'\t' read -r label p; do
			(( ${+size[$label]} )) || order+=($label)
			kb=${$(du -sk -- $p 2>/dev/null)[1]:-0}
			(( size[$label] += kb, count[$label] += 1, total += kb ))
			targets+=($p)
		done < <(_ai_purge_${tool}_targets)
	done

	local claude_keys=0 codex_sections=0
	(( claude )) && claude_keys=$(_ai_purge_scrub_claude_json 0)
	(( codex )) && codex_sections=$(_ai_purge_scrub_codex_toml 0)

	print -r -- "${${yes/1/Deleting}/0/Would delete} ($(_ai_purge_human $total)):"
	for label in $order; do
		(( size[$label] )) || continue  # empty dirs: still deleted, just not worth a row
		line="  $(_ai_purge_human $size[$label])"$'\t'"$label"
		(( count[$label] > 1 )) && line+="  [${count[$label]} items]"
		print -r -- $line
	done
	(( claude_keys )) && print -r -- "  ~/.claude.json: $claude_keys last-session keys"
	(( codex_sections )) && print -r -- "  ~/.codex/config.toml: $codex_sections [projects] entries for ~/Documents/Codex folders"

	if (( ! yes )); then
		if (( ${#running} )); then
			print -r -- "Still running (quit before deleting):"
			print -rl -- "  - "${^running}
		fi
		print -r -- "Dry run: nothing deleted. Rerun with --yes to delete."
		return 0
	fi

	if (( claude_keys || codex_sections )); then
		local backup=${TMPDIR:-/tmp}/ai-purge-$(date +%Y%m%d-%H%M%S)
		mkdir -p -m 700 -- $backup || return 1
		(( claude_keys )) && { cp -p -- ~/.claude.json $backup/ || return 1; _ai_purge_scrub_claude_json 1 >/dev/null || return 1 }
		(( codex_sections )) && { cp -p -- ~/.codex/config.toml $backup/ || return 1; _ai_purge_scrub_codex_toml 1 >/dev/null || return 1 }
		print -r -- "Config backups (cleared on reboot): $backup"
	fi
	(( ${#targets} )) && rm -rf -- $targets
	# Project folders left empty once their sessions are gone (no memory/).
	rmdir -- $HOME/.claude/projects/*(N/^F) 2>/dev/null
	print -r -- "Done: freed about $(_ai_purge_human $total)."
}
