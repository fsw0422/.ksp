---
name: git-worktrees
description: "Create, sync and remove git worktrees with one script. It puts each worktree beside the repository's main checkout as `<repo folder>-<branch>`, copies the `.env`, keeps VS Code's `.code-workspace` file in step, keeps every branch on its parent's head with its copy on the remote current, and deletes a merged branch here and on the remote once that loses no work and closes no open pull request. Use it whenever you create or remove a git worktree, and whenever a branch that has children gets new commits (a merge, a commit, a pull, or a rebase), in any repository and from any skill, such as Spec Workflow, instead of Claude Code's own worktree features (`EnterWorktree` with a name, a subagent's `isolation: worktree`, `use_worktree`, or `claude --worktree`)."
---

# Git Worktrees

Create, sync and remove git worktrees with this skill's script. Each worktree goes beside the repository's main checkout, never inside a repository. Each branch follows its parent, the branch it was created from: when the parent gets new commits, the branch is rebased onto them, and its copy on the remote follows. Once its work is merged, removing its worktree deletes the branch here and on the remote, after checking that this loses no work and closes no open pull request.

**Why:** the folder name shows the repository and branch at a glance, paths stay short, and no checkout sits inside another one. Claude Code's automatic cleanup never removes these folders. The copied `.env` lets the worktree run, and the workspace file shows every worktree in one VS Code window. A branch that follows its parent always builds on what's really there, so conflicts show up early, while they're small.

## Create a worktree

```bash
python3 <this skill's folder>/scripts/worktree.py add <repo> <branch> [--from <parent>] [--env-from <folder>]
```

- `<repo>`: any checkout of the repository, usually its main checkout.
- `<branch>`: an existing branch is checked out as it is. A branch that exists only on the remote gets a local branch that tracks it. Any other name is a new branch, and needs `--from`.
- `--from`: the branch the new branch builds on. The new branch starts at its head, and the script records it as the parent, so `sync` keeps the new branch on that head. A commit or a tag works too, but then no parent is recorded.
- `--env-from`: the checkout to copy the `.env` from. By default, it's the checkout where `--from` is checked out, or else `<repo>`.

For example, run from the ichbinkalt workspace (made up):

```bash
python3 <this skill's folder>/scripts/worktree.py add ichbinkalt-backend 001-initial-pause-limit --from 001-initial
```

```text
Created /Users/kev/projects/ichbinkalt/ichbinkalt-backend-001-initial-pause-limit on new branch 001-initial-pause-limit from 001-initial at 6c671b9
Parent: 001-initial, so sync keeps 001-initial-pause-limit on its head
.env: copied from /Users/kev/projects/ichbinkalt/ichbinkalt-backend-001-initial
ichbinkalt.code-workspace: added
```

If the parent is behind its own copy on the remote, as of the last fetch, the script adds a line such as `Note: 001-initial is 2 commits behind origin/001-initial, as of the last fetch. Pull it, then run sync.` It never fetches by itself.

The script does three more things:

1. **Names the folder** `<repo folder>-<branch>`, beside the main checkout, with any `/` in the branch name as `-`. For example, branch `fix/login` of `~/code/app` goes in `~/code/app-fix-login`.
2. **Copies the `.env`** when the source has one and the worktree doesn't, with the same permissions. It never prints the file. If Git doesn't ignore `.env`, it adds a local exclusion, so the file can't be committed.
3. **Updates the workspace file.** Each `.code-workspace` file beside the main checkout that lists the main checkout gets the new folder, with a relative path, in sorted place. With no such file, it does nothing. It never creates one.

To work in the new worktree in Claude Code, call `EnterWorktree` with its `path`. Claude Code asks the user first, because the folder is outside `.claude/worktrees/`.

## Keep children on their parent's head

When a branch gets new commits, every branch created from it moves onto its new head, parents first, at every depth. It doesn't matter how the commits got there: a merge, a commit made directly on the parent, a pull of someone else's work, or a rebase of the parent itself.

Git doesn't do this by itself, and nothing runs it automatically. Run `sync` in each repository where a parent moved:

