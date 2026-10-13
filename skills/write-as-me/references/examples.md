# Examples

Paraphrased from his real messages, with names, customer details and security settings replaced by placeholders. Mechanics (line breaks, capitalization, punctuation, emoji) follow the labelled register.

## Casual vs slightly formal (same message)

Casual, as he'd type it to his manager:
```text
the call yesterday was not helpful either :harold:
they couldn't reproduce the error

continuing today though with others in the channel
```

Slightly formal (default):
```text
The call yesterday wasn't helpful either.
They couldn't reproduce the error.

I'm continuing today with others in the channel though
```

## Asking for reviews

PR review, own team (slightly formal):
```text
@<reviewers> can you please review <PR link>?
Thanks
```

PR review, other team (slightly formal):
```text
Hi @<team>, can you give a quick review on <PR link>?
We're fixing how <feature> is scoped so it doesn't show up in other orgs.
Thanks!
```

Urgent review (slightly formal):
```text
:alert1: Urgent :alert1:
@<reviewers> can you please review <PR link>?
This is the mitigation for the ongoing incident.
Thanks
```

## Support / on-call

Answering a support question (slightly formal):
```text
Hi @<support>, this seems to be an SSO/SCIM org where no one (even the admin) can change their email unless the IdP changes it.
Can you ask the org admin to contact their IT department to change the email and sync it?
```

Follow-up after a fix (slightly formal):
```text
@<support> I've merged <PR link>
What this does is shorten the reset window from <old> to <new>, and raise the IP attempt limit <old> -> <new>, so it takes more attempts to trigger the CAPTCHA.

These numbers are based on the org's login attempts during the day.
If the problem persists, we'll keep tuning them.
```

Closing a ticket (slightly formal):
```text
I'll close this ticket for now.
However, feel free to open another thread in #<team-channel> by linking this one if the resolution doesn't work for the customer.
```

## Investigation / incident write-ups

Alert triage reply, preferred shape (from Kevin's feedback, 2026-09-27):
```text
Looks like a staging-wide database hiccup, not us
- The database couldn't find its tables for ~8 min (03:19 to 03:27 CEST)
- Every staging service got hit, not just this route
- 28 errors here, all from nightly autotests
- No deploy, it fixed itself
- All clean since

Nothing to do on our side.
We could add a min traffic check to this alert though
Dashboard
```

Dead end, DM to manager (slightly formal):
```text
FYI, I continued today where I left off and hit a dead end on <ticket>.

In short:
Seems like ServiceA has been causing the exception since mid-October, and I can't find the root cause yet.
Flow is ServiceA -> ServiceB -> ServiceC (blows up)
ServiceB and ServiceC didn't change.
I asked the owning team on Wednesday and they don't know either.

Is it worth investigating further?
```

Progress and a proposal, team channel (slightly formal):
```text
I couldn't make much progress on <PR link> since on-duty was quite disruptive.

Here's where it is:
1. The code data has no TTL of its own, so I've put 30 days as a placeholder.
   I'd like some opinions on this.
2. We're still on a shared Redis cluster.
   I think if we store this in our own database with a TTL, we'll never have to migrate it again.
   What do you think?

FYI, very few users should be impacted (~9 req/min at peak) when we turn the switch on.
```

Hypothesis in an incident thread (slightly formal):
```text
Strange that there are no logs.
I'm still leaning towards the sheer amount of data this user triggers being the root cause :thinking_face:
Do you know any other user with this many teams?
```

Incident channel, first response (slightly formal):
```text
Looking into it
What are the affected environments now?
Is it only staging?
```

```text
I'll check what changed recently on the BE side.
Either it never worked before, OR something changed recently.
```

## Decisions and discussion

Proposal to manager (slightly formal):
```text
Ok, let's push the metrics then, with an alert on top.
What do you think?
I'll approve yours and open the alert with that metric.
```

Laying out options (slightly formal):
```text
I'll put it this way:
option1: pick the numbers based on the investigation, but keep the current window
option2: lower the lockout period -> if you think this doesn't need a whole security review, I'm good with this one
```

Polite disagreement (slightly formal):
```text
Understood, but a "hard block" on a PR sends a pretty clear message to us that says otherwise :)
```

Cross-team help request (slightly formal, leaning formal):
```text
Hello @<team>,

I recently merged <PR link> to collect some client info from the server.
With the changes:
1. It's fully released in prod
2. The switcher is ON for logging
3. The endpoint is receiving traffic

However, no logs are showing up.
Could you help with this?
```

## Formal (external or customer-relayable)

```text
Hi <Name>, thanks for flagging this.
The email is sent because the certificate in their SSO config has expired, and we send a reminder every week until it's replaced.
SSO still works in the meantime.

Could the customer upload a new signing certificate in their SSO settings?
The emails will then stop.
Please let us know if anything is unclear.
```
