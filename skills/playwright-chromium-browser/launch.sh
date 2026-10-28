#!/bin/bash
# Starts Playwright MCP with the options from .mcp.json. Inside a Claude Code
# session it also loads session-tabs.cjs, which keeps that session's open tabs in
# ~/.playwright-chromium-browser/sessions/<session-id>/tabs.json and reopens them
# when the browser starts again. Every session shares the one signed-in profile.
set -euo pipefail

here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
session_id="${CLAUDE_CODE_SESSION_ID:-}"

if [[ "${session_id}" =~ ^[A-Za-z0-9-]+$ ]]; then
	export PW_SESSION_DIR="${PW_SESSIONS_DIR:-${HOME}/.playwright-chromium-browser/sessions}/${session_id}"
	(umask 077 && mkdir -p "${PW_SESSION_DIR}")
	exec npx -y @playwright/mcp@latest "$@" --init-page "${here}/session-tabs.cjs"
fi
exec npx -y @playwright/mcp@latest "$@"
