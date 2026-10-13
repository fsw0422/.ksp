# Applicant profile

Read this file when the skill is invoked for any application work, and before inspecting an application form.

Application forms keep asking the same personal questions: work permit, notice period, salary, demographics, consents. The user answers each one once in a private profile file, and the skill reuses those answers on every application.

## The profile file

- Path: <home-directory>/jobhunt/applicant-profile.md, next to tracker.csv.
- It holds the user's personal answers. Never commit it, copy it into this skill or any repository, upload it, paste it into the tracker or a cover letter, or send it to a subagent. Share only the single answer a form field needs, after the submit approval.
- Read and change it only with the Read, Edit, and Write tools. Create it with the Write tool the first time the questionnaire runs.
- The user owns it. Change an answer only when the user gives or confirms the new value.

Write one section per question ID from the catalog below, in the same order:

```markdown
## NOTICE-PERIOD
Answer: <the user's answer>
How to apply: <optional, e.g. which option to pick when a form offers ranges>
Updated: <YYYY-MM-DD>
```

"How to apply" is optional and only explains how to map the answer onto different form wordings. Questions the user adds during applications go under a final `## Additional answers` heading in the same shape, with the form's wording as the heading.

The catalog is the reusable baseline maintained with the skill. For each new form question that is not a per-company fact, ask whether it belongs in that template. A yes starts the skill PR lifecycle and stores the private answer under the proposed catalog ID in the generated profile. A no writes the question and answer directly under `Additional answers` in the generated profile without changing the skill repository.

## Catalog questionnaire

On the first application work in a session:

1. Read the profile file. If it is missing, treat every question as unanswered.
2. Compare it with the catalog. A question is unanswered when its ID has no section or an empty Answer.
3. If any are unanswered, ask all of them in one numbered message before continuing. Show each question's choices, and allow "prefer not to say" for any demographic or optional question.
4. Write every answer into the profile, re-read it, and continue the user's request.

Never ask an answered catalog question again. When the user maintains this catalog and adds a question, the next run asks only that new one.

## Using answers on a form

```mermaid
flowchart TD
    A[Form field] --> P{Per-company fact?}
    P -- Yes --> Q[Use for this application only]
    P -- No --> B{Matching profile answer?}
    B -- Yes --> C[Use it and show it in the packet]
    B -- No --> D{Derivable from resume or tracker?}
    D -- Yes --> E[Use the verified value]
    D -- No --> F[Ask the user for the answer]
    F --> G{Add to the catalog template?}
    G -- Yes --> H[Start the skill PR lifecycle]
    H --> J[Store the answer under the catalog ID in application-profile.md]
    G -- No --> I[Write it under Additional answers in application-profile.md]
```

- Use an answer only when the field has the same meaning and scope. For example, a German work-permit answer does not answer a US work-authorization question.
- When a question is not in the profile, ask for the answer and whether to add the question to the reusable catalog template.
- A yes authorizes the skill PR lifecycle: create a branch, add a stable question ID to the source catalog, validate, commit, push, and open a PR. Keep the answer private by writing it only to the generated profile under that ID.
- A no writes the question and answer directly under `Additional answers` in the generated profile and continues the application without changing the skill repository.
- Per-company facts remain application-specific and are not saved to the profile.
- Profile answers never replace the submit approval for a named role. Every value still appears in the application packet.

## Question catalog

### Work authorization and location

| ID | Question |
| --- | --- |
| WORK-PERMIT-DE | Are you authorized to work in Germany, and with which permit? |
| SPONSORSHIP | Do you need visa sponsorship now or in the future for Germany? |
| US-PERSON | Are you a "U.S. person" (US citizen, green-card holder, refugee, or asylee)? |
| SANCTIONS | Are you a citizen, national, or resident of an embargoed or sanctioned country, such as Iran, Cuba, North Korea, or Syria? |
| NATIONALITY | Your citizenship(s), or "prefer not to say" when a form asks for diversity reporting |
| RESIDENCE | Which city and country do you live in? |
| WORK-MODE | Do you accept hybrid, fully onsite, or remote-only roles? |

### Availability and pay

| ID | Question |
| --- | --- |
| NOTICE-PERIOD | What is your notice period? |
| START-DATE | What is your earliest start date? |
| SALARY | Desired annual gross salary: your minimum, the single number for exact fields, and the currency |

### Personal and legal

| ID | Question |
| --- | --- |
| LEGAL-NAME | Your legal first and last name as on official ID, in Latin characters |
| PREFERRED-NAME | The first name you prefer to be called |
| PHONE | Your phone number with country code, for forms and cover letters when the resume has none |
| PRONOUNS | Your pronouns, or "prefer not to say" |
| GENDER | Gender for diversity forms, or "prefer not to say" |
| AGE-RANGE | Age range for diversity forms, or "prefer not to say" |
| DISABILITY | Disability status for diversity forms, or "prefer not to say" |
| CRIMINAL-RECORD | Do you have a criminal record or pending charges? |

### Profiles and languages

| ID | Question |
| --- | --- |
| GITHUB | Your GitHub profile URL, or none |
| WEBSITE | Your personal website or portfolio URL, or none |
| LANGUAGES | Each language you speak with its level (native, or CEFR A1 to C2) |

### Consents and preferences

| ID | Question |
| --- | --- |
| AI-SCREENING | Do you accept the employer's AI-assisted screening of your application? |
| OPTIONAL-CONSENTS | Text-message updates, marketing, talent pools, and future-opportunity retention: opt in or out? |
| REQUIRED-CONSENTS | May the skill agree to a data-processing consent that is required to submit the application? |
| HOW-HEARD | What do you answer to "How did you hear about this job?" |

## Not stored in the profile

- Contact details on the resume: name, email, LinkedIn URL, and residence come from the verified resume. The phone number comes from the resume when it has one, otherwise from PHONE above.
- Per-company facts: whether you previously applied to, interviewed with, or worked for this employer or its auditor, referrer names, and cooldowns. Answer these from the resume, the tracker, and research, and ask when they are ambiguous.
