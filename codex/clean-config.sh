#!/bin/sh
# Git clean filter for codex/config.toml (see .gitattributes): reads the live config on
# stdin and prints only the portable personal settings. It drops what Codex writes for
# this machine: project trust entries other than ~/projects, ~/.ksp, and ~/jobhunt,
# app-managed paths and services, and marketplace update stamps. Output must not change
# when run on its own output.
exec awk '
function machine_only(name) {
	return (name ~ /^projects\./ && name !~ /^projects\."[^"]*\/(projects|\.ksp|jobhunt)"$/) ||
		name ~ /^mcp_servers\.(node_repl|computer-use)(\.|$)/ ||
		name ~ /^marketplaces\.openai-(bundled|primary-runtime)$/ ||
		name ~ /^shell_environment_policy(\.|$)/
}
/^[[:space:]]*\[/ {
	section = $0
	gsub(/^[[:space:]]*\[+[[:space:]]*|[[:space:]]*\]+[[:space:]]*$/, "", section)
	skip = machine_only(section)
	in_array = 0
}
skip { next }
in_array { if ($0 ~ /\]/) in_array = 0; next }
section == "" && /^[[:space:]]*notify[[:space:]]*=/ { if ($0 !~ /\]/) in_array = 1; next }
section ~ /^marketplaces\./ && /^[[:space:]]*(last_updated|last_revision)[[:space:]]*=/ { next }
/^[[:space:]]*$/ { blank = 1; next }
{
	if (blank && printed) print ""
	blank = 0
	printed = 1
	print
}
'
