---
name: purge-all-sessions
description: >-
  Permanently delete dead conversations and their files for the platform
  currently running the skill: Claude sessions when invoked from Claude, or
  Codex chats when invoked from Codex. For Claude, only sessions that no longer
  show in the `claude agents` dashboard are purged. Also clears Playwright
  plugin output. Use when the user asks to purge, wipe, clean up, or delete
  old, archived, or hidden sessions, conversations, agents, or chats. Never
  touches the other platform or live sessions. Irreversible.
---

# Purge all sessions

Deletes dead sessions for good on the current platform only. `scripts/purge.py`
(in this skill's base directory) plans and applies. You show the plan and
confirm with the user. Run it with `python3 -I`.

At the start, identify the host from the current agent environment:

- In Claude Code (CLI, `claude agents` rows, IDE) or Claude Desktop, use
  `--platform claude` and never inspect, plan, or delete Codex data.
- In Codex, use `--platform codex` and never inspect, plan, or delete Claude
  data.

Never run both platforms during one invocation. Do not ask the user to choose
when the host is already known.

## Live means keep

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

## Purged means not restorable

Hidden Claude sessions are exactly what `/claude-restore-session` brings back. Once
purged, their transcripts are gone and `/claude-restore-session` cannot find them.
Always say this in the confirm step. Offer `--older-than <days>` when the user
wants recently hidden sessions to stay restorable for a while.

## Steps

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

## What gets deleted

| Selected platform | Per purged session |
|---|---|
| Claude | `projects/*/<id>*` (transcript, subagents, tool results), `file-history/<id>`, `session-env/<id>`, `tasks/<id>`, `debug/<id>*`, dead `sessions/*.json`, matching lines in `history.jsonl`. `jobs/<job>` only with `--also-purge`. |
| Codex | rollout files in `sessions/` and `archived_sessions/`, `shell_snapshots`, `generated_images`, `attachments`, `session_index.jsonl` and `history.jsonl` lines, rows in every `*.sqlite` table with a thread/session id column (`threads`, logs, goals, history, queue, ...) |
| Playwright | `~/.playwright-chromium-browser/output/*` older than 10 minutes. The profile only with the flag, and only when the browser window is closed. |

Only the selected platform row and the shared Playwright row apply to one run.

Not touched: `plans/`, `paste-cache/`, `shell-snapshots/` for Claude (not keyed by
session), settings, skills, auth.

## Rules learned the hard way

- Never build a path by splitting on `.` - `~/.claude` has a dot in it. Strip
  suffixes only, and never run a recursive delete on a path you did not verify
  sits inside `~/.claude`, `~/.codex`, or `~/.playwright-chromium-browser`.
- `ListAgents` is not the dashboard. `~/.claude/jobs/` is.
- Dry-run first, always.
