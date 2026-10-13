---
name: restore-session
description: Bring back a Claude Code conversation that is missing from the `claude agents` dashboard (its row was deleted, or `/resume` inside another row swapped it away), starting from a vague description such as "the desktop one in ~/projects". Finds matching past conversations, lets the user pick one, then restores it as a background row with its old session id. Use when the user asks to restore, unhide, recover, reopen, or bring back a session, conversation, chat, or agent row. Claude Code only.
---

# Restore session

Bring a past conversation back as a row in `claude agents`. The script does the
searching, the safety checks, and the launch. You choose the search words, show
the options, and act on the answer.

The script is `scripts/restore-session.py` in this skill's base directory. Run
it with `python3 <base directory>/scripts/restore-session.py`. It prints JSON.

## 1. Find candidates

Turn the user's words into 1-4 distinctive keywords: topic words, ticket keys,
repository, tool, or people names. Add an obvious synonym when it helps. Leave
out filler such as "conversation", "session", or "restore". When the user names
a folder, pass it with `--cwd`.

```sh
python3 <base directory>/scripts/restore-session.py find desktop chromium --cwd ~/projects
```

`results` are ranked by match. Each has `id`, `title`, `folder`,
`last_active_ago`, `first_prompt`, `last_prompt`, `summary`, `status`, and
`matched` (where each word was found). Conversations that already have a row
are left out and counted in `skipped_listed`; add `--include-listed` to see
them. The conversation running this skill is always left out.

- No results: retry with fewer or broader words, then without `--cwd`, then
  with no words (newest first). Still nothing: say so and ask for another
  detail, such as roughly when it happened or what it was about.
- A match found only a few times in the text is weak. Say so instead of
  presenting it as a sure match.

## 2. Let the user pick

Always ask, even when one match is clearly best. Use AskUserQuestion with the
best 2-4 results:

- label: the title, shortened to a few words
- description: `<folder> · <last_active_ago> · "<first prompt, shortened>"`,
  plus a short note when `status` is not `hidden` (see the table below)

Several conversations can share a title, for example after `/resume` moved a
row to another conversation. When titles match, label each option by its topic
(from `first_prompt` or `summary`) instead of the shared title.

A result with `name_in_use_by` has a title that row `name_in_use_by` already
uses as its name. Restoring it needs a new name (see `name_in_use` below).

With a single result, add "None of these" as the second option. When the user
picks "None of these" or types something else, search again with their words.
If AskUserQuestion is not available, show a numbered list and wait for the
choice.

## 3. Restore the chosen conversation

```sh
python3 <base directory>/scripts/restore-session.py restore <id> [--name "<name>"]
```

The script checks the status again. For a `hidden` conversation it runs
`claude --bg --resume <id> --permission-mode auto --agent <agent> --name <name>`
from the conversation's original folder and waits for the row to appear.
`<name>` is `--name`, or else the conversation's title. The script refuses a
name that another row already uses.

| Exit, `status` | Meaning | What to do |
|---|---|---|
| 0, `ok: true` | The row is back. | Report `row`, `name`, and `attach` (`claude attach <row>`). If `copy` is true, say it came back as a copy with a new id. |
| 4, `name_in_use` | Row `row` is already named `name`. The title is usually an old row name that `/resume` left on the conversation. | Suggest a short name for the conversation's topic (from `summary` or `first_prompt`) and ask the user to accept it or type their own. Then run `restore <id> --name "<name>"`, keeping any flag such as `--allow-copy`. |
| 3, `listed` | It already has a row. | Tell the user the `row` and `row_name`. |
| 4, `swapped` | It is open inside row `row` because `/resume` switched that row to it. | Ask before restarting that row. On yes, run `claude respawn <row>`, then run `restore` again. |
| 4, `replaced` | Row `row` is saved as this conversation, but `/resume` switched it to another one. | Ask before restarting that row. On yes, run `claude respawn <row>`. That alone brings it back. |
| 4, `switched_away` | Row `row` started as this conversation and later moved to another one. | Explain it can only come back as a copy with a new id. On yes, run `restore <id> --allow-copy`. |
| 4, `open_in_terminal` | It is open in a terminal session. | Ask the user to exit that session, then run `restore` again. |
| 2, `not_found` | Unknown or ambiguous id. | Search again. |
| 1, `error` | The launch or the dashboard check failed. | Show `message`. Do not retry with other tools. |

`claude respawn <row>` restarts that row from its saved state. Its conversation
is kept; only the running process restarts.

A row's name belongs to the row, not to its conversation. `/resume` swaps the
conversation and keeps the old name, so a name can stop matching what the row
shows. When that happens, tell the user to select the row in `claude agents`
and press Ctrl+R to rename it. The new name sticks when the row restarts.

Add `--permission-mode <mode>` to restore in a different mode, or `--dry-run`
to see the checks and the command without launching anything.

## Rules

- Never edit files under `~/.claude/jobs`, `~/.claude/sessions`, or
  `~/.claude/projects` by hand.
- Never run `/resume` inside an existing row to restore a conversation. It
  replaces that row's conversation.
- Never restart, stop, or delete another row without the user's yes.

## Why the built-in ways do not work here

- Typing `/resume` in the `claude agents` dashboard opens a picker of past
  sessions only when the dashboard was started without options such as
  `--permission-mode`, `--model`, `--agent`, `--effort`, `--add-dir`, or
  `--plugin-dir`.
- When settings cannot make auto mode the default (for example, a managed
  policy sets `permissions.defaultMode`), auto mode needs
  `claude agents --permission-mode auto`, and that flag turns the picker off.
- `/resume` inside a row switches that row to the chosen conversation and
  hides the row's own conversation.
