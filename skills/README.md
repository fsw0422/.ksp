# Agent skills

Personal agent skills maintained under `skills/` in the `.ksp` dotfiles
repository. Clone `.ksp` to `~/.ksp` and link these folders into Claude Code and
Codex. Both tools read the same files, independent of which tool was installed
first. This directory also owns their shared user-level instructions and the
Playwright Chromium MCP configuration for CLI browsing; setup links or
registers both for each selected tool.

## Install

For a new machine, use [ksp-setup](https://github.com/fsw0422/ksp-setup) and choose
`claude`, `codex`, or `both` when `install.sh` asks which AI tool configs to
install. It clones this repository to `~/.ksp`, links the shared settings, and
creates instruction and skill links for the selected tools:

- Claude Code instructions: `~/.claude/CLAUDE.md` → `~/.ksp/skills/AGENTS.md`
- Codex instructions: `~/.codex/AGENTS.md` → `~/.ksp/skills/AGENTS.md`
- Claude Code: `~/.claude/skills/<name>`
- Codex: `~/.agents/skills/<name>`

To rerun just this setup from your `ksp-setup` checkout:

```sh
bash setup-agent-skills.sh both
```

Setup verifies which AI tools are installed through their CLI or desktop app
before creating links. Use `claude` or `codex` instead of `both` to restrict the
requested targets; unavailable targets are skipped. With no argument, setup
detects every installed platform. `link-only` also detects installed platforms
but does not fetch or change MCP registrations.

The helper links `AGENTS.md`, discovers every top-level `<name>/SKILL.md`,
creates or updates its links, removes stale links that point back into this
checkout, and migrates links made by earlier setups. Unrelated files and links
are preserved. Full setup also needs `jq` and the selected tool's CLI for MCP
registration; desktop-only installs still receive instruction and skill links.
The browser server needs Node.js and `npx`.

The old `skills@fsw0422` and `playwright-chromium-browser@fsw0422` Claude plugins
are disabled to prevent duplicate skills and servers. The shared `.ksp` settings
also keep them disabled and no longer declare the fsw0422 marketplace. If you
installed these plugins in Codex, disable those copies as well. Restart the tools after
changing skill sources. `restore-session` restores Claude Code conversations,
even when invoked from Codex.

### Browsers

browser-pilot governs every browser task, and the global instructions tell both tools to load it before any browser tool. The Claude Code Desktop and Codex apps use only their built-in browser. Sessions without one, such as a CLI, use the directly registered `playwright-chromium-browser` MCP server. Your own Chrome is never used: the Claude Code user settings deny Claude in Chrome (`mcp__claude-in-chrome`), and the Codex config turns off the bundled Chrome plugin with `enabled = false` under `[plugins."chrome@openai-bundled"]`.

Setup reads `playwright-chromium-browser/.mcp.json`, resolves `${HOME}`, and saves
the server through `claude mcp add-json --scope user` and/or `codex mcp add`.
It preserves Playwright's Chromium (Chrome for Testing), isolated from your own
Chrome, with a persistent profile at `~/.playwright-chromium-browser/profile` and
output in `~/.playwright-chromium-browser/output`. Never commit either folder;
they hold login cookies and page contents. No marketplace install is needed.

The server starts through `playwright-chromium-browser/launch.sh`. Inside a
Claude Code session it loads `session-tabs.cjs`, which keeps that session's open
tabs in `~/.playwright-chromium-browser/sessions/<session-id>/tabs.json` and
reopens them when the browser starts again, so each session has its own tabs
while every session shares the one signed-in profile. Only one session can hold
the browser at a time; quit it with Cmd+Q to hand it to another session. Set
`PW_SESSION_RESTORE=0` in the server environment to record tabs without
reopening them. Codex sessions use the shared profile without tab tracking.

If the browser binary is missing on a new machine, install it once:

```sh
npx -y @playwright/mcp@latest install-browser chrome-for-testing
```

This downloads the browser (about 100 MB); repeat it if Playwright reports the
browser missing after an update. Rerun setup if the repo's MCP configuration
changes, since each tool stores a copy of those options.

## Global instructions and settings

The shared user-level instructions live here in `AGENTS.md`.
[ksp-setup](https://github.com/fsw0422/ksp-setup) links that file to
`~/.claude/CLAUDE.md` and `~/.codex/AGENTS.md`. Claude Code settings and the
Codex system config live alongside this directory in the
[.ksp](https://github.com/fsw0422/.ksp) dotfiles repo and link to
`~/.claude/settings.json` and
`/etc/codex/config.toml`.

## Update

Update the `.ksp` checkout with:

```sh
git -C ~/.ksp pull --ff-only
```

Rerun the setup helper after adding or removing a skill directory or changing
the browser MCP configuration. Existing instruction and skill file edits are
visible through their links immediately after the pull.

No plugin version bump is needed. The `.ksp` checkout has no automatic update
trigger; opening Claude or Codex does not pull it. Instructions, skills, and
browser configuration come from this checkout rather than marketplace updates.

## Add a skill

Create `<name>/SKILL.md` in this directory. After pulling the change, rerun
`bash setup-agent-skills.sh both` from `ksp-setup` to create the new links, then
restart the tools. Existing skill edits need no new links; rerunning setup
removes links for deleted skills. Optional Codex UI metadata goes in
`<name>/agents/openai.yaml`.
