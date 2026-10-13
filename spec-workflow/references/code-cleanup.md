# Code cleanup

Use these rules for Spec Workflow's [pre-merge cleanup pass](../SKILL.md#clean-up-code-before-merging), or for an authorized code-only refactor within the workflow. Improve maintainability while preserving accepted behavior and domain terms.

## Preserve behavior

- Read the repository's `AGENTS.md` and `CONTRIBUTING.md` when present. Inspect the working tree and preserve unrelated user changes.
- Preserve public APIs, persisted data, side effects, errors, and user-visible behavior. An accepted spec replacement defines the new target; cleanup does not make new product or domain decisions.
- Establish a baseline with relevant existing tests. Add characterization tests first when important behavior is not covered.
- Keep changes small and reviewable. Stay within the proposed change and its affected code.

## Clean up the code

- Use simple, clear names. Rename related tests and call sites together. Follow agreed domain terms; return to specs before changing a shared concept.
- Remove dead code only after checking references, exports, configuration, reflection, dependency injection, and other dynamic uses. Missing documentation does not prove code is dead.
- Split large classes or methods along clear responsibilities. Avoid moving complexity into scattered helpers or wrappers that only forward calls.
- For generic functionality, check the standard library and existing dependencies first. Consider an established library when it offers a clear benefit.
- Before adopting a library, check its maintenance, compatibility, license, security, correctness, size, and operating cost. Preserve output and wire formats unless a change is already accepted in scope.
- Remove replaced utilities and dependencies only after all callers have moved and checks pass.

## Check for regressions

- Run focused tests after each logical change, then the repository's applicable format, lint, type, test, and build checks.
- Check affected integration boundaries after renames, dependency changes, or structural refactors.
- Compare behavior with the baseline. Fix regressions before proceeding. Never weaken or delete a valid test to make cleanup pass.
- Record what changed, why removed code was unused, any library tradeoffs, and the checks performed. If verification is incomplete, state what remains unchecked and why; hold the affected merge.

A pass may make no edits. Record that result rather than inventing cleanup work.
