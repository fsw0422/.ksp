# Work record

Current work only. When a change's state changes, rewrite its entry instead of adding a new one. When a change is finished, move a short summary to `WORK_HISTORY.md` and delete its entry here: the change name, its destination, each repository's squash SHA, the date, and what happened to its recovery data.

Updated: <YYYY-MM-DD HH:MM>

## Priorities

1. <change name>: <why it comes first>

## <change name>

- **State:** <spec draft | implementing | cleanup | in review | approved | merging | blocked | paused>
- **Goal:** <the result we want, in one sentence>
- **Mode:** <live | --not-live>, from <the request | the project default | the default>
- **Authorized:** <what the user has approved for this change, such as "build within the accepted spec" or "merge into `initial`">
- **Parent:** `<parent branch>`, because <why the change belongs there>
- **Depends on:** <other changes this one waits for, or nothing>
- **Spec:** accepted at `<sha>` | not needed: <reason>
- **Spec and code:** <agree | gaps: what is missing or different>
- **Repositories:**

  | Repo | Worktree | Branch | Base | Head | Squash | Checks |
  | --- | --- | --- | --- | --- | --- | --- |
  | <repo> | `<absolute path>` | `<branch>` | `<sha>` | `<sha>` | – | <passed / not run> |

  Base is the parent commit where this branch's own work begins. Fill in Squash when that repository's merge succeeds, and add "pushed" once the parent's push goes through, such as `` `a1b2c3d`, pushed ``, so a retry skips what's done.

- **Chunk map:** <chunks in build order, each with its requirement IDs and repositories; mark the riskiest and the ones already built>
- **Unaffected:** <repo>: <evidence>
- **Cleanup pass:** <not run | no edits | edits in `<sha>`>, for inputs `<shas>`
- **Bug review:** <not run | skipped: docs only | no findings | fixed: <finding> in `<sha>`, re-reviewed `<files>`: <clean | new problem, asked the user>; plausible: <finding>, in chunk <name>; outside scope: <finding>>, at `<level>`, heads `<shas>`
- **Test merges:** <not run | clean with every open branch | conflict with `<branch>` in `<files>`: adjusted, left for its rebase, or decision asked>, at heads `<shas>`
- **Review:** <not started | chunk <n> of <m>, accepted 1–<n> | approved for `<destination>` at `<shas>`>
- **Needs rebase:** <no | left behind by sync on `<date>`: a conflict in `<files>`, uncommitted files, or commits on its remote copy that it lacks>
- **Done so far:** <merged repositories, removed worktrees, rebased siblings>
- **Recovery:** <checkpoint commits and refs under `refs/recovery/`>; delete when <condition>
- **Blocked by:** <nothing | the decision or failure, and who must act>
- **Next action:** <the step, and how we will know it is done>
