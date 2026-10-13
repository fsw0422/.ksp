# Company and role research

Read this file for every stable unique role during discovery and every manually supplied role. Research is part of discovery, not a later top-ten phase.

Research ends in the tracker row's research columns, defined in discovery-tracking.md. Do not write research Markdown or other per-company files.

## Research order

~~~mermaid
flowchart TD
    A[Exact official posting on the careers page] --> B[Official company sources]
    B --> C{Enough material evidence?}
    C -- No --> D[Use filings, reporting, LinkedIn, Levels, Reddit, Blind, Glassdoor]
    C -- Yes --> E[Reconcile dates and contradictions]
    D --> E
    E --> F[Complete brief and final fit]
    F --> G[Write and verify the row's research columns]
    G --> H{Decision-critical gap remains and a public question could resolve it?}
    H -- Yes --> I[Draft r/cscareerquestionsEU question]
    H -- No --> J[Finish without public post]
    I --> K{User approves exact post?}
    K -- Yes --> L[Post only there]
    K -- No --> J
    L --> J
~~~

Start with the job URL, role, location, posting date, and user constraints, then find the exact official posting.

## Careers page is the source of truth

The employer's official careers page, or the job board it uses (Greenhouse, Ashby, Lever, Workday, and similar), is the source of truth for every role. This includes roles found on LinkedIn and sibling roles found during company expansion. LinkedIn is a bulletin board for finding listings and a fallback for missing details.

~~~mermaid
flowchart LR
    A[LinkedIn card or user input] --> B[Find exact official posting]
    B -- Found --> C[Take role facts from the official posting]
    C --> D{Fact missing there?}
    D -- Yes --> E[Fill from LinkedIn, labeled as LinkedIn-only]
    D -- No --> F[Use official value]
    B -- Not found --> G[Use LinkedIn text, mark the role as not verified on the careers page]
~~~

1. Find the exact posting for the role on the official careers page. A generic careers or search page is not enough. Confirm the board belongs to the same employer.
2. Take requirements, duties, level, location, work mode, compensation, language, authorization, and posting dates from the official posting.
3. Use LinkedIn text only for facts the official posting does not state, such as applicant counts, repost state, or Premium signals, or a detail the employer omitted. Label each such fact `(LinkedIn only)`.
4. When the official posting and LinkedIn disagree, the official posting wins. Mention the difference in the Summary only when it matters to the user, such as a different work mode or salary.
5. If the posting is closed on the careers page but still listed on LinkedIn, treat the role as closed.
6. If no official posting can be found, research from LinkedIn, say `not on the careers page` in the Summary, and lower confidence.

The diagram is a priority order, not a requirement to search every site. Stop adding sources when material questions are answered. Respect access controls and report unavailable evidence.

For each company establish its business model, ownership or funding, approximate workforce, AI relevance, and material financial or market signals. For each role establish hard requirements, central duties, work mode, compensation, interview signals, candidate match, largest gaps, and source dates.

Reuse current company facts across roles, but verify role facts separately.

Complete the full material checklist for each role. A verified hard blocker, such as a closed posting or a required language the resume lacks, may end research early after recording the blocker in the Summary and setting Status to `Closed` or `Skipped`.

## Research checklist

| Area | Questions |
| --- | --- |
| Business | What does it sell, to whom, and how does it earn money? |
| Stage and ownership | Public, private, acquired, bootstrapped, or venture-backed? |
| Financial health | Revenue, growth, profitability, burn, funding, runway clues, and risks |
| Workforce | Headcount, hiring, offices, layoffs, reorganizations, attrition |
| Role | Team, duties, level, reporting line, work mode, visa support, success measures |
| AI relevance | Products, internal tools, partnerships, technical posts, hiring signals |
| Compensation | Base, bonus, equity, total compensation, location, level, date |
| Interviewing | Stages, coding, design, take-home, behavior, timing, difficulty |
| Culture | Repeated strengths, concerns, workload, management, office expectations |
| Market | Competitors, differentiation, concentration, regulation, current news |
| Candidate fit | Evidence, gaps, transferability, objections, label-changing facts |

## Source discipline

Use this reliability order:

1. Audited filings, the official job posting on the careers page, investor relations, and direct company publications.
2. Reputable reporting and attributed databases.
3. LinkedIn company and workforce signals, and LinkedIn job text as a labeled fallback for facts missing from the official posting.
4. Levels.fyi and recent role- or location-relevant Glassdoor, Blind, and Reddit anecdotes.

Check material facts against a dated source while researching, and prefer the most recent reliable one when sources disagree. Estimates may inform the fit, but never write an estimate into Salary Range or Glassdoor Review.

For every role without a verified blocker, run targeted read-only Reddit, Blind, and Glassdoor searches when accessible and material. Prefer recent reports for the same country, office, discipline, and level. Treat anonymous reports as anecdotal and never let one report override stronger official evidence. When Glassdoor shows a company rating, record it in Glassdoor Review; when it does not or is not accessible, leave the column blank. Put a decision-relevant culture red flag in the Summary.

## Reddit fallback

Use the posting fallback only after ordinary research is complete, the CSV row is verified, and the remaining gap is decision-critical. Never propose a public post for a role with a Status.

Draft a concise r/cscareerquestionsEU post with:

- A neutral title.
- Generalized role, country, and seniority.
- Specific unresolved questions.
- Brief verified context.
- No confidential information, personal identifiers, account email, application ID, or unnecessary resume details.

Before posting, show the active handle, subreddit, flair, exact title, exact body, and whether the employer or role is identifiable. State that the post will be public. Hard stop until the user approves that exact draft and identity. Any edit, reply, message, vote, cross-post, or deletion requires separate approval.

## Research result

End each role's research with exactly these values for its tracker row:

| Column | Value |
| --- | --- |
| Company Website | The company's main website |
| Summary | One line, at most 320 characters: what the company does; revenue or `revenue not public`, plus funding or ownership; location and work mode; the main fit reason; the biggest gap or red flag |
| Salary Range | Only a numeric range the employer published for this role and location; otherwise blank |
| Glassdoor Review | Only a rating seen on Glassdoor, such as `4.4/5 (17 reviews)`; otherwise blank |
| Status | Blank, or `Closed` or `Skipped` only for a verified blocker. Never a fit grade. |

After each result, follow discovery-tracking.md: write the research columns and Status into the row, verify it, and move on. Do not wait for all pages or a separate batch.
