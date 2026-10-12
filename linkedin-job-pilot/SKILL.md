---
name: linkedin-job-pilot
description: Discover, curate, research, and track LinkedIn roles, then prepare, submit, and update applications, including cover letter PDFs, using a user-provided PDF resume, a local CSV tracker that holds the research summary, and a single submit-approval application flow. Use when the user asks to browse or shortlist jobs, provide a company or role manually, evaluate a role, apply through LinkedIn or an employer site, write a cover letter, or track applications. Require a readable PDF resume before doing any work; resume creation and revision belong to resume-pilot.
---

# LinkedIn Job Pilot

Run an evidence-based job search while leaving every consequential choice with the user.

For all browser work on LinkedIn, careers pages, employer application sites, and the approved Reddit fallback, read and follow [../browser-pilot/SKILL.md](../browser-pilot/SKILL.md): browser choice, tabs, allowed tools, page loading, sign-in handoff, and form filling and read-back. This skill's approval and data rules take precedence over it.

Store all durable research and tracking data under the active user's home directory in `jobhunt`. Never fall back to a workspace-local copy, another home directory, a cache, or a cloud file.

## Canonical local resources

At the start of each run:

1. Resolve the active user's home directory once without deriving it from the current workspace.
2. Use <home-directory>/jobhunt as the only durable job-data root.
3. Use <home-directory>/jobhunt/tracker.csv for the tracker. It is the only research record; do not write research Markdown files.
4. Use <home-directory>/jobhunt/applicant-profile.md for the user's private application answers. Never commit, copy, or upload it; see references/applicant-profile.md.

Create `jobhunt` when missing. Reject symlinks or resolved paths that escape the active user's home directory. The tracker is a file, not a directory.

The exact tracker columns are:

Company, Role, Company Website, Summary, Salary Range, Glassdoor Review, Status, Notes

A row's identity is its Company and Role together. Job-board and posting URLs change with every repost, so the tracker never stores them; find the live posting from the company's careers page when needed.

Company Website, Summary, Salary Range, and Glassdoor Review hold the research result for the row; references/discovery-tracking.md defines them. Salary Range and Glassdoor Review are optional: fill them only with a value actually found, and leave them blank otherwise. Never estimate or guess either one.

Status holds only the application lifecycle. The cell must be empty or contain exactly one of these case-sensitive values: `Researching`, `Skipped`, `Closed`, `Applied`, `Recruiter`, `Technical`, `Behavioral`, `Rejected`, `Offer`, `No Offer`, or `Aborted`. Never write any other Status value to tracker.csv. Use `Aborted` when the user explicitly ends pursuit of a role or withdraws, before or after applying; see the Status lifecycle in references/discovery-tracking.md. Status is the only application record; the tracker stores no application or interview dates and no fit label.

Fit has one source of truth: LinkedIn's own match assessment for the role, such as its match details or applicant signals, read on LinkedIn when the role is opened. The skill never computes, labels, or stores a fit grade. The Summary may still name the main match and the biggest gap as research context.

Notes is free text owned by the user, for example recruiters, people contacted individually, or dates such as `Waiting cooltime: 23/03/2026`. Preserve it on every change, and write to it only when the user asks. Separate entries with `; `. Status-supporting entries, such as `Waiting cooltime: <date>` or `Pipeline kicked-off from other role`, come first; `PoC: <name>` entries always come last.

## Default explicit invocation

When the user explicitly invokes this skill, first apply the mandatory PDF gate. Once a PDF is verified, an invocation with no additional scope, or only Start discovery, begins from the already-open LinkedIn Jobs tab in the browser browser-pilot selects, using its current search, collection, location, and filters. If no such tab exists, open LinkedIn Jobs in that browser and use a secure browser handoff for sign-in when needed.

Run the complete workflow: capacity preflight, ten-page discovery horizon, immediate CSV tracking, one research agent per stable job, company-role expansion, automatic research-column population, and application queue preparation. Ask only for a genuinely missing material search criterion or an ambiguous choice between multiple open LinkedIn collections.

## Mandatory PDF resume gate

Before opening LinkedIn, reading the tracker, researching a company, evaluating a role, or entering an application workflow, require one exact PDF resume for the session. If no accessible PDF is provided, ask for it and stop.