- right after a merge, commit or pull on a branch that has children
- when you start work in a repository, because the user may have committed or pulled since
- before you review or merge a branch

```bash
python3 <this skill's folder>/scripts/worktree.py sync <repo>
```

For example, after three new commits on `master`, one of them pushed straight to it:

```text
/Users/kev/.ksp
master 2b27083
  personal-finance-review: rebased onto master 2b27083: 1 commit of its own, unchanged
Old tips and bases: refs/recovery/sync/2026-11-08-155619/
```

**Why at those points:** a parent can move while nobody watches, such as when the user pulls a teammate's work. Checking whenever work starts, and before anything builds on a branch, catches every move before it matters.

Each branch goes through these checks, parents first:

```mermaid
flowchart TD
    Start[Each branch with a recorded parent, parents first] --> OnHead{On its parent's head?}
    OnHead -->|Yes| Leave[Leave it]
    OnHead -->|No| Merged{Is its work already in the parent?}
    Merged -->|Yes| Removal[Leave it for removal]
    Merged -->|No| Safe{Safe to rebase now?}
    Safe -->|No| Skip[Leave it and say why]
    Safe -->|Yes| Rebase[Save the old tip, then rebase onto the parent's head]
    Rebase --> Conflict{Conflict?}
    Conflict -->|Yes| Undo[Undo the rebase and list the files]
    Conflict -->|No| Done[Rebased. Its own children come next]
```

A branch is safe to rebase when all of these hold:

- **It has its own worktree.** Sync rebases a branch only inside its own worktree, so no other checkout changes.
- **Its worktree is clean:** no uncommitted or untracked files, and no rebase or merge in progress. Someone may be halfway through an edit there.
- **Its copy on the remote has nothing new.** Sync fetches first, so it sees the latest pushes. If someone else pushed commits to the branch, a rebase followed by a force-push would erase them. Older versions of the branch's own commits, left by earlier rebases, don't count: they have the same author, date and subject as the local ones.

When a rebase conflicts, sync undoes it, so the branch is exactly as it was, and prints the files and the command to rebase by hand. The other branches still move. For example, if `001-initial-review-memory` conflicts with `001-initial`, sync reports its files, leaves it alone, and still rebases its siblings.

**Copies on the remote.** After rebasing, sync pushes each rebased branch over its copy on the remote, so the remote stays current. Every push uses `--force-with-lease`, pinned to the commit sync checked, so it can't overwrite a commit nobody here has seen. A branch rebased earlier, whose copy still holds only older versions of its commits, is pushed the same way.

```text
Copies on the remote:
  origin/001-initial-review-memory: pushed 72894cf → 0b0df1b
```

Sync never publishes a branch that has no copy on the remote yet. It also never pushes a copy that's only behind: those new local commits weren't rewritten, so you push them when you choose. A failed push leaves the local rebase in place and says why.

**Recovery.** Sync saves each rebased branch's old tip and base as `refs/recovery/sync/<time>/tip/<branch>` and `refs/recovery/sync/<time>/base/<branch>`. To undo a rebase, run `git reset --keep <old tip>` in the branch's worktree, then `git config branch.<branch>.worktreeBase <old base>`. Delete the refs once you no longer need them, with `git update-ref -d <ref>`.

### Record a parent for an existing branch

Branches created before this command, or by other tools, have no recorded parent, so sync leaves them alone. Record one with:

```bash
python3 <this skill's folder>/scripts/worktree.py parent <worktree> <parent>
```

```text
Parent of 001-initial-review-memory: 001-initial. Its own commits start after 6ace5c4.
```

Use the same command when a branch moves to a different parent. The next sync replays only its own commits onto the new parent.

## Remove a worktree

```bash
python3 <this skill's folder>/scripts/worktree.py remove <worktree> [--close-prs]
```

It first removes the folder's entry from the same workspace files and waits 3 seconds, so VS Code drops the folder while its files still exist. Then it runs `git worktree remove`, which refuses a worktree with uncommitted changes, untracked files, or a lock. If git refuses, the script puts the entry back.

