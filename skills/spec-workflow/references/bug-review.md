# Bug review

Use these rules for Spec Workflow's [bug review](../SKILL.md#find-bugs-before-review). It runs after the cleanup pass and before the test merges and the guided review. The goal is to find bugs while the change is still open, so the user reviews code that's already fixed.

```mermaid
flowchart TD
    Clean[Cleanup pass done] --> Run[One bug review per repository, at medium]
    Run --> Found{What did it find?}
    Found -->|Nothing| Next[Test merges, then the guided review]
    Found -->|Confirmed bug| Fix[Fix it with a test]
    Fix --> Again[Re-review only the fixed files, once]
    Again --> Broke{New problem in the code a fix changed?}
    Broke -->|No| Next
    Broke -->|Yes| Ask[Stop and ask the user instead of patching again]
    Found -->|Plausible issue| Attach[Attach it to its chunk with a suggested change]
    Attach --> Next
    Found -->|Code the change did not touch| Outside[Record it as a finding outside scope]
    Outside --> Next
```

## Run it

- Run it in each repository with code changes, on the committed change: `/code-review` in Claude Code, or the host's own code review command elsewhere.
- Review exactly this change, from its recorded base to its head. Give the tool that comparison as its target, or name both commits in the request if it can't take one. Afterwards, check that each finding falls inside that diff.
- Always pass the level: `medium`, unless the user asks for another one. Without a level, `/code-review` reuses the last level the user typed, which may be `max`. Use `max` or `ultra` only when the user asks for them, because they start many reviewers and each run takes much longer.
- Don't pass `--fix` or `--comment`. Fixes follow the rules below, and nothing is posted to a PR.
- Skip repositories whose change is docs only, and record why. The checks in [Writing specs](writing-specs.md#before-merging-a-spec-change) cover spec changes.

**Why:** the agent that built the change also explains it in the review, so it tends to defend its own choices. A bug review reads the code fresh. One run on the whole change, rather than one after each chunk, costs less and also catches bugs that cross chunks, such as a backend function and the frontend call that misuses it.

## Act on each finding

| Finding | What to do | Why |
| --- | --- | --- |
| Confirmed bug in the change | Fix it with a test, as part of building the change. If the fix needs a product decision, return to specs first | The user should review code that's already correct. A fix during the review would reopen chunks they already accepted |
| Plausible issue in the change | Don't fix it on your own. Attach it to its chunk with a suggested change, and the user decides in the review | It may not be a real problem, and changing behavior on a guess is the user's call |
| Anything in code the change didn't touch | Record it under findings outside scope, and tell the user. Don't fix it in this change | Fixing it here would slip unrelated work into this review |

> Example: the bug review confirms that `resumeClass()` releases the device lock before the save finishes, so a second phone can open the same Class. The agent fixes it, adds a test that resumes from two devices, and the resume chunk explains the fix.

## Limit the reruns

A fix changes the change. Rerun the affected tests, and reassess the [cleanup pass](code-cleanup.md#when-the-pass-must-run-again) for the changed lines. Then:

1. **Re-review the fixes once.** Review only the files the fixes changed, at `medium`. Don't rerun the full review.
2. **Stop if the same code breaks again.** If the re-review finds a new problem in code a fix changed, don't patch it again. Tell the user what it found, and propose a redesign of that code. The user decides: redesign it, or keep the fix and judge the new problem in its chunk.
3. **Send everything else to the guided review.** Other findings from the re-review go to their chunks as plausible issues, for the user to decide.

An edit the user asks for during the guided review gets the same: its tests, the cleanup check, and one re-review of the files it changed.

**Why:** each fix can bring its own rare case. Without a limit, fix, review, and new finding can repeat round after round, and each round is another review. Two problems in a row in the same code usually mean its design is wrong, and another patch won't fix that.

> Example: the bug review confirms that two quick saves can overwrite each other in `saveChunk()`. The agent adds a lock and a test, then re-reviews `saveChunk.ts` once. The re-review finds that a save retried after a timeout can still land after a newer one. That's the same code breaking again, so the agent stops and asks: "Locks keep missing write orders here. Should I give each chunk a revision number, so the store rejects stale writes?"

## Record the result

For each repository, record in the work record the level, each fix and its commit, the re-review and what it found, each plausible issue and its chunk, the findings outside scope, and the heads the review covered. The [guided review](guided-review.md) shows each finding in its chunk, as the [guided-review](../../guided-review/SKILL.md#explain-the-chunk) skill describes.