Verify the resume once per session, the first time the skill runs: open it with the Read tool to confirm it is a PDF with usable extractable text, and record its absolute path, visible filename, page count, and SHA-256 from `shasum -a 256`. Later invocations in the same session reuse that record without re-reading the file or reporting the check again. Immediately before each upload, run `shasum -a 256` again and compare it with the recorded hash; if it differs, stop and ask the user to confirm the new file, then verify it again. If the file is unreadable, image-only, or ambiguous, stop and ask for a valid PDF.

Treat the PDF as immutable input. This skill may read it to write the Summary and the packet's role-alignment notes, draft answers from verified contents, and attach that exact file after the user approves submission. Extract the exact phone number, LinkedIn URL, and residence from it when those values are unambiguous so application forms can reuse them without asking again. When the resume has no phone number, use the PHONE answer from the applicant profile; never write it into the skill or the tracker. Extraction is not authorization to transmit them: show the values in the application packet and transmit them only after the submit approval below. The skill must not critique, edit, optimize, rebuild, rename, copy, commit, push, or upload the resume to LinkedIn preferences. Resume work belongs to resume-pilot.

## Applicant profile questionnaire

Before the first application work in a session, read references/applicant-profile.md and the user's profile file. If the catalog has questions the profile does not answer yet, ask all of them in one message, save the answers, and never ask them again. During an application, when a form asks a personal question that the profile does not cover, ask for the answer and whether to save it to the profile. Do not propose skill changes for new questions; the user maintains the catalog.

## Non-negotiable approvals

Research, comparison, cover letter drafting and PDF rendering, bounded tracker updates, and read-only application-form inspection may proceed without approval. For an ordinary named application, use exactly one approval gate:

1. **Submit approval:** after inspecting the form, present one complete application packet with every drafted answer, the full cover letter text and its PDF, every personal-data value, and every named file upload. When the user replies `submit` for that named role, enter everything in the browser, upload the files, verify the populated form against the packet, and click the final submit control without asking again.

Stop before submitting and ask again only when the populated form cannot be made to match the packet, a required field still lacks an answer, or a later form step reveals new personal data, files, or substantive content that the packet did not show. A newly revealed field whose answer exactly matches an applicant-profile answer or a value from the verified resume is not new: fill it, list it in the outcome report, and continue without asking. Present only the remaining items; the user's next `submit` covers them.

Do not ask for approval merely to open, navigate to, or inspect an application form when that action is read-only and shares no applicant data. If opening or advancing the form would itself save an application, transmit applicant data, or trigger a recruiter-visible action, do it only after the user says `submit`.

Outside the ordinary submit approval, stop and obtain explicit approval immediately before:

1. Sending any application-related message.
2. Activating Top Choice, I’m interested, or another recruiter-visible signal.
3. Posting an approved question to r/cscareerquestionsEU.
4. Changing the tracker schema.
5. Writing outside <home-directory>/jobhunt, except owner-only temporary scratch ledgers described in references/job-discovery.md and the temporary folder that scripts/render-cover-letter.py creates and deletes.
6. Changing the user-level Codex configuration, including discovery concurrency.

An approval must identify the company, role, action, materials, recipient, and exact message when relevant. Earlier approval for another role or action does not carry over.

Use the user's applicant-profile answers when a field has the same meaning and scope. Otherwise never infer work authorization, sponsorship, relocation, compensation expectations, notice period, demographic answers, disability, veteran status, criminal history, or other sensitive application data.

## Tooling: no ad-hoc scripts

Do not write one-off code at any step of this skill: no shell pipelines, inline Python, curl or API calls, or custom browser JavaScript. Use only these tools:

| Need | Use |
| --- | --- |
| Open, read, check, fill, and submit any website, including careers pages, job boards, and application forms | The browser tools allowed by browser-pilot |
| Read the resume or another PDF | The Read tool |
| Record the resume's SHA-256 | `shasum -a 256 <resume.pdf>`, the only allowed hashing command |
| Change tracker.csv, the applicant profile, or `letter.txt` | The Read, Edit, and Write tools |
| Render and verify a cover letter PDF | `scripts/render-cover-letter.py`, which prints pages, SHA-256, and text and header match |
| Install the CLI browser's Chromium build when it is missing | `npx -y @playwright/mcp@latest install-browser chrome-for-testing`, as browser-pilot describes |
| Research the web | Web search and web fetch tools, or subagents that use them |

Never run custom JavaScript in a page; browser-pilot lists the allowed browser tools. If a step cannot be done with these tools, stop and tell the user what is missing instead of improvising a script.

## Bounded local-write authorization