**Why this order:** a language server, such as the IntelliJ one, that sees a listed folder's files vanish can keep that folder's modules in its cache. On its next start it fails on them, with errors such as `can't parse url with authority: file://$WORKSPACE_54$/src/test`.

Then it deals with the branch. When its parent already has all its work, the script deletes the branch here and its copy on the remote, after saving its tip as `refs/recovery/removed/<time>/<branch>`. It fetches first, so a branch merged on the remote, such as through a pull request, counts even before you pull its parent.

```text
ichbinkalt.code-workspace: removed
Removed /Users/kev/projects/ichbinkalt/ichbinkalt-backend-001-initial-pause-limit.
Deleted branch 001-initial-pause-limit: 001-initial has all its work. Its tip is saved as refs/recovery/removed/2026-11-08-171500/001-initial-pause-limit.
origin/001-initial-pause-limit: deleted from origin
```

It keeps the branch when it has no recorded parent, when other branches build on it, or when it has work that neither the parent nor the parent's copy on the remote has. It says so when the remote already deleted the branch's copy.

### Before it deletes a copy on the remote

Deleting a branch on the remote can lose work or close pull requests, so the script checks the copy first. If a check fails, it stops before removing anything and says why. Run `remove` again once that's fixed.

```mermaid
flowchart TD
    Start[remove a worktree] --> Merged{Does the parent have all its work?}
    Merged -->|No| Keep[Remove the worktree, keep the branch]
    Merged -->|Yes| Copy{Does the branch have a copy on the remote?}
    Copy -->|No| Local[Remove the worktree, delete the branch]
    Copy -->|Yes| Checks{Do all three checks pass?}
    Checks -->|No| Stop[Stop before removing anything, and say why]
    Checks -->|Yes| Both[Remove the worktree, delete the branch here and on the remote]
```

1. **The copy holds nothing new.** If someone else pushed commits to it, deleting it would lose them.
2. **The parent's copy on the remote has the work too.** Otherwise the work would be left only on this machine. For example, after a squash into `001-initial` that isn't pushed yet, it says `Push 001-initial, then run remove again.`
3. **No open pull request uses it.** Deleting a branch on GitHub closes the pull requests from it, as "Closed" rather than "Merged", and closes or retargets the ones into it. The script asks the `gh` CLI. For a fork, it also looks in the parent's repository, where the fork's pull requests live.

```text
Stopped before removing anything: deleting origin/001-initial-pause-limit would close the pull requests from it, and close or retarget those into it:
  #12 Add the Pause limit (from it): https://github.com/example/ichbinkalt-backend/pull/12
Merge or close them first, or run remove again with --close-prs.
```

If `gh` can't tell, because it isn't installed or logged in, or the remote isn't on GitHub, the script stops too. `--close-prs` skips the pull request check, for when the user has decided those pull requests can close. The other two checks still apply.

**Why stop instead of keeping the branch:** a kept branch has no worktree left to run `remove` from, so its copy on the remote would stay behind with nothing to clean it up. Stopping leaves everything in place for the next try.

## Don't use Claude Code's own worktree features

`EnterWorktree` with a `name`, a subagent's `isolation: worktree`, `use_worktree` for a new session, and `claude --worktree` all put the worktree in `.claude/worktrees/`, inside the repository. Create it with this script instead, then enter it with `EnterWorktree` and its `path`.

## If it fails

