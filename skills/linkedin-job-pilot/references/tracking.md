# Post-application tracker updates

Read this file only after submission is reliably confirmed. The user has provided standing authorization for the scoped update defined below, so do not ask for a separate tracker approval.

Identify the existing tracker.csv row by Company and Role. Update that row; never create a second row for the same vacancy.
## Consistency flow

~~~mermaid
sequenceDiagram
    participant A as Agent
    participant C as tracker.csv
    A->>C: Parse and find the Company and Role row
    A->>A: Derive scoped Applied status
    A->>C: Edit the row's Status
    C-->>A: Re-read exact row
    A->>A: Verify against submission evidence
~~~

## Confirmed values

Use only a confirmation page, receipt, or application ID:

- Status: `Applied`.

## Standing authorization

After reliable submission confirmation, automatically update the existing row without asking again. The standing authorization is limited to setting Status to `Applied`.

It does not authorize creating another row, changing the schema, editing company or role identity, recording an unconfirmed attempt, or changing later lifecycle stages.

Do not overwrite Company, Role, the research columns (Company Website, Summary, Salary Range, Glassdoor Review), or Notes during an ordinary post-submit update.

Read tracker.csv with the Read tool, replace only that row's line with the Edit tool, then re-read and verify the exact row and that nothing else changed. If submission is ambiguous, do not claim Applied. Never retry or mark the role applied without renewed approval.

## Later stages

Use the same row for every later stage, following the Status lifecycle in discovery-tracking.md: `Rejected` when the employer declines before any interview, otherwise `Recruiter`, `Technical`, or `Behavioral` in the interview pipeline, then the final `Offer` or `No Offer`. An employer rejection after an interview stage is `No Offer`; use `Aborted` when the user explicitly ends pursuit of the role or withdraws. Change only Status. Write dates only into Notes, and only when the user gives them. Each new external write must be authorized by the user's request or an exact approved manifest. Never replace a newer stage with an older one without the user's explicit decision to resume or reapply.

## Sibling roles when a pipeline starts

When the user asks to move a row from `Applied` to an interview-pipeline stage (`Recruiter`, `Technical`, or `Behavioral`), make that change first. Then list the company's other rows and ask once whether to mark them:

~~~mermaid
flowchart TD
    A[User moves a row from Applied to an interview stage] --> B[Update that row's Status]
    B --> C{Company has other rows?}
    C -- No --> Z[Done]
    C -- Yes --> D[List them and ask once]
    D -- No --> Z
    D -- Yes --> E{Sibling's Status}
    E -- Blank --> F[Set Status Skipped and add the note]
    E -- Skipped or Closed --> G[Add the note, keep Status]
    E -- Applied, later stage, or Aborted --> H[Leave unchanged]
~~~

- The note is exactly `Pipeline kicked-off from other role`. Add it after any existing status-supporting Notes but before any `PoC:` entries, separated by `; `, and never remove existing Notes.
- A blank sibling becomes `Skipped` with the note. A `Skipped` or `Closed` sibling keeps its Status and gets the note. A sibling with `Applied`, a later stage, or `Aborted` stays unchanged; mention it to the user.
- Write nothing to the siblings until the user agrees; the user's reply authorizes only the rows listed in the question.