Explicitly invoking discovery or manual-role research authorizes these bounded home-local writes for that run:

- Create or update <home-directory>/jobhunt/tracker.csv without changing its eight-column schema, including the research columns: Company Website, Summary, Salary Range, and Glassdoor Review.
- After reliable submission confirmation, automatically set the existing tracker row's Status to `Applied`. This standing authorization covers only that Status change for the confirmed application; all other tracker changes keep their normal authorization requirements.

The run may also create or update <home-directory>/jobhunt/applicant-profile.md with answers the user gives in the questionnaire or agrees to save, as described in references/applicant-profile.md.

The run may also create or update <home-directory>/jobhunt/cover-letters/<company-file>-<role-file>/ with a drafted letter.txt and its PDF without approval, as described in references/cover-letter.md.

Browser output files, such as the `playwright-chromium-browser` plugin's snapshots, console logs, and screenshots, are temporary browser artifacts, not research or tracking records, and never belong in <home-directory>/jobhunt.

The primary agent is the sole writer. Subagents return structured research only.

For every CSV change:

1. Read the current file with the Read tool.
2. Check every existing row's Status against the exact allowlist above. If any value is unknown, stop and ask the user how to reconcile it; never silently replace or preserve an unknown Status in a rewritten row.
3. Before writing, check that each proposed Status is on the allowlist. If the user's wording differs, map it only when the intended stage is unambiguous; otherwise ask which allowed value to use.
4. Change only the target row or section with the Edit tool, replacing one exact, unique line or block; use the Write tool only to create a new file. Never rewrite the whole tracker.
5. Preserve user-authored content and unrelated fields. Keep tracker rows sorted by Company, case-insensitively, by inserting each new or renamed row at its sorted position; see "Row order" in references/discovery-tracking.md.
6. Keep CSV rows valid RFC-4180 UTF-8: eight fields, and quote a field that contains a comma, quote, or line break.
7. Re-read with the Read tool and verify every Status is allowed, the exact target row is correct, and nothing else changed.
8. Stop on a malformed row, ambiguous company identity, or path escape.

Use Company plus Role as the row identity, compared case-insensitively after trimming spaces. A job seen again under the same company and title, such as a LinkedIn repost or the same role in another city, reuses the existing row.

## Workflow

~~~mermaid
flowchart TD
    A[Readable PDF] --> B[Resolve home jobhunt paths]
    B --> C[Discover LinkedIn roles]
    C --> D[Upsert tracker.csv as Researching]
    D --> E[Run one research agent per job]
    E --> F[Write research columns in the row]
    F --> G[Verify the row]
    G --> H[Set Status Skipped or Closed only for a verified blocker]
    H --> I{More result pages?}
    I -- Yes --> C
    I -- No --> J[Build queue of rows with blank Status]
    J --> K{Decision-critical gap and public question needed?}
    K -- Yes --> L[Draft exact Reddit post]
    L --> M{User approves exact post?}
    M -- Yes --> N[Post only to r/cscareerquestionsEU]
    M -- No --> O[Keep documented gap]
    K -- No --> O
    O --> PV[Show next-job preview from the row]
    PV --> PG{User says go?}
    PG -- skip --> PV
    PG -- go --> P[Inspect application form read-only]
    P --> Q[Draft answers and render cover letter PDF]
    Q --> R[Present full application packet]
    R --> S{User says submit?}
    S -- No --> T[Revise, stop, or move to next role]
    T --> R
    S -- Yes --> U[Enter data, upload files, verify form]
    U --> V{Form matches packet?}
    V -- No --> R
    V -- Yes --> W[Submit and verify]
    W --> X{Submission reliably confirmed?}
    X -- Yes --> Y[Update tracker.csv automatically]
    X -- No --> Z[Report unconfirmed outcome]
~~~

## Route the work

### Discovery

Before discovery, read references/subagent-orchestration.md, references/job-discovery.md, references/company-research.md, and references/discovery-tracking.md.

Inspect every unique visible job through page 10, or stop earlier when LinkedIn genuinely ends. Select cards sequentially in the primary agent. Immediately upsert each stable job in tracker.csv as Researching, matching existing rows by Company and Role. Complete and verify the current page’s research columns and final statuses before advancing.

Do not cap tracking at a top-ten shortlist. A manually supplied role or company uses the same identity, research, persistence, and approval rules. For hand-picked companies or roles, discover and research openings on each company's official careers page, not through LinkedIn search; see Manual intake in references/discovery-tracking.md.

