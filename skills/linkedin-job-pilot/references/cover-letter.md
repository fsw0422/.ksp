# Cover letters

Read this file when an application form asks for or accepts a cover letter, either as a file upload or as a text box.

The cover letter speaks for the user. Always draft the full version, save it, and render the PDF when the form wants a file, all without asking for approval. Show the exact text and PDF details in the application packet. The letter is typed or uploaded only after the user says `submit`.

## Flow

~~~mermaid
flowchart TD
    A[Form asks for or accepts a cover letter] --> B[Draft from the resume, job post, and research]
    B --> C{Upload field or text box?}
    C -- Upload field --> D[Save letter.txt and render one-page PDF]
    D --> E[Verify PDF]
    E --> F[Show letter text and PDF details in application packet]
    C -- Text box --> F
    F --> G{User says submit?}
    G -- Revise --> B
    G -- Yes --> H[Type text or upload PDF with the rest of the form]
    H --> I[Submit application]
~~~

## Style

Write the way the user asked:

- Colloquial and warm, like a real person talking.
- Full of excitement. Use `!` to show it.
- Only easy, everyday words. No buzzwords or stiff corporate phrases.
- Short sentences. Simple and concise: about 150 to 250 words in three or four short paragraphs, always one page.
- Easy to read at a glance.

Use this shape:

1. A greeting, such as `Hi Acme team!`. Use a person's name only when the posting or research names them.
2. Why this role and company excite the user, with one or two specific, verified reasons.
3. Two or three matching experiences, taken only from the resume.
4. A short, warm close.
5. A sign-off with the name exactly as it appears on the resume.

Write in English unless the posting asks for another language. In that case, ask the user first.

## Truth rules

The excited tone is the user's chosen style. The facts inside the letter must still be true:

- Use only experience, skills, titles, dates, and numbers that appear in the provided resume PDF.
- Use only company facts from the posting or cited research.
- Never invent metrics, responsibilities, relationships, referrals, or company knowledge.
- Leave out salary, visa or work authorization, notice period, and other sensitive facts unless the user supplies them for this letter.
- Point out any sentence the user should check before saying `submit`.

## Full-letter default

Always use the full 150-to-250-word letter described above whenever an application requests or accepts a cover letter. Do not offer A/B length choices or a routine `Do not include` option. Show one optimized full draft in the application packet; the user may request edits before saying `submit`.

If a hard character or file limit cannot accept the full version, produce the longest compliant version that preserves the same structure and substance, explain the limit, and include that exact text in the application packet.

## Save and render

Save the drafted letter without asking for approval in `<home-directory>/jobhunt/cover-letters/<company-file>-<role-file>/`, where both parts are lowercase with hyphens, such as `acme-senior-backend-engineer`:

- `letter.txt` holds the exact drafted text. Write it with the Write tool and re-read it with the Read tool.
- The PDF is named `<First>-<Last>-Cover-Letter-<Company>.pdf`, because recruiters see this name. Take the name from the resume and replace spaces and unsafe characters with hyphens. Create it only when the form wants a file.

Render the PDF with:

```sh
python3 scripts/render-cover-letter.py \
  --letter <folder>/letter.txt \
  --name "<name from the resume>" \
  --contact "<email · phone · city from the resume; phone from the applicant profile if the resume has none>" \
  --title "<Name> – Cover Letter – <Company>" \
  --date "<today, such as 29 September 2026>" \
  --paper a4 \
  --out "<folder>/<PDF name>" \
  --preview "<folder>/preview.png"
```

Use `--paper letter` for postings in the US or Canada. The header uses the name and contact line exactly as they appear on the resume; show them with the letter in the application packet. If the script is unavailable, stop and tell the user; do not improvise another renderer.

If the script reports that the letter does not fit on one page, shorten it and render again. If the user asks for edits, update `letter.txt`, render again, and show the new version. Never keep a PDF that differs from `letter.txt`.

## Verify

The script verifies every PDF it renders and prints one line:

```text
<pdf path> pages=1 sha256=<hex> text_match=yes header_match=yes
```

Before presenting the application packet:

1. Accept the PDF only when the script exits 0 and prints `pages=1`, `text_match=yes`, and `header_match=yes`. Exit 2 means more than one page: shorten the letter. Exit 3 means the text or header does not match: fix `letter.txt` or the arguments and render again.
2. Record the path, filename, page count, and SHA-256 from that line.
3. Look at the `--preview` PNG with the Read tool to catch layout problems.
4. To re-check an existing PDF without rendering, run the same command with `--verify-only`.

Keep cover letter text out of tracker.csv. The tracker is a research and status record, not an application archive.

## Upload

Attach the PDF, or type the text, only after the user says `submit`, together with the rest of the form and the same way as attaching the resume. If the letter changes after the packet was shown, show the new version before transmitting it.

Never upload the cover letter in place of the resume, and never add it to LinkedIn `My qualifications`.
