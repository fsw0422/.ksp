# Examples

More examples for the [guided review](../SKILL.md)'s rules. All are made up.

## Which code goes in the chat

The chunk "Lock after 5 failures" changes `limiter.py`, its test, and a logging helper, and renames `attempts` to `failures` in 8 other files. The chat shows the lines in `limiter.py` that count and lock, with two notes, and the test line that checks the limit. It shows the rename once and lists the other 7 files. The logging helper gets one sentence. When the user replies "line by line", the agent shows the helper's lines as a diff with notes, and waits.

## A prose chunk

A chunk raises the lock time in the spec from 15 to 30 minutes. A diff of the spec's long lines would scroll sideways, so the chat quotes the wording instead: before, "A locked account opens again after 15 minutes"; after, "A locked account opens again after 30 minutes".

## "Looks good" in the middle

After chunk 2, the user says "looks good". The agent marks chunk 2 as accepted and shows chunk 3. That covers chunk 2 only. The whole change needs its own decision at the end, in the words the brief defines, such as "approve" for a pull request, or "approve for `initial`" in Spec Workflow.

## An approval goes stale

The user accepts chunk 1 of a colleague's pull request. Before chunk 2, the colleague pushes a commit that changes two lines in chunk 1. The agent says so, pins the new head, shows chunk 1's changed lines again, and asks about that part again.

## A change request on someone else's branch

In a review of Priya's branch, the user says "change it to count in the database". Nothing in the brief allows edits, so the agent leaves her branch alone. It writes the change as a suggestion with the code, ready to paste into a review comment, records it, marks the chunk ✎, and offers to go on. It posts the comment only if the user asks, after showing them the text.

## Something the why doesn't cover

AUTH-88's criteria cover the login limit, but the branch also shortens the session timeout from 8 hours to 1. The agent shows that as its own chunk, says that no criterion covers it, and asks whether it belongs in this ticket. Being in the branch doesn't make it part of the ticket.

## A missing input

A workflow's brief gives the comparison and the plan, but no checks. The opening says "Checks: none given, so running a bug review at medium first" instead of leaving the line out. The user sees the gap before the first chunk, and can say "CI already ran, skip it".
