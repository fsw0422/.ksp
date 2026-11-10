---
name: purge-all-sessions
description: >-
  Permanently delete AI session data. By default, purge dead conversations and
  their files for the platform currently running the skill: Claude sessions
  when invoked from Claude, or Codex chats when invoked from Codex. For Claude,
  only sessions that no longer show in the `claude agents` dashboard are
  purged. Also clears Playwright plugin output. On request, prepare a full
  wipe of all Claude Code and Codex session data, which the user then runs
  from a terminal with both tools quit. Use when the user asks to purge, wipe,
  clean up, or delete old, archived, or hidden sessions, conversations,
  agents, or chats, or to wipe all session data and start fresh. The default
  purge never touches the other platform or live sessions. Irreversible.
---

# Purge all sessions

Deletes session data for good, in one of two modes:

| The user wants | Mode | Script |
|---|---|---|
| Old, hidden, or archived sessions gone | [Purge dead sessions](#purge-dead-sessions) | `scripts/purge.py` |
| Everything gone, to start fresh | [Wipe everything](#wipe-everything) | `scripts/wipe.py` |

Both scripts are in this skill's base directory. Run them with `python3 -I`.
When the request doesn't say which mode, purge dead sessions: it keeps every
live conversation, and a wipe keeps none.

## Purge dead sessions

Deletes dead sessions on the current platform only. `purge.py` plans and
applies. You show the plan and confirm with the user.

At the start, identify the host from the current agent environment:

- In Claude Code (CLI, `claude agents` rows, IDE) or Claude Desktop, use
  `--platform claude` and never inspect, plan, or delete Codex data.
- In Codex, use `--platform codex` and never inspect, plan, or delete Claude
  data.

Never run both platforms during one invocation. Do not ask the user to choose
when the host is already known.

### Live means keep

- **Claude:** every session with a dashboard row is kept automatically. Each
  row in `claude agents` has a `~/.claude/jobs/<job>/` folder, and the script
  reads them. Also always kept: this session, running processes, anything
  touched in the last 10 minutes, and any session id that Claude Desktop's Code
  sidebar storage mentions. Only hidden sessions are purged: rows deleted from
  the dashboard, sessions swapped away by `/resume`, and finished plain
  terminal `claude` sessions that never had a row.
- **Codex:** anything not archived. Only `archived = 1` threads are purged.

Do not judge "on the dashboard" from `ListAgents`. It lists only sessions with
a running process, and the daemon retires idle finished ones (see
`~/.claude/daemon.log`, "retire ... idle 61m") while their rows and job
folders remain.

### Purged means not restorable

Hidden Claude sessions are exactly what `/claude-restore-session` brings back. Once
purged, their transcripts are gone and `/claude-restore-session` cannot find them.
Always say this in the confirm step. Offer `--older-than <days>` when the user
wants recently hidden sessions to stay restorable for a while.

### Steps

1. **Select the current platform.** Use `claude` in Claude and `codex` in Codex.
   Never include the other platform.
2. **Plan (no deletion):**
   - Claude: `python3 -I purge.py plan --platform claude [--older-than <days>]`
   - Codex: `python3 -I purge.py plan --platform codex`

   Claude-only options:
   - `--older-than <days>`: only purge hidden sessions idle for more than that
     many days. Newer ones stay restorable.
   - `--also-purge <id>`: also purge a dashboard row, only when the user names
     it. It removes the row's job folder too. It cannot override this session,
     running processes, or the 10-minute guard.
   - `--live <id>`: keep an extra hidden session the user wants to keep.

   Add `--playwright-profile` only if the user wants browser logins wiped too,
   since it signs them out of every site.
3. **Confirm the delete list.** Show the counts, MB, the kept dashboard rows,
   and the hidden sessions to purge (the plan prints the id, last activity,
   folder, and first prompt for each). Name any job folder that will be
   deleted (only with `--also-purge`). For Claude, say the purged sessions can
   no longer be restored with `/claude-restore-session`. Ask once, and wait for yes.
   In Codex only, if the Codex app is running, tell the user to quit it first,
   or its database cleanup can fail with "locked".
4. **Apply:** `python3 -I purge.py apply --manifest <path printed by plan>`.
   Re-run `plan` first if the manifest is over an hour old.
5. **Check and report:** run `plan` again with the same options and confirm it
   finds nothing new, then tell the user what was deleted and what was kept.
   In Codex, note any database the script could not open and offer to retry
   after Codex is closed.

### What gets deleted

| Selected platform | Per purged session |
|---|---|
| Claude | `projects/*/<id>*` (transcript, subagents, tool results), `file-history/<id>`, `session-env/<id>`, `tasks/<id>`, `debug/<id>*`, dead `sessions/*.json`, matching lines in `history.jsonl`. `jobs/<job>` only with `--also-purge`. |
| Codex | rollout files in `sessions/` and `archived_sessions/`, `shell_snapshots`, `generated_images`, `attachments`, `session_index.jsonl` and `history.jsonl` lines, rows in every `*.sqlite` table with a thread/session id column (`threads`, logs, goals, history, queue, ...) |
| Playwright | `~/.playwright-chromium-browser/output/*` older than 10 minutes. The profile only with the flag, and only when the browser window is closed. |

Only the selected platform row and the shared Playwright row apply to one run.

Not touched: `plans/`, `paste-cache/`, `shell-snapshots/` for Claude (not keyed by
session), settings, skills, auth.

## Wipe everything

`wipe.py` deletes all session data of Claude Code and Codex, and keeps the
setup. Without `--yes` it is a dry run.

```bash
python3 -I wipe.py [--yes] [--claude-only | --codex-only]
```

**You run only the dry run. The user runs the delete.** With `--yes` the script
refuses to start while Claude Code, the Claude desktop app, or Codex is
running, because an open session would corrupt its SQLite databases or simply
write the files back. That includes the session you are in, so the delete can
only happen from a plain terminal once the tools have quit.

1. **Dry run:** `python3 -I wipe.py`. It covers both tools, which is the one
   time this skill looks at the other platform. Add `--claude-only` or
   `--codex-only` when the user wants one tool.
2. **Show the list** with its sizes and the total, and say what it means:
   every conversation goes, this one included, and none can be brought back,
   from the Trash or with `/claude-restore-session`. Settings, logins, skills,
   plugins, and memory stay.
3. **Hand over the command.** The user quits everything the dry run listed as
   still running, then runs the script in a terminal with `--yes`, and with
   the same `--claude-only` or `--codex-only` as the dry run. Give its full
   path, so it works from any folder:

   ```bash
   python3 -I ~/.ksp/skills/purge-all-sessions/scripts/wipe.py --yes
   ```

Never pass `--yes` yourself, even for the other platform while it is closed.
A wipe is something the user starts by hand, with everything quit.

### What a wipe deletes

| Tool | Deleted | Kept |
|---|---|---|
| Claude | Transcripts, subagent and tool outputs in `~/.claude/projects/*/`. Prompt history, plans, todos, file history, caches, and logs in `~/.claude/`. The desktop app's `claude-code-sessions` and `local-agent-mode-sessions`. Last-session keys in `~/.claude.json`. | Settings, logins, skills, plugins, each project's `memory/` |
| Codex | Sessions, history files, state and log databases, caches, and logs. Thread folders in `~/Documents/Codex/` and their trust entries in `~/.codex/config.toml`. | Settings, logins, `memories_*.sqlite` |

The dry run lists every folder, and the lists at the top of `wipe.py` are the
full set. Before the script edits `~/.claude.json` or `~/.codex/config.toml`,
it copies them to a folder in the temp directory and prints the path.

Tests: `python3 -m unittest discover -s <this skill's folder>/tests`. They run
on a throwaway home folder.

## Rules learned the hard way

- Never build a path by splitting on `.` - `~/.claude` has a dot in it. Strip
  suffixes only, and never run a recursive delete on a path you did not verify
  sits inside `~/.claude`, `~/.codex`, or `~/.playwright-chromium-browser`.
  A wipe reaches further, so `wipe.py` checks every path against its own
  `ROOTS` list first.
- `ListAgents` is not the dashboard. `~/.claude/jobs/` is.
- Dry-run first, always.
