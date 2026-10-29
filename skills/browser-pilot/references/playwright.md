# The playwright-chromium-browser MCP server

Use this browser only in sessions without a built-in browser, as SKILL.md describes. It is a separate Chromium with its own profile, isolated from the user's own Chrome.

- Use only tools exposed by the MCP server named `playwright-chromium-browser`. Clients may normalize hyphens to underscores in tool names; identify the server from the available tool metadata. Never substitute another Playwright server.
- It runs Playwright's Chromium build (Chrome for Testing), never the user's own Chrome, and keeps sign-ins in one persistent profile at `~/.playwright-chromium-browser/profile`, so they survive restarts. The profile holds login cookies: never read, copy, commit, or upload its files.
- If its tools are missing, tell the user to run `bash setup-agent-skills.sh claude` or `bash setup-agent-skills.sh codex` from their `ksp-setup` checkout, then restart the session. The helper registers the server from `~/.ksp/skills/playwright-chromium-browser/.mcp.json` in that tool's user configuration. Stop until it is available; do not fall back to another browser.

## One shared browser

Every session attaches to the same long-running Chromium on `127.0.0.1:19222` instead of starting its own. It opens on the first browser action and keeps running after sessions end, until the user quits it.

- The tab list also shows tabs that the user and other sessions opened. Work only in the tabs you opened, and leave the others alone.
- Start every task with the tabs tool's `new` action and the page address. A navigate as your first action reuses whichever tab is current, which can belong to the user or another session.
- Never close tabs or the browser; the user closes them. In Claude Code, `browser_close` is denied and the tabs tool refuses `action: close`.
- In Claude Code, a hook opens the browser before each browser action when it is not running. Elsewhere, if a browser tool fails with `ECONNREFUSED 127.0.0.1:19222`, run `bash ~/.ksp/skills/playwright-chromium-browser/browser.sh start`, then retry.
- If opening reports that Chrome for Testing is not installed, which happens once on a new computer, run `npx -y @playwright/mcp@latest install-browser chrome-for-testing`, tell the user it is a one-time download of about 100 MB, and retry the action.
- If opening reports that another browser is using the profile, tell the user to quit that browser with Cmd+Q, then retry. Never work around it with `--isolated`, another profile, or another browser.

## Output files

The server saves snapshots, console logs, and screenshots automatically in `~/.playwright-chromium-browser/output`. They are temporary browser artifacts that may contain page content, including filled-in forms; treat them as private, never commit or upload them, and never copy them into a calling skill's records.
