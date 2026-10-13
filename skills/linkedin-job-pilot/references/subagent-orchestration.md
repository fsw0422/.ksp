# Discovery concurrency and research agents

Read this file at the start of every discovery run before navigating results. Skip it for a tracking-only or single-role workflow without parallel discovery.

## Startup capacity preflight

The target spawned-agent capacity equals the maximum stable job cards on one result page or batch. Use the current page count when verified; otherwise use 25. This excludes the primary agent.

~~~mermaid
flowchart TD
    A[Discovery invoked] --> B[Determine jobs per page]
    B --> C[Read user Codex config]
    C --> D{Configured limit sufficient?}
    D -- Yes --> E[Continue]
    D -- No --> F[Raise only concurrency key]
    F --> G[Validate config]
    G --> H[Ask user to restart and reinvoke]
    H --> I[Stop]
~~~

Use the user-level Codex configuration at CODEX_HOME/config.toml, or ~/.codex/config.toml when CODEX_HOME is unset. The relevant setting is agents.max_concurrent_threads_per_session.

Rules:

- Never lower a higher value.
- If missing or lower, show the exact existing and proposed values and obtain approval before editing the configuration.
- After approval, update only that key and preserve unrelated configuration.
- A config change requires restart. Report old and new values and stop.
- If a later page exceeds the target, save the cursor and private ledger, request approval for the exact increase, and stop. After approval, raise the key, validate it, and require restart before resuming.
- If runtime capacity is lower despite valid config, queue remaining one-job tasks. Preserve one agent per job.
- Do not let job agents recursively spawn same-job helper trees.

## One research agent per stable job

The primary agent alone controls LinkedIn and local durable files. It navigates one page sequentially, deduplicates identities, writes initial CSV rows, and then dispatches one bounded read-only research agent per stable unique job.

~~~mermaid
sequenceDiagram
    participant P as Primary agent
    participant L as LinkedIn
    participant C as tracker.csv
    participant R as Job agents
    P->>L: Inspect cards sequentially
    P->>C: Add Researching rows with the Edit tool
    P->>R: Dispatch company owners
    R-->>P: Company dossiers and sibling identities
    P->>C: Write owner rows' research columns
    P->>R: Dispatch remaining one-job agents
    R-->>P: Structured role results
    P->>C: Write research columns
    P->>L: Advance only after page wave completes
~~~

Give each job agent:

- Exact job ID and posting URL from the private ledger, company, title, location, visible requirements, posting facts, and Premium signals.
- Candidate evidence verified for the current run.
- Fit-label definitions and tracker duplicate state.
- Existing company dossier text when relevant.
- A flag saying whether it owns one-pass company expansion.

Each agent returns:

- Stable identity, the exact official posting URL, and its open or closed state.
- Role requirements, duties, work mode, salary, and interview evidence, taken from the official posting first, with LinkedIn-only facts labeled.
- Required company facts with dated source links and confidence.
- Strongest evidence, largest gap, unknowns, and any verified blocker. Never a fit grade.
- Ready-to-write research columns as defined in discovery-tracking.md: Company Website, Summary, Salary Range (employer-published only, else blank), and Glassdoor Review (seen on Glassdoor only, else blank).
- Fitting sibling roles only when it is the expansion owner, found on the company's official careers page, each with its official posting URL.

Agent boundaries:

- The official careers-page posting is the source of truth for role facts; see company-research.md. Then official company sources, then reputable reporting.
- Targeted read-only Reddit, Blind, and Glassdoor checks when material.
- No browser use at all, as browser-pilot requires: no browser tools of any kind and no tab changes. Use web search and web fetch only.
- No LinkedIn control, application action, saving, dismissal, interest signal, profile visit, contact, or Reddit post.
- No local durable writes. Only the primary agent may write tracker.csv.
- No inference of authorization, language, relocation, compensation expectations, or other sensitive answers.
- No child agents unless the primary agent explicitly assigns distinct one-job tasks and capacity allows it.

## Company expansion and reuse

Maintain normalized company identities for the run. On each page:

1. Dispatch the first job for each new company as expansion owner.
2. Wait and merge company dossiers and sibling identities.
3. For each sibling found on the official careers page, take its exact title and deduplicate it against existing rows by Company and Role.
4. Parse tracker.csv and upsert only new sibling rows.
5. Verify each row.
6. Dispatch one agent for every remaining original and tracked sibling job.
7. Reuse existing rows' Company Website, Glassdoor Review, and company facts for companies researched earlier.
8. Do not recursively expand from sibling roles.

Wait for every dispatched job agent on the page to finish, fail, or request attention before advancing. Retry a transient research failure at most once. Never silently omit a job or invent missing evidence.
