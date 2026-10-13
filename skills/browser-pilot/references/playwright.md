# The playwright-chromium-browser MCP server

Use this browser only in sessions without a built-in browser, as SKILL.md describes. It is a separate Chromium with its own profile, isolated from the user's own Chrome.

- Use only tools exposed by the MCP server named `playwright-chromium-browser`. Clients may normalize hyphens to underscores in tool names; identify the server from the available tool metadata. Never substitute another Playwright server.
- It runs Playwright's Chromium build (Chrome for Testing), never the user's own Chrome, and keeps sign-ins in a persistent profile at `~/.playwright-chromium-browser/profile`, so they survive restarts. The profile holds login cookies: never read, copy, commit, or upload its files.
- If its tools are missing, tell the user to run `bash setup-agent-skills.sh claude` or `bash setup-agent-skills.sh codex` from their `ksp-setup` checkout, then restart the session. The helper registers the server from `~/.ksp/skills/playwright-chromium-browser/.mcp.json` in that tool's user configuration. Stop until it is available; do not fall back to another browser.
- If a tool reports that the browser is not installed, which happens once on a new computer or after Playwright updates its Chromium build, run `npx -y @playwright/mcp@latest install-browser chrome-for-testing`, tell the user it is a one-time download of about 100 MB, and retry the action.

## Output files

The server saves snapshots, console logs, and screenshots automatically in `~/.playwright-chromium-browser/output`. They are temporary browser artifacts that may contain page content, including filled-in forms; treat them as private, never commit or upload them, and never copy them into a calling skill's records.
