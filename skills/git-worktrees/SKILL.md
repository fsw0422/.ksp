---
name: git-worktrees
description: Create and remove git worktrees with one script. It puts each worktree beside the repository's main checkout as `<repo folder>-<branch>`, copies the `.env`, and keeps VS Code's `.code-workspace` file in step. Use it whenever you create or remove a git worktree, in any repository and from any skill, such as Spec Workflow, instead of Claude Code's own worktree features (`EnterWorktree` with a name, a subagent's `isolation: worktree`, `use_worktree`, or `claude --worktree`).
---

# Git Worktrees

Create and remove git worktrees with this skill's script. Each worktree goes beside the repository's main checkout, never inside a repository.

**Why:** the folder name shows the repository and branch at a glance, paths stay short, and no checkout sits inside another one. Claude Code's automatic cleanup never removes these folders. The copied `.env` lets the worktree run, and the workspace file shows every worktree in one VS Code window.

## Create a worktree

```bash
python3 <this skill's folder>/scripts/worktree.py add <repo> <branch> [--from <start>] [--env-from <folder>]
```

- `<repo>`: any checkout of the repository, usually its main checkout.
- `<branch>`: an existing branch is checked out as it is. A branch that exists only on the remote gets a local branch that tracks it. Any other name becomes a new branch from `--from`, or from `<repo>`'s current commit.
- `--env-from`: the checkout to copy the `.env` from. By default, it's the checkout where `--from` is checked out, or else `<repo>`.

For example, run from the ichbinkalt workspace (made up):

```bash
python3 <this skill's folder>/scripts/worktree.py add ichbinkalt-backend 001-initial-pause-limit --from 001-initial
```

```text
Created /Users/kev/projects/ichbinkalt/ichbinkalt-backend-001-initial-pause-limit on new branch 001-initial-pause-limit from 001-initial
.env: copied from /Users/kev/projects/ichbinkalt/ichbinkalt-backend-001-initial
ichbinkalt.code-workspace: added
```

The script does three things:

1. **Names the folder** `<repo folder>-<branch>`, beside the main checkout, with any `/` in the branch name as `-`. For example, branch `fix/login` of `~/code/app` goes in `~/code/app-fix-login`.
2. **Copies the `.env`** when the source has one and the worktree doesn't, with the same permissions. It never prints the file. If Git doesn't ignore `.env`, it adds a local exclusion, so the file can't be committed.
3. **Updates the workspace file.** Each `.code-workspace` file beside the main checkout that lists the main checkout gets the new folder, with a relative path, in sorted place. With no such file, it does nothing. It never creates one.

To work in the new worktree in Claude Code, call `EnterWorktree` with its `path`. Claude Code asks the user first, because the folder is outside `.claude/worktrees/`.

## Remove a worktree

```bash
python3 <this skill's folder>/scripts/worktree.py remove <worktree>
```

It runs `git worktree remove`, which refuses a worktree with uncommitted changes, untracked files, or a lock. Then it removes the folder's entry from the same workspace files. The branch stays: delete it yourself once its work is merged or saved.

## Don't use Claude Code's own worktree features

`EnterWorktree` with a `name`, a subagent's `isolation: worktree`, `use_worktree` for a new session, and `claude --worktree` all put the worktree in `.claude/worktrees/`, inside the repository. Create it with this script instead, then enter it with `EnterWorktree` and its `path`.

## If it fails

| The script says | What to do |
| --- | --- |
| `... already exists.` | Use that worktree if it's on the branch you want. Otherwise, ask the user. |
| `git:` and the branch is already used by another worktree | Work in that worktree instead. |
| `git:` and the worktree contains modified or untracked files | Commit or save the work first. Never force the removal. |
| `... so update it by hand` | The worktree step worked. Edit that workspace file yourself: add or remove the folder's entry, keep the entries sorted, and keep its comments. |
| `... does not exist.` | The worktree was removed by hand. Run `git worktree prune` in the main checkout, and remove its workspace entry yourself. |

## How it works

- `scripts/worktree.py` runs the steps. `checkouts.py` wraps git, `env_copy.py` copies the `.env`, and `workspace.py` edits the workspace files.
- It needs only Python 3 and git. It reads workspace files with Python's built-in `json`, which can't keep comments, so it leaves a file that has comments for a manual edit instead of rewriting it without them.
- Tests: `python3 -m unittest discover -s <this skill's folder>/tests`. They run on throwaway repositories.