### Research

Use references/company-research.md. Write each role's result into its own tracker row: Company Website, Summary, Salary Range, Glassdoor Review. Set Status only when research verifies a blocker: `Closed` for a closed posting, `Skipped` for a hard blocker such as a required language, with the reason in the Summary. Reuse current company facts across that company's rows, but verify role facts separately. Do not create research Markdown or other per-company files.

Use official sources first, then reputable reporting. Check recent role- and location-relevant Reddit, Blind, and Glassdoor reports when accessible and material. Treat anonymous reports as anecdotal.

A public Reddit fallback is allowed only after ordinary research and CSV verification leave a decision-critical gap. Never propose a public post for a role with a Status.

### Application queue

Build the queue from the local CSV after research: every row with a blank Status, in tracker order, unless the user names a role. Exclude rows with any Status.

Keep `Aborted` rows out of the queue and preserve that Status during discovery and research. Preparing an application for one requires the user's explicit decision to resume that role, including a reapply decision if it was already submitted.

A role must remain open, and its Status must not show `Applied` or a later stage such as `Rejected`, `Recruiter`, `Technical`, `Behavioral`, `Offer`, or `No Offer`. Treat confirmed reposts as one application opportunity. Never auto-reapply; reapplying to such a row needs the user's explicit decision. When Notes mention a rejection, cooldown, or referrer, point it out in the preview.

### Next-job preview

Before preparing any application packet, show a short preview of the role and wait for the user's reply. Show it when the user asks for the next job, when the user names a tracked role, and at the end of every application outcome report, for the next role in the queue.

~~~mermaid
sequenceDiagram
    participant U as User
    participant A as Agent
    participant C as tracker.csv
    U->>A: next
    A->>C: Read the next queued row
    A-->>U: Preview built from that row only
    alt go
        A->>A: Check the posting is open, then follow application-gates.md
    else skip
        A->>C: Set the row's lifecycle to Skipped
        A-->>U: Preview of the following row
    end
~~~

Build the preview only from the row's columns. Do not research, open the posting, or inspect the form for it, so it costs no browsing. Use this shape:

~~~text
Next: <Company>, <Role> · <Status, or "not started">
- Company: <Company Website>
- Summary: <Summary>
- Salary: <Salary Range, or "not found">
- Glassdoor: <Glassdoor Review, or "not found">
- Notes: <Notes>            (only when not blank)
Reply go for the full packet, or skip.
~~~

When the row's Summary is blank, say so in the preview instead of researching; the packet step will fill it.

On `go`, find the live posting: open the company's careers page from Company Website and look for the exact role title, and search LinkedIn for the company and title only when the careers page does not list it. If it is closed, expired, or not found, set the row's Status to `Closed`, say so in one line, and show the next preview. Otherwise also open the role on LinkedIn by company and title to read LinkedIn's match assessment for the packet, then follow references/application-gates.md. On `skip`, set the row's Status to `Skipped` and show the next preview. A `skip` reply is the user's authorization for that one Status change.

### Applications and Premium

Before opening an application flow, read references/application-gates.md. Prepare the full application packet and preserve the submit approval. When a form asks for or accepts a cover letter, also read references/cover-letter.md.

Use visible Premium information as research and prioritization evidence only. Do not claim it guarantees ranking or response. Do not use bots, unofficial APIs, scrapers, mass invitations, or automated engagement.

### Post-application tracking

After reliable submission confirmation, read references/tracking.md and apply the user's standing authorization without asking again. Update the existing CSV row and set its Status to `Applied`. Never mark Applied from a click or assumption, and never extend this standing authorization to another lifecycle, field, row, or schema change.

When the user later moves a row from `Applied` to an interview stage (`Recruiter`, `Technical`, or `Behavioral`), update it, then ask once whether to mark the company's other rows with the note `Pipeline kicked-off from other role`, as "Sibling roles when a pipeline starts" in references/tracking.md describes.

## Completion standard

Report:

- PDF filename and hash used for fit.
- Resolved home directory and exact jobhunt paths.
- Search criteria, pages inspected, counts, duplicates, and stop reason.
- Totals of rows by Status, including blank.
- Exact tracker rows.
- Partial write or verification failures.
- Eligible application queue.
- Exact outcome of any approved application action.
- Cover letter text and PDF paths for any application that used one.

Never mark an application submitted without reliable confirmation.
