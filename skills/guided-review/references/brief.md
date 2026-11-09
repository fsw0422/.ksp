# The brief

A workflow hands the [guided review](../SKILL.md) a brief: what to review, and what the decision does. Every field is optional. A missing field gets its default, and the review's opening says so.

| Field | What it holds | Default with no workflow |
| --- | --- | --- |
| **Comparison** | Each repository's base and head, and where to read it: a worktree folder, or a branch or commit | As [Find the comparison](#find-the-comparison) describes |
| **Why** | What the change must do, and its version, such as requirement IDs at a spec commit, or a ticket's acceptance criteria | The PR description and the commit messages. If they don't say, ask |
| **Starting plan** | A chunk map planned before building, or one chunk per acceptance criterion | Chunks cut from the diff |
| **Checks** | Checks already run, each with the commits it covered and its findings | Whatever is visible, such as CI on a PR, plus a bug review if none ran and the change has code |
| **Extra rules** | Rules to check each chunk against, such as a domain glossary or team conventions | None |
| **Edits** | Whether edits are allowed, where, and how to check one | Read-only: changes go back as suggestions |
| **Decision** | What the decision is for, its words, and what approval does | The user's verdict, with nothing posted |
| **Record** | Where the review record lives | The conversation |

**Why defaults:** the review then works the same everywhere. A workflow fills in what it knows, and the rest comes from defaults the user can see in the opening.

## Find the comparison

- **A local branch:** compare it with the branch it was created from, or else with the repository's default branch.
- **A pull request:** take its base and head from `gh pr view <number> --json baseRefName,headRefName,headRefOid`, or from what the user pasted. Read its code from the fetched head, without checking it out.
- **A ticket:** use its linked branch or pull request. If it has none, ask.

In every case, the base is the merge base, so the diff holds only the change's own work, as in `git diff main...feature`. A plain `git diff main feature` would also show the newer commits on `main`, reversed, as if the change undid them.

> Example: `fix/retry-timeout` started from `main` at `2c81f0a`. Since then, `main` got a new logging format. `git diff main...fix/retry-timeout` shows only the retry fix. `git diff main fix/retry-timeout` would also show the logging format going back to the old one.

Pin the head commit when the review starts, and name it in the opening. If the branch gets new pushes during the review, the affected chunks become stale, as [Keep the review record](../SKILL.md#keep-the-review-record) describes.

## Sample briefs

All made up. A workflow writes its brief down in its own words; these show what each kind of review fills in.

**A Spec Workflow merge review:**

```text
Comparison   backend: 6ace5c4..72894cf, in backend-initial-class-recovery
             specs: 1d9e0b2..4c7a113, in specs-initial-class-recovery
Why          REC-012 and REC-013, at spec commit 4c7a113
Plan         the chunk map in the work record
Checks       cleanup pass: no edits. Bug review at medium: 1 fixed, 1 plausible. Test merges: clean. 18 tests pass
Extra rules  domain mapping, the spec guardrail, --not-live
Edits        in the change's worktree, then its tests, the cleanup check, and one re-review
Decision     "approve for initial", after which Spec Workflow squashes and merges
Record       the change's entry in WORK_RECORD.md
```

**A colleague's pull request:**

```text
Comparison   merge base 2c81f0a to 4be91c0, the head of origin/fix/retry-timeout, read from Git
Why          the PR description
Plan         none, so the chunks are cut from the diff
Checks       CI passed at 4be91c0. Bug review: none yet
Extra rules  none
Edits        none: it's a colleague's branch
Decision     the user's verdict: approve, request changes, or comment. Nothing is posted unless they ask
Record       the conversation
```

**The user's own local branch:**

```text
Comparison   the merge base with main to the head of login-limit, in the folder auth-service
Why          the commit messages
Plan         none, so the chunks are cut from the diff
Checks       none yet, so a bug review runs first
Extra rules  none
Edits        none until the user asks, then only the edit they asked for, with its tests rerun
Decision     the user's verdict
Record       the conversation
```

**A Jira ticket:**

```text
Comparison   AUTH-88-login-limit against main, from their merge base
Why          AUTH-88's acceptance criteria, as pasted or read from Jira
Plan         one chunk per acceptance criterion
Checks       CI on the ticket's pull request, if it has one. Bug review: none yet
Extra rules  the team's review checklist, if the user names one
Edits        none: it's Priya's branch
Decision     the user's verdict. A Jira or PR comment only if they ask, after they see its text
Record       the conversation
```