| The script says | What to do |
| --- | --- |
| `... already exists.` | Use that worktree if it's on the branch you want. Otherwise, ask the user. |
| `New branch ... needs --from <parent>` | Pass the branch the new one builds on, such as `--from 001-initial`. |
| `git:` and the branch is already used by another worktree | Work in that worktree instead. |
| `git:` and the worktree contains modified or untracked files | Commit or save the work first. Never force the removal. |
| `... so update it by hand` | The worktree step worked. Edit that workspace file yourself: add or remove the folder's entry, keep the entries sorted, and keep its comments. |
| `... does not exist.` | The worktree was removed by hand. Run `git worktree prune` in the main checkout, and remove its workspace entry yourself. |
| Sync: `... uncommitted or untracked files` | Run `sync` again once that work is committed. Never commit or stash someone else's edits to make sync run. |
| Sync: `its rebase conflicts in ...` | Run the printed command in that worktree, resolve the conflicts, and check the result. If a conflict needs a decision, ask the user. |
| Sync: `... has 1 commit it lacks; pull them in first` | Someone else pushed to this branch. Ask the user before pulling their commits in, then run `sync` again. |
| Sync: `already in <parent>, so it only waits for removal` | Remove its worktree with `remove`, which deletes the branch too. |
| Sync: `its parent ... no longer exists` | Record the new parent with `parent`. |
| Sync: `not checked out in any worktree` | Create a worktree for it with `add`, then run `sync` again. |
| Sync: `... not pushed, because it has ... commits that ... doesn't` | Someone else pushed to this branch. Ask the user before pulling their commits in, then run `sync` again. |
| Sync: `... not updated, because the push failed` | The local rebase stays. If the reason says `stale info`, someone pushed in between: run `sync` again, which fetches and checks again. Otherwise fix the cause, such as the network, and run `sync` again. |
| `Couldn't fetch ...` | The checks used the last fetch, and pushes may fail. Run the command again once the remote is reachable. |
| Remove: `Kept branch ...: it has work that isn't in ...` | Nothing is lost. If you know it was merged some other way, delete it yourself with `git branch -D <branch>`. |
| Remove: `Stopped ...: ... has 1 commit that ... doesn't` | Someone else pushed to the branch after its work was merged. Ask the user whether to pull those commits in or drop them. |
| Remove: `Stopped ...: ... doesn't have its work yet` | Push the parent, then run `remove` again. |
| Remove: `Stopped ...: deleting ... would close the pull requests ...` | Show the user the listed pull requests. Merge or close them, or, with the user's OK, run `remove` again with `--close-prs`. |
| Remove: `Stopped ...: couldn't check the pull requests ...` | If `gh` isn't logged in, ask the user to run `gh auth login`. If a sandbox blocked the network, run the command again with network access. With the user's OK, `--close-prs` deletes the copy without checking. |
| Remove: `... not deleted, because the push failed` | Run the printed command once the remote is reachable. |

## How it works

- `scripts/worktree.py` runs the commands. `checkouts.py` wraps git, `env_copy.py` copies the `.env`, `workspace.py` edits the workspace files, `lineage.py` keeps each branch's parent and base, `sync.py` rebases the children, `cleanup.py` decides what happens to a removed worktree's branch, `remote_copy.py` fetches, checks, pushes and deletes each branch's copy on the remote, and `pull_requests.py` asks `gh` which open pull requests use a copy.
- **Leases:** every push names the commit it expects on the remote, as in `--force-with-lease=<branch>:<commit>`. If the remote has anything else by then, the push fails instead of overwriting it.
- Each branch's parent and base live in git config, as `branch.<name>.worktreeParent` and `branch.<name>.worktreeBase`. They follow a renamed branch and go away with a deleted one.
- **Why the base matters:** the base is the parent commit where a branch's own commits start. A rebase gives commits new IDs, so after a parent is rebased, its old commits still sit under its children, and a plain `git rebase` would try to replay them a second time. Sync replays only the branch's own commits, with `git rebase --onto <parent's head> <base>`. If a branch was rebased by hand, its fork point is newer than the recorded base, and sync uses the fork point instead.
- `GIT_WORKTREES_UNLIST_PAUSE` sets the wait after the workspace files change, in seconds. The default is 3, and the tests use 0.
- It needs Python 3 and git. Deleting a branch's copy on GitHub also needs the `gh` CLI, logged in. It reads workspace files with Python's built-in `json`, which can't keep comments, so it leaves a file that has comments for a manual edit instead of rewriting it without them.
- Tests: `python3 -m unittest discover -s <this skill's folder>/tests`. They run on throwaway repositories.
