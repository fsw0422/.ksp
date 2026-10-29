---
name: purge-all-sessions
description: >-
  Permanently delete dead conversations and their files for the platform
  currently running the skill: Claude sessions when invoked from Claude, or
  Codex chats when invoked from Codex. Also clears Playwright plugin output.
  Use when the user asks to purge, wipe, clean up, or delete old, archived, or
  hidden sessions, conversations, agents, or chats. Never touches the other
  platform or live sessions. Irreversible.
---

# Purge all sessions

Deletes dead sessions for good on the current platform only. `scripts/purge.py`
(in this skill's base directory) plans and applies; you decide what is live and
confirm with the user. Run it with `python3 -I`.

At the start, identify the host from the current agent environment:

- In Claude Code or Claude Desktop, use `--platform claude` and never inspect,
  plan, or delete Codex data.
- In Codex, use `--platform codex` and never inspect, plan, or delete Claude
  data.

Never run both platforms during one invocation. Do not ask the user to choose
when the host is already known.

## Live means keep

For Claude, the user decides what to keep. Never guess from `ListAgents` alone:
it lists only sessions with a running process, and the daemon retires idle
finished ones (see `~/.claude/daemon.log`, "retire ... idle 61m") while their
dashboard rows and job folders remain. Deleting from that list once destroyed
three rows the user still had.

- **Claude:** keep what the user picks. Also always kept: this session, running
  processes, anything touched in the last 10 minutes, and any session id that
  Claude Desktop's Code sidebar storage mentions.
- **Codex:** anything not archived. Only `archived = 1` threads are purged.

## Steps

1. **Select the current platform.** Use `claude` in Claude and `codex` in Codex.
   Never include the other platform.
2. **Claude only - list candidates and ask what to keep.** Run `purge.py jobs`
   (job id, session id, name, state, last change) and call `ListAgents`. Show one
   numbered list of every Claude session, marking which are running now. Ask the
   user which numbers to keep. Do not proceed on silence or decide for them.
3. **Plan (no deletion):**
   - Claude: `python3 -I purge.py plan --platform claude --live <id> --live <id> ...`
   - Codex: `python3 -I purge.py plan --platform codex`

   Pass every kept session id (full id or unique prefix). Add
   `--playwright-profile` only if the user wants browser logins wiped too, since
   it signs them out of every site. Claude plans refuse to run without `--live`;
   Codex plans do not accept it.
4. **Confirm the delete list.** Show the summary: counts, MB, the kept sessions,
   and the names of every job folder that will be deleted. Ask once more, and
   wait for yes. Deletion is irreversible. In Codex only, if the Codex app is
   running, tell the user to quit it first, or its database cleanup can fail
   with "locked".
5. **Apply:** `python3 -I purge.py apply --manifest <path printed by plan>`.
   Re-run `plan` first if the manifest is over an hour old.
6. **Check and report:** run `plan` again for the same platform and confirm it
   finds nothing new, then tell the user what was deleted and what was kept.
   In Codex, note any database the script could not open and offer to retry
   after Codex is closed.

## What gets deleted

| Selected platform | Per purged session |
|---|---|
| Claude | `projects/*/<id>*` (transcript, subagents, tool results), `jobs/<job>`, `file-history/<id>`, `session-env/<id>`, `tasks/<id>`, `debug/<id>*`, dead `sessions/*.json`, matching lines in `history.jsonl` |
| Codex | rollout files in `sessions/` and `archived_sessions/`, `shell_snapshots`, `generated_images`, `attachments`, `session_index.jsonl` and `history.jsonl` lines, rows in every `*.sqlite` table with a thread/session id column (`threads`, logs, goals, history, queue, ...) |
| Playwright | `~/.playwright-chromium-browser/output/*` older than 10 minutes. The profile only with the flag, and only when the browser window is closed. |

Only the selected platform row and the shared Playwright row apply to one run.

Not touched: `plans/`, `paste-cache/`, `shell-snapshots/` for Claude (not keyed by
session), settings, skills, auth.

## Rules learned the hard way

- Never build a path by splitting on `.` - `~/.claude` has a dot in it. Strip
  suffixes only, and never run a recursive delete on a path you did not verify
  sits inside `~/.claude`, `~/.codex`, or `~/.playwright-chromium-browser`.
- `ListAgents` is not the dashboard. Ask the user which sessions to keep.
- Dry-run first, always.
