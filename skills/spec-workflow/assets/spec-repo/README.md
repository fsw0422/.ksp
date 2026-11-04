# <Project name>

<One or two sentences: what the product is and who it is for.>

## Customer and problem

<Who the customer is, and the problem they have today.>

## Promise

<What the product promises the customer.>

## Core experience

<A small Mermaid diagram of the main path through the product. Link each step to the feature document that owns its rules.>

## Boundaries

<What is out of scope.>

## Success measures

<How we will know the product works for its customer.>

## Where things are

| File or folder | Owns |
| --- | --- |
| `features/` | One document per feature, with its behavior rules and requirement IDs |
| `contracts/` | Message shapes: <list each contract file and what it owns> |
| `architecture/` | System boundaries and deployment. `architecture/domain-model.md` owns domain terms and their names in code |
| `decisions/` | The reasons for choices that cross features or are hard to reverse |
| `research/` | Dated evidence only |
