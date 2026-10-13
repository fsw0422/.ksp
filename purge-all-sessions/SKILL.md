---
name: purge-all-sessions
description: Permanently delete dead Claude Code and Codex conversations plus the files tied to them. Claude - every session not on the `claude agents` dashboard or in Claude Desktop's Code sidebar (transcripts, job rows, file-history, session-env, tasks, debug, history). Codex - every archived chat and its rollouts, snapshots, images, DB rows. Also clears Playwright plugin output. Use when the user asks to purge, wipe, clean up, or delete old/archived/hidden sessions, conversations, agents, or chats. Never touches live ones. Irreversible.
---

# Purge all sessions

Deletes dead sessions for good. `scripts/purge.py` (in this skill's base
directory) plans and applies; you decide what is live and confirm with the user.
Run it with `python3 -I`.

## Live means keep

The user decides what to keep. Never guess from `ListAgents` alone: it lists only
sessions with a running process, and the daemon retires idle finished ones
(see `~/.claude/daemon.log`, "retire ... idle 61m") while their dashboard rows
and job folders remain. Deleting from that list once destroyed three rows the
user still had.

- **Claude:** keep what the user picks. Also always kept: this session, running
  processes, anything touched in the last 10 minutes, and any session id that
  Claude Desktop's Code sidebar storage mentions.
- **Codex:** anything not archived. Only `archived = 1` threads are purged.

## Steps

1. **List candidates.** Run `purge.py jobs` (job id, session id, name, state, last
   change) and call `ListAgents`. Show the user one numbered list of every
   Claude session, marking which are running now. Group them as: running,
   finished/retired.
2. **Ask which to keep.** Ask the user to reply with the numbers to keep (or "all
   finished" / "none"). Everything not picked will be deleted. Do not proceed
   on silence, and do not decide for them.
3. **Plan (no deletion):**
   `python3 -I purge.py plan --live <id> --live <id> ...`
   Pass every kept session id (full id or unique prefix). Add
   `--playwright-profile` only if the user wants browser logins wiped too, since
   it signs them out of every site. The plan refuses to run without `--live`.
4. **Confirm the delete list.** Show the summary: counts, MB, the kept sessions,
   and the names of every job folder that will be deleted. Ask once more, and
   wait for yes. Deletion is irreversible. If the Codex app is running, tell the
   user to quit it first, or its database cleanup can fail with "locked".
5. **Apply:** `python3 -I purge.py apply --manifest <path printed by plan>`.
   Re-run `plan` first if the manifest is over an hour old.
6. **Check and report:** run `plan` again and confirm it finds nothing new, then
   tell the user what was deleted and what was kept. Note any database the
   script could not open and offer to retry after Codex is closed.

## What gets deleted

| Area | Per purged session |
|---|---|
| Claude | `projects/*/<id>*` (transcript, subagents, tool results), `jobs/<job>`, `file-history/<id>`, `session-env/<id>`, `tasks/<id>`, `debug/<id>*`, dead `sessions/*.json`, matching lines in `history.jsonl` |
| Codex | rollout files in `sessions/` and `archived_sessions/`, `shell_snapshots`, `generated_images`, `attachments`, `session_index.jsonl` and `history.jsonl` lines, rows in every `*.sqlite` table with a thread/session id column (`threads`, logs, goals, history, queue, ...) |
| Playwright | `~/.playwright-chromium-browser/output/*` older than 10 minutes. The profile only with the flag, and only when the browser window is closed. |

Not touched: `plans/`, `paste-cache/`, `shell-snapshots/` for Claude (not keyed by
session), settings, skills, auth.

## Rules learned the hard way

- Never build a path by splitting on `.` - `~/.claude` has a dot in it. Strip
  suffixes only, and never run a recursive delete on a path you did not verify
  sits inside `~/.claude`, `~/.codex`, or `~/.playwright-chromium-browser`.
- `ListAgents` is not the dashboard. Ask the user which sessions to keep.
- Dry-run first, always.
