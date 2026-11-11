#!/bin/bash
# One shared, long-running Playwright Chromium for every agent session (macOS).
#   serve  Start Playwright MCP attached to the shared browser; .mcp.json runs this.
#   start  Open the shared browser unless it is already running.
#   stop   Quit the shared browser cleanly. Use it when Cmd+Q does not respond.
#   hook   Claude Code PreToolUse hook: refuse tab closing, then make sure the browser runs.
#   path   Print the browser program, for tools that start their own throwaway copy.
#   tidy   Internal: close the startup blank tab once another page opens.
# The browser is opened through launchd, so it keeps running after sessions end
# until the user quits it. Every session sees the same window and tabs.
set -euo pipefail

root="${HOME}/.playwright-chromium-browser"
profile="${root}/profile"
# Not 9222: the user's own Chrome may listen there, and attaching to it would drive their real browser.
port="${PW_BROWSER_PORT:-19222}"
endpoint="http://127.0.0.1:${port}"
startup_url="about:blank"
missing="Chrome for Testing is not installed. Run: npx -y @playwright/mcp@latest install-browser chrome-for-testing"

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

# Prints the pid of the running Chromium that holds the profile. Chromium marks a
# profile in use with a SingletonLock link to "<host>-<pid>".
profile_pid() {
	local lock pid
	lock=$(readlink "${profile}/SingletonLock" 2>/dev/null || true)
	pid="${lock##*-}"
	[[ "${pid}" =~ ^[0-9]+$ ]] && ps -p "${pid}" -o comm= 2>/dev/null | grep -qi chrom && printf '%s\n' "${pid}"
}

profile_busy() {
	profile_pid >/dev/null
}

# Prints the ids of open page tabs, optionally only those showing the given address.
page_ids() {
	curl -sf --max-time 2 "${endpoint}/json/list" |
		jq -r --arg url "${1:-}" '.[] | select(.type == "page" and ($url == "" or .url == $url)) | .id'
}

start() {
	local app busy="Another browser is using ${profile} without the shared port ${port}. Quit it with Cmd+Q, then retry."
	browser_up && return 0
	if ! app=$(newest_app); then
		echo "${missing}" >&2
		return 1
	fi
	if profile_busy; then
		echo "${busy}" >&2
		return 1
	fi
	mkdir -p "${profile}"
	# The mock keychain and basic password store match Playwright's own launch, so the
	# profile's saved sign-ins stay readable. The four flags after them also match it,
	# so the profile's installed extensions (Claude in Chrome among them) and default
	# apps stay off and cannot open tabs of their own. --disable-infobars hides Chrome
	# for Testing's "only for automated testing" bar, which shows on every window,
	# along with Chrome's other infobars. The last three keep tabs that
	# are not in front running at full speed. It opens one blank tab instead of using
	# --no-startup-window: a browser started without a window ignores Cmd+Q and the
	# Dock icon. tidy closes that blank tab once an agent opens a real page.
	open -na "${app}" --args \
		--user-data-dir="${profile}" \
		--remote-debugging-port="${port}" \
		--use-mock-keychain \
		--password-store=basic \
		--disable-extensions \
		--disable-component-extensions-with-background-pages \
		--disable-default-apps \
		--disable-search-engine-choice-screen \
		--no-first-run \
		--no-default-browser-check \
		--disable-infobars \
		--disable-background-timer-throttling \
		--disable-backgrounding-occluded-windows \
		--disable-renderer-backgrounding \
		"${startup_url}"
	for _ in {1..50}; do
		if browser_up; then
			start_tidy
			return 0
		fi
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

# Starts tidy in the background for the startup blank tab. Its output goes to
# /dev/null so the hook, which waits for start's output, does not wait for it.
start_tidy() {
	local id=""
	for _ in {1..25}; do
		id=$(page_ids "${startup_url}" | head -1) || true
		[[ -n "${id}" ]] && break
		sleep 0.2
	done
	[[ -n "${id}" ]] || return 0
	nohup bash "${BASH_SOURCE[0]}" tidy "${id}" </dev/null >/dev/null 2>&1 &
}

# Closes the startup blank tab once another page is open, so the window stays open
# and the tab is never one a person or agent is using. Gives up after an hour, when
# the browser quits, or when the tab leaves the blank page.
tidy() {
	local id="$1" pages
	for _ in {1..3600}; do
		pages=$(page_ids) || return 0
		page_ids "${startup_url}" | grep -qx "${id}" || return 0
		if grep -vqx "${id}" <<< "${pages}"; then
			curl -sf --max-time 2 "${endpoint}/json/close/${id}" >/dev/null || true
			return 0
		fi
		sleep 1
	done
}

# Quits the shared browser with SIGTERM, which saves the profile like Cmd+Q does.
# Forces it only when it is still running after 10 seconds.
stop() {
	local pid
	if ! pid=$(profile_pid); then
		echo "The shared browser is not running."
		return 0
	fi
	kill -TERM "${pid}"
	for _ in {1..50}; do
		ps -p "${pid}" >/dev/null || { echo "The shared browser quit."; return 0; }
		sleep 0.2
	done
	kill -KILL "${pid}"
	echo "The shared browser did not quit within 10 seconds, so it was forced to stop."
}

# Prints the program inside the newest Chrome for Testing app. The mermaid-image
# skill starts its own windowless copy with an empty profile, so it never touches
# the shared browser, its tabs, or its sign-ins.
program_path() {
	local app
	if ! app=$(newest_app); then
		echo "${missing}" >&2
		return 1
	fi
	printf '%s\n' "${app}/Contents/MacOS/Google Chrome for Testing"
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
	stop) stop ;;
	hook) hook ;;
	path) program_path ;;
	tidy) tidy "${2:?tab id}" ;;
	*)
		echo "Usage: bash browser.sh serve|start|stop|hook|path" >&2
		exit 1
		;;
esac
