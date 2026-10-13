---
name: purge-all-sessions
description: Permanently delete dead Claude Code and Codex conversations plus the files tied to them. Claude - every session not on the `claude agents` dashboard or in Claude Desktop's Code sidebar (transcripts, job rows, file-history, session-env, tasks, debug, history). Codex - every archived chat and its rollouts, snapshots, images, DB rows. Also clears Playwright plugin output. Use when the user asks to purge, wipe, clean up, or delete old/archived/hidden sessions, conversations, agents, or chats. Never touches live ones. Irreversible.
---

# Purge all sessions

Deletes dead sessions for good. `scripts/purge.py` (in this skill's base
directory) plans and applies; you decide what is live and confirm with the user.
Run it with `python3 -I`.

## Live means keep

- **Claude:** the row is on the `claude agents` dashboard, or the session shows in
  Claude Desktop's Claude Code sidebar, or its process is running, or it was
  touched in the last 10 minutes. This session is always kept.
- **Codex:** anything not archived. Only `archived = 1` threads are purged.

## Steps

1. **Find the dashboard rows.** Call `ListAgents`. Run `purge.py jobs` (job id,
   session id, name, state). Match each dashboard row to a session id by name.
   A job folder with no dashboard row is dead, even if it still has a folder.
   If a name is unclear or duplicated, keep it (add it as live) and say so.
2. **Plan (no deletion):**
   `python3 -I purge.py plan --live <id> --live <id> ...`
   Use the full session id from step 1 (or a unique prefix). Add
   `--playwright-profile` only if the user wants browser logins wiped too, since
   it signs them out of every site. The plan refuses to run without `--live`.
3. **Show the summary** (counts, MB, the kept sessions and why). Ask once before
   deleting, unless the user already said to go ahead without asking. Deletion is
   irreversible. If Codex is running, tell the user to quit it first, or the DB
   cleanup can fail with "locked".
4. **Apply:** `python3 -I purge.py apply --manifest <path printed by plan>`.
   Re-run `plan` first if the manifest is over an hour old.
5. **Check and report:** run `plan` again and confirm it finds nothing new, then
   tell the user what was deleted and what was kept.

## What gets deleted

| Area | Per purged session |
|---|---|
| Claude | `projects/*/<id>*` (transcript, subagents, tool results), `jobs/<job>`, `file-history/<id>`, `session-env/<id>`, `tasks/<id>`, `debug/<id>*`, dead `sessions/*.json`, matching lines in `history.jsonl` |
| Codex | rollout files in `sessions/` and `archived_sessions/`, `shell_snapshots`, `generated_images`, `attachments`, `session_index.jsonl` and `history.jsonl` lines, rows in every `*.sqlite` table with a thread/session id column (`threads`, logs, goals, history, queue, ...) |
| Playwright | `~/.playwright-chromium-browser/output/*` (profile only with the flag). Skipped if the browser is running. |

Not touched: `plans/`, `paste-cache/`, `shell-snapshots/` for Claude (not keyed by
session), settings, skills, auth.

## Rules learned the hard way

- Never build a path by splitting on `.` - `~/.claude` has a dot in it. Strip
  suffixes only, and never run a recursive delete on a path you did not verify
  sits inside `~/.claude`, `~/.codex`, or `~/.playwright-chromium-browser`.
- The jobs folder can lag the dashboard in both directions. Trust `ListAgents`.
- Dry-run first, always.
