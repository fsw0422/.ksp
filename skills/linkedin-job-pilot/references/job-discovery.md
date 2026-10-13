# LinkedIn job discovery

Read this file for discovery, browsing, scanning, or shortlisting when no exact role is already selected. Complete subagent-orchestration.md first.

Discovery is non-engagement work. LinkedIn may record opened cards as viewed and use that activity for recommendations. Discovery authorizes only the bounded local CSV writes defined in the main skill. It does not authorize saving, dismissing, applying, signaling interest, contacting anyone, changing alerts, or opening named people profiles.

Maintain a private structured ledger of job IDs, occurrence positions, facts, dispositions, and the resume cursor. For large runs, the main skill explicitly authorizes an owner-only scratch directory under /private/tmp containing job facts only. This is temporary, not durable storage. Keep it until local writes and readbacks are verified, then delete it. If a restart is required, report its exact path as the private resume handle and verify it before resuming.

Discovery includes incremental CSV tracking, and research columns for every stable unique job. Do not cap research or tracking at a top-ten shortlist.

## Search horizon

~~~mermaid
flowchart TD
    A[Open LinkedIn Jobs] --> B[Verify account and search context]
    B --> C[Inspect current page]
    C --> D[Open each card sequentially]
    D --> E[Record stable facts and Premium signals]
    E --> F[Upsert tracker.csv as Researching]
    F --> G{Page complete?}
    G -- No --> D
    G -- Yes --> H[Dispatch company-owner agents]
    H --> I[Merge dossiers and sibling roles]
    I --> J[Track resolved sibling URLs]
    J --> K[Dispatch remaining one-job agents]
    K --> L[Wait and reconcile page wave]
    L --> M[Write and verify research columns]
    M --> N[Finalize CSV statuses]
    N --> O{Page 10 or stop condition?}
    O -- No --> P[Advance once and verify IDs changed]
    P --> D
    O -- Yes --> Q[Reconcile tracker and build queue]
~~~

- Preserve the current query, filters, sort, and collection.
- Inspect pages 1 through 10 inclusive by default; stop sooner when results end.
- Finish lazy-loading every card on a page before counting it complete.
- For infinite scroll, use observed page size or 25 stable slots per page equivalent, capped at 250 unique jobs.
- If recommendations rather than search results are open, use the unambiguous primary collection matching the user's criteria.
- Do not silently broaden location, level, work mode, recency, or company scope.
- Clarify material title or geography ambiguity. Never infer work authorization.
- A discovery request permits only the unavoidable viewed-job signal.

## Navigate job by job

The primary agent uses the authenticated UI and one result tab. Enumerate cards top to bottom, open one detail at a time, wait for it to settle, record it, then continue. Never parallelize UI navigation, use unofficial APIs, hidden endpoints, bulk scrapers, or automation extensions.

For each stable job:

1. Record the numeric job ID in the private ledger only, and read the company and exact title.
2. Parse tracker.csv, match existing rows by Company and Role case-insensitively, stop when more than one row matches, and reuse the unique matching row; a repost or another job ID with the same company and title is the same row.
3. Upsert a new row with blank research columns, Status = Researching, and blank Notes.
4. Preserve existing status, research columns, and application history for an existing row.
5. Write the row with the Edit tool and re-read it with the Read tool.
6. Stop on a conflicting Applied badge or unverified application history.
7. Finalize fit only after the assigned research completes and its research columns are written and verified.

After the page is recorded, follow subagent-orchestration.md. Complete the full page wave before navigating to the next page. Queue agents when runtime capacity is lower; never combine or drop jobs.

For every unique job record:

- Job ID and posting URL, kept in the private ledger only.
- Page and ordinal occurrence.
- Company, title, location, work mode, employment type.
- Posting age/date, promoted or reposted state.
- Stated compensation and type.
- Application channel without opening it.
- Visible badges and applicant count.
- Language, authorization, sponsorship, relocation, clearance, travel, or on-call requirements.
- Central qualifications.
- Company business, ownership, workforce, AI relevance, and financial or market signals.
- Salary and interview evidence with estimates and anecdotes labeled.
- Visible Premium signals.
- Strongest evidence, largest gap, and any verified blocker.

Card and detail-panel facts are listing data. The research agent replaces them with facts from the exact official posting on the careers page, keeps LinkedIn values only where the official posting is silent, and labels them; see company-research.md.

Use only the PDF accepted by the mandatory gate for personal fit. Do not substitute the LinkedIn profile or another resume. Premium is a tie-breaker, never proof of qualification.

## Fit

Fit has one source of truth: LinkedIn's own match assessment for the role, such as its match details or applicant signals, read on LinkedIn when the role is opened. The skill never computes, labels, or stores a fit grade. The Summary may still name the main match and the biggest gap as research context. Unknown information is not negative; never invent a grade.

## Deduplication

Use job ID as the temporary identity within a run and Company plus Role as the CSV identity.

- Consolidate repeated cards with the same ID and retain every occurrence position.
- Keep distinct URLs separate unless requisition, description, employer URL, and date evidence proves one vacancy.
- Record confirmed repost clusters in the private ledger, mention them in the Summary, and treat them as one application opportunity.
- Track roles with a verified blocker with Status `Skipped` or `Closed` instead of silently dropping them.
- Keep a short exclusion reason.
- Never dismiss or hide a LinkedIn job.

## Read-only boundaries

Do not:

- Click Apply, Easy Apply, or an employer application link.
- Save or dismiss jobs, create alerts, follow companies, or change preferences.
- Use Top Choice or interest signals.
- Send messages or requests.
- Open named profiles.
- Change the tracker schema or files outside the bounded <home-directory>/jobhunt paths.

## Stopping conditions

Stop when:

1. Page 10 or the tenth batch is fully processed.
2. LinkedIn shows the end of results.
3. Two consecutive bottom checks contain no new stable IDs.
4. Next fails to change page or IDs after one retry.
5. Search context changes and cannot be restored once.
6. A sign-in checkpoint, CAPTCHA, security warning, restriction, or rate limit appears.
7. Reliable order or identity cannot be established.
8. An application opens unexpectedly and context cannot be restored.
9. The user interrupts or changes criteria.

Never bypass safety barriers or rapidly retry unchanged pages. Preserve a cursor with search fingerprint, last page/ordinal/job ID, and stop reason.

## Discovery output

Return:

1. Search criteria and actual filters.
2. Pages inspected and stop reason.
3. Counts for cards, unique jobs, duplicates, unknown gates, and rows by Status.
4. Fit-grouped results with material evidence and links.
5. Skipped and Closed reasons, and common gap themes.
6. Verified CSV rows.
7. Eligible queue: rows with blank Status, in tracker order.
8. Compact resume cursor and private ledger handle only when needed.

Describe coverage as observed at scan time. LinkedIn can reorder or remove cards.
