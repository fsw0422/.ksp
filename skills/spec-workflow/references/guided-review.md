# Guided review

Spec Workflow runs the [guided-review](../../guided-review/SKILL.md) skill for a spec before it's accepted, and before every merge, as [Review and merge](../SKILL.md#review-and-merge) describes. Load that skill and follow it. This page says how Spec Workflow fills the skill's brief, and which rules it adds.

**Why a separate skill:** walking someone through a change works the same in any workflow, so it lives in one place. Spec Workflow only says what goes into the review, and what an approval does.

## Fill the brief

| Field | Spec Workflow fills it with |
| --- | --- |
| Comparison | For each repository, the base and head commits from the work record, verified in Git, and the change's worktree folder and branch. The scope: spec acceptance, one repository, a coordinated merge, or the final release |
| Why | The accepted spec commit, and the requirement IDs the chunks implement, such as `REC-012`. A code-only change needs no invented spec counterpart: its why is the goal in the work record |
| Starting plan | The [chunk map planned before building](../SKILL.md#plan-the-chunks), from the work record |
| Checks | The [cleanup pass](code-cleanup.md), the [bug review](bug-review.md), the [test merges](git-operations.md#test-merge-with-open-branches), and the tests, each with the heads it covered. That includes a recorded "no code cleanup" result, or a skip reason, where one applies. A spec review has the checks in [Writing specs](writing-specs.md#before-merging-a-spec-change), and no bug review, because there's no code |
| Extra rules | The domain mapping, the spec guardrail, and the change's mode, as described below |
| Edits | Allowed, in the change's worktree. Check each edit as [Limit the reruns](bug-review.md#limit-the-reruns) describes: its tests, the cleanup check, and one re-review of the files it changed |
| Decision | For a spec review, "accept the spec". For a merge, "approve for `<destination>`". The decision is one of: spec accepted, changes requested, paused, rejected, deferred, walkthrough complete, or merge approved for an exact destination, plus any explicit waiver |
| Record | The change's entry in the work record, as [The review record](#the-review-record) describes |

The cleanup pass, the bug review, and the test merges are Spec Workflow's own steps, run before the review starts. The review checks that they cover the current heads, and says so before the first chunk when one is missing or stale. It doesn't run them itself. Each bug review finding appears in its chunk: a confirmed bug with the commit that fixed it, and a plausible issue with its suggested change.

Accepting a spec allows building. It doesn't approve the code or the merge.

## Spec Workflow's own rules

**Domain mapping.** For a domain-related chunk, check the [domain mapping](../SKILL.md#map-domain-language-into-code). Show how the spec term maps to the real model, storage, and contract names, and how its relationships and rules are represented. Flag unexplained synonyms or missing links. Use a small table or model diagram when it helps.

**Spec guardrail.** New behavior or shared terms missing from the specs follow the [spec guardrail](../SKILL.md#when-to-return-to-specs): keep the existing code, pause dependent merges, and decide in the spec first. Don't rewrite specs to justify the code.

**Spec and code sync.** For a [spec and code sync](spec-code-sync.md), include the finding, the accepted decision, and the change's [mode](spec-code-sync.md#use-the-tasks-mode). Explain the affected APIs, consumers, and data, and why old contracts or migrations are kept or removed. `--not-live` allows replacements within the accepted scope; unrelated feature decisions and merge approval still need their usual review.

**Squashes.** The new commit IDs a squash creates don't count as a change when the content is verified unchanged, as [Merge across repositories](git-operations.md#merge-across-repositories) describes.

**One approval covers one thing.** Approving one repository doesn't approve the others, the parent branches, or the final release.

**After the decision,** continue with [Review and merge](../SKILL.md#review-and-merge), which checks merge readiness and does only the authorized action.

## The review record

Keep the skill's review record in the change's entry in the work record, with these additions:

| Record | Spec Workflow adds |
| --- | --- |
| Identity and scope | The mode, live or `--not-live`, and for a sync, the finding and the accepted decision |
| Commits | Each repository's accepted spec commit, and the cleanup, bug review, and test merge results |
| Decision | The decision, as listed in [Fill the brief](#fill-the-brief), with its destination and the heads it covers |
