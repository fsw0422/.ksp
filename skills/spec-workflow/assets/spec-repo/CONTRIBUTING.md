# Contributing to the specification

People and coding agents read this specification to build and check the product. It should make sense without its edit history.

## Where each fact lives

Every fact has one owner. Other documents link to the owner instead of restating it, even in different words.

| File or folder | Owns |
| --- | --- |
| `README.md` | The customer, the promise, the product boundary, and global success measures. It links to rules instead of stating them. |
| `features/` | One document per feature, with that feature's behavior rules and requirement IDs. |
| `contracts/` | Message shapes: OpenAPI for HTTP, JSON Schema for events and other payloads. |
| `architecture/` | System boundaries and deployment. `architecture/domain-model.md` owns domain terms and their names in code. |
| `decisions/` | The reasons for choices that cross features or are hard to reverse. |
| `research/` | Dated evidence. It never states requirements. |

## Write for readers

- Match the format of sibling documents.
- Use easy, concise words, and explain each rule in enough detail that someone new to the project can follow it. Explain a necessary technical term the first time you use it.
- Give plenty of concrete examples: a scenario for each rule, sample values, and what the user sees.
- Prefer a diagram when it explains the idea clearly. Use Mermaid inline: C4 for the system and its parts, sequence diagrams for interactions, state diagrams for lifecycles, and flowcharts only for flows with branches. Use a numbered list for simple steps.
- Give every diagram a short explanation in prose. Exact rules stay in prose or tables.

## Feature documents

Begin each feature document with a header block:

```yaml
---
status: draft             # draft | accepted
implementation: backlog   # backlog | partial | complete
validation: pending       # pending | partial | passed
prefix: CHECKOUT          # requirement ID prefix owned by this document
owners: [product, backend]
last-reviewed: 2026-01-31
---
```

Then use this order:

1. Purpose
2. Scope and non-goals
3. Main flow
4. States and rules that always hold
5. Failure and recovery
6. Requirements
7. Links to contracts and decisions

Keep a feature document under about 400 lines. Split it when it covers more than one independent lifecycle or protocol.

## Requirements

Define requirement IDs only in feature documents, in a table:

| ID | Rule | Example |
| --- | --- | --- |
| `EXAMPLE-001` | An empty cart MUST NOT be checked out. | A user with no items taps Checkout: the button is disabled and no order is created. |

- Each ID holds one testable rule. If a rule joins separate behaviors with "and", split it.
- Each row has a concrete example: the situation and the expected result.
- Each feature uses its own prefix, listed in its header.
- Keep an ID when you only clarify its wording. Retire an ID rather than reusing it for a different rule.

## Tests cite requirement IDs

A test that proves a rule names the rule's ID in its title:

```ts
it('EXAMPLE-001: an empty cart cannot be checked out', () => {
  // ...
})
```

A rule that no test cites is not proven yet. To find a rule's tests, search the code repositories for its ID.

## Domain terms

`architecture/domain-model.md` lists each domain term once, with its meaning and its names in code, storage, and APIs. Use the same word everywhere. Agree on a new name in the specification before renaming code.

## Decisions

Write a decision record only for a choice that crosses features or is hard to reverse. Name it `decisions/NN-short-title.md`, keep its status in the header block, and cover Context, Decision, and Consequences. Feature documents link to it. Smaller reasons belong in commit messages.

When a decision changes, rewrite the record to the current decision. Add a short "Why we changed" note when the old option might come up again. Git keeps the old text.

## Keep documents current

Documents describe the current product. Don't keep task lists, implementation plans, or old proposals in them. Git keeps the history, and active work is tracked outside this repository.

## Review checklist

Before merging a change to the specification, check that:

- relative links resolve, and no absolute paths to someone's computer were added
- requirement IDs are unique and defined only in `features/`
- each new or changed rule has an example, and a test cites its ID once the code exists
- Mermaid blocks render, and contracts parse
- the change updates the owning document instead of repeating it elsewhere
