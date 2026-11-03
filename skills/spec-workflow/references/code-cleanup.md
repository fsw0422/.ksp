# Code cleanup

Use these rules for Spec Workflow's [pre-merge cleanup pass](../SKILL.md#clean-up-code-before-merging), or for an authorized code-only refactor. The goal is code that's easier to read and change, with the same behavior.

## Preserve behavior

- Read the repository's `AGENTS.md`, `CLAUDE.md`, and `CONTRIBUTING.md` when present. Inspect the working tree and keep unrelated user changes.
- Keep public APIs, saved data, side effects, errors, and user-visible behavior the same. An accepted spec replacement defines the new target; cleanup doesn't make new product or domain decisions. Under `--not-live`, cleanup can remove leftovers of a replacement that was already accepted.
- Establish a baseline with relevant existing tests. When important behavior isn't covered, first add characterization tests: tests that pin down what the code does today.
- Keep changes small and reviewable. Stay within the proposed change and the code it affects.

**Why:** behavior is decided in the spec and approved in review. Cleanup that changes behavior would slip a decision past both.

> Example: before splitting a long `finishClass()` method, add a test that records what it returns today for an ended Class. After the split, the same test must still pass.

## Clean up the code

- Use simple, clear names. Rename related tests and call sites together. Follow agreed domain terms, and return to specs before changing a shared concept.
- Remove dead code only after checking references, exports, configuration, reflection, dependency injection, and other dynamic uses. Missing documentation doesn't prove code is dead.
- Split large classes or methods along clear responsibilities. Avoid moving complexity into scattered helpers or wrappers that only forward calls.
- For generic functionality, check the standard library and existing dependencies first. Consider an established library when it offers a clear benefit.
- Before adopting a library, check its maintenance, compatibility, license, security, correctness, size, and operating cost. Keep output and wire formats unless a change is already accepted in scope.
- Remove replaced utilities and dependencies only after all callers have moved and checks pass.

> Example: a text search finds no callers of `formatLegacyPause()`, but a dependency-injection container registers it by name. It isn't dead, so leave it.

## Check for regressions

- Run focused tests after each logical change, then the repository's applicable format, lint, type, test, and build checks.
- Check affected integration boundaries after renames, dependency changes, or structural refactors.
- Compare behavior with the baseline, and fix regressions before going on. Never weaken or delete a valid test to make cleanup pass.

**Why:** a cleanup that breaks something costs more than the mess it removed.

## Record the result

Record each repository's parent, head, and spec SHAs, the scope, the outcome, and the checks in the work record. Also record what changed, why removed code was unused, any library tradeoffs, and the checks performed. If verification is incomplete, state what remains unchecked and why, and hold the affected merge.

A pass may make no edits. Record that result rather than inventing cleanup work.

## Cleanup on an integration branch

Cleanup edits go in the short-lived worktree that owns the change. If a release's cleanup edits would land on an integration branch, create or reuse a cleanup child of that branch instead. Review and squash that child into the integration branch, remove the child, and rebase siblings as usual. Then reassess the release at its new commit before the final review.

**Why:** nobody edits an integration branch directly, so its cleanup goes through a child like any other change.

## When the pass must run again

If the pass makes edits, check them, capture the updated candidate, and include the edits in the guided review. Changes after approval cancel the affected approvals. If the pass finds an unclear requirement or a behavior bug, route it through the spec or implementation steps before continuing.

At merge time, check that the cleanup result still covers the candidate. Changed content, bases, spec inputs, or a wider merge scope need a fresh assessment of the affected work. Reuse unchanged check evidence where it's still valid. A squash gives commits new IDs; if the content is verified to match what was approved, the pass doesn't need to run again. If required checks stay unresolved, hold the affected merge and report why.

> Example: after review, a sibling merges and this branch is rebased onto a new base, so the pass is reassessed. If `range-diff` shows the branch's own diff is unchanged, the earlier result still holds. If the diff changed, the pass runs again on the changed part, and the affected review chunks reopen.
