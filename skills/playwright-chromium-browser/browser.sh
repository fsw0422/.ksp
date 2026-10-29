#!/bin/bash
# One shared, long-running Playwright Chromium for every agent session (macOS).
#   serve  Start Playwright MCP attached to the shared browser; .mcp.json runs this.
#   start  Open the shared browser unless it is already running.
#   hook   Claude Code PreToolUse hook: refuse tab closing, then make sure the browser runs.
# The browser is opened through launchd, so it keeps running after sessions end
# until the user quits it. Every session sees the same window and tabs.
set -euo pipefail

root="${HOME}/.playwright-chromium-browser"
profile="${root}/profile"
# Not 9222: the user's own Chrome may listen there, and attaching to it would drive their real browser.
port="${PW_BROWSER_PORT:-19222}"
endpoint="http://127.0.0.1:${port}"

browser_up() {
	curl -sf --max-time 1 "${endpoint}/json/version" >/dev/null
}

# Prints the newest Chrome for Testing build that Playwright installed.
newest_app() {
	local app rev best="" best_rev=0
	for app in "${PLAYWRIGHT_BROWSERS_PATH:-${HOME}/Library/Caches/ms-playwright}"/chromium-*/chrome-mac*/"Google Chrome for Testing.app"; do
		[[ -d "${app}" ]] || continue
		rev="${app##*/chromium-}"
		rev="${rev%%/*}"
		if [[ "${rev}" =~ ^[0-9]+$ ]] && ((rev > best_rev)); then
			best_rev="${rev}"
			best="${app}"
		fi
	done
	[[ -n "${best}" ]] && printf '%s\n' "${best}"
}

# Succeeds when a running Chromium holds the profile. Chromium marks a profile in
# use with a SingletonLock link to "<host>-<pid>".
profile_busy() {
	local lock pid
	lock=$(readlink "${profile}/SingletonLock" 2>/dev/null || true)
	pid="${lock##*-}"
	[[ "${pid}" =~ ^[0-9]+$ ]] && ps -p "${pid}" -o comm= 2>/dev/null | grep -qi chrom
}

start() {
	local app busy="Another browser is using ${profile} without the shared port ${port}. Quit it with Cmd+Q, then retry."
	browser_up && return 0
	if ! app=$(newest_app); then
		echo "Chrome for Testing is not installed. Run: npx -y @playwright/mcp@latest install-browser chrome-for-testing" >&2
		return 1
	fi
	if profile_busy; then
		echo "${busy}" >&2
		return 1
	fi
	mkdir -p "${profile}"
	# The mock keychain and basic password store match Playwright's own launch, so the
	# profile's saved sign-ins stay readable. The last three keep tabs that are not in
	# front running at full speed.
	open -na "${app}" --args \
		--user-data-dir="${profile}" \
		--remote-debugging-port="${port}" \
		--use-mock-keychain \
		--password-store=basic \
		--no-first-run \
		--no-default-browser-check \
		--disable-background-timer-throttling \
		--disable-backgrounding-occluded-windows \
		--disable-renderer-backgrounding
	for _ in {1..50}; do
		browser_up && return 0
		sleep 0.2
	done
	# A browser that took the profile meanwhile makes the new one hand over and exit.
	if profile_busy; then
		echo "${busy}" >&2
	else
		echo "The shared browser did not open on port ${port}." >&2
	fi
	return 1
}

deny() {
	jq -n --arg reason "$1" '{hookSpecificOutput: {hookEventName: "PreToolUse", permissionDecision: "deny", permissionDecisionReason: $reason}}'
	exit 0
}

hook() {
	local input error
	input=$(cat)
	if [[ "$(jq -r '.tool_name // empty' <<< "${input}")" == *__browser_tabs &&
		"$(jq -r '.tool_input.action // empty' <<< "${input}")" == close ]]; then
		deny "Closing tabs is turned off. Leave the tab open; the user closes tabs."
	fi
	if ! error=$(start 2>&1); then
		deny "${error}"
	fi
}

case "${1:-}" in
	serve) exec npx -y @playwright/mcp@latest --cdp-endpoint "${endpoint}" --output-dir "${root}/output" ;;
	start) start ;;
	hook) hook ;;
	*)
		echo "Usage: bash browser.sh serve|start|hook" >&2
		exit 1
		;;
esac
