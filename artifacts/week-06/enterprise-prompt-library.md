# Enterprise Prompt Library

A curated set of ready-to-use AI prompts for common business scenarios, organized by function. Each prompt explains what it's for, when to reach for it, and includes a real example you can copy and adapt.

## How to use this library

- Replace anything in `[brackets]` with your own details before running the prompt.
- Treat every example as a starting point, not a final answer. Add or remove constraints based on your actual situation.
- The more specific the input you give (real numbers, real names, real constraints), the more useful the output will be. Vague inputs produce vague, generic answers.
- If the first response isn't quite right, don't start over. Tell the AI what's wrong and ask it to revise ("make this shorter," "this tone is too casual," "add a section on risk").

---

## Table of Contents

1. [Sales & Business Development](#1-sales--business-development)
2. [Customer Support & Success](#2-customer-support--success)
3. [Marketing & Content](#3-marketing--content)
4. [HR & Recruiting](#4-hr--recruiting)
5. [Finance & Reporting](#5-finance--reporting)
6. [Legal & Compliance](#6-legal--compliance)
7. [Data Analysis & Insights](#7-data-analysis--insights)
8. [Meetings & Internal Communication](#8-meetings--internal-communication)
9. [Strategic Planning](#9-strategic-planning)
10. [Project Management](#10-project-management)

---

## 1. Sales & Business Development

### Prompt: Cold Outreach Email

**Purpose:** Writes a short, personalized first-touch email to a prospect, instead of a generic template that sounds like every other sales email in their inbox.

**When to use:** Before reaching out to a new lead, especially one you've researched a bit (their company, their role, a recent event).

**Example prompt:**
```
Write a cold outreach email to [prospect name], [title] at [company].
Context: [1-2 sentences about their company, a recent event, or a pain
point you believe they have]. I'm reaching out because [your product/
service] helps companies like theirs [specific benefit]. Keep it under
120 words, no jargon, one clear call to action, and don't open with
"I hope this email finds you well."
```

**What you'll get:** A short, specific email with one ask (a 15-minute call, a reply, a resource). Not a wall of text pitching every feature you have.

---

### Prompt: Discovery Call Question List

**Purpose:** Builds a list of questions to ask on a first sales call, so you spend the call learning about the prospect's actual problem instead of pitching too early.

**When to use:** Before any first call with a new prospect, especially in an unfamiliar industry.

**Example prompt:**
```
I have a discovery call with [prospect role] at a [industry] company.
We sell [product/service]. Give me 8-10 open-ended discovery questions,
grouped into: their current process, what's not working, who else is
involved in this decision, and budget/timeline signals. Avoid yes/no
questions.
```

**What you'll get:** A structured question set you can print or keep on a second screen, organized so the call naturally builds toward a real picture of the buyer's situation.

---

## 2. Customer Support & Success

### Prompt: Triage and Draft a Response to a Customer Complaint

**Purpose:** Reads a raw, sometimes emotional customer message and turns it into (1) a quick read on what's actually being asked for, and (2) a calm, useful draft reply.

**When to use:** Any time a support ticket, email, or review needs a human-quality response fast, especially an angry or confused one.

**Example prompt:**
```
Here is a customer message: "[paste the message]"

1. Summarize in one sentence what they actually want resolved.
2. Note their emotional tone (frustrated, confused, just informational).
3. Draft a reply that acknowledges the issue, doesn't over-apologize,
   states what we'll do next, and gives a realistic timeframe. Our
   policy: [insert relevant policy, e.g. refund window, escalation
   path].
```

**What you'll get:** A reply you can send with light editing, plus a one-line internal summary useful for tracking or handing off to a manager.

---

### Prompt: Turn a Support Pattern into a Help Center Article

**Purpose:** Converts a recurring support question (the kind your team answers five times a week) into a self-service article, so customers can solve it themselves next time.

**When to use:** When you notice the same question coming up repeatedly in tickets or chats.

**Example prompt:**
```
Our support team gets this question often: "[describe the recurring
question]." Here's how we currently answer it: "[paste a typical
answer]." Write a help center article: a clear title, a one-sentence
summary, numbered steps if it's a how-to, and a short "still stuck?"
section pointing to [contact method]. Write for someone non-technical.
```

**What you'll get:** A publish-ready article that reduces repeat ticket volume, in the voice of a helpful person, not a manual.

---

## 3. Marketing & Content

### Prompt: Turn One Idea into Multiple Formats

**Purpose:** Takes a single piece of content (a blog post, a webinar, a customer story) and repurposes it into shorter formats for different channels, so one piece of work produces a week of content instead of one post.

**When to use:** Right after you've published or recorded something substantial.

**Example prompt:**
```
Here is a [blog post/webinar transcript/case study]: "[paste content
or a detailed summary]."

Turn this into:
1. A 3-post LinkedIn series (short, one idea per post)
2. A 5-tweet thread
3. A 100-word email teaser with one link
Keep the core insight intact in every format. Match a [confident but
not salesy] tone.
```

**What you'll get:** Draft copy for each channel, ready for light editing and your own voice pass, not a wholesale rewrite you have to do from scratch.

---

### Prompt: Competitive Positioning Snapshot

**Purpose:** Helps you write clear, honest messaging about how your product compares to a competitor, without resorting to vague marketing-speak or unsupported claims.

**When to use:** Building a comparison page, a sales battlecard, or answering "how are you different from [competitor]" in a deck.

**Example prompt:**
```
We compete with [competitor name]. Here's what we know about them:
"[list known facts, features, pricing you're aware of]." Here's what
we do differently: "[your real differentiators]." Write a short
positioning summary (150 words) that's factual, doesn't disparage
the competitor, and leads with the customer problem we solve better.
Flag anything I should verify before publishing, since you don't have
live data on them.
```

**What you'll get:** Positioning language you can actually stand behind, with a built-in reminder to fact-check competitive claims before they go out the door.

---

## 4. HR & Recruiting

### Prompt: Job Description from a Rough Brief

**Purpose:** Turns a hiring manager's informal notes about a role into a structured, candidate-friendly job description.

**When to use:** Opening a new requisition, especially when the hiring manager's notes are scattered or incomplete.

**Example prompt:**
```
A hiring manager gave me this rough description of a role: "[paste
notes, bullet points, or a voice-to-text transcript]." Write a job
description with: a 2-sentence role summary, "what you'll do" (5-6
bullets), "what you'll bring" (must-haves vs. nice-to-haves, clearly
separated), and a note on [remote/hybrid/onsite] and [salary range if
known]. Avoid buzzwords like "rockstar" or "ninja."
```

**What you'll get:** A posting-ready draft that separates real requirements from wish-list items, which also helps reduce candidates self-selecting out over inflated requirements.

---

### Prompt: Structured Interview Scorecard

**Purpose:** Creates a consistent scorecard so multiple interviewers evaluate a candidate against the same criteria, instead of everyone just going with a gut feeling.

**When to use:** Before a round of interviews for a specific role, especially when several people will interview the same candidate.

**Example prompt:**
```
We're hiring for [role]. Key requirements: [list 3-5 must-haves].
Create an interview scorecard with 4-5 competencies to assess, a
1-2 sentence definition of what a strong answer looks like for each,
and a 1-4 rating scale with a short description of each score level.
```

**What you'll get:** A shared rubric that makes debrief conversations faster and more objective, and gives you a paper trail if a hiring decision is ever questioned.

---

## 5. Finance & Reporting

### Prompt: Plain-Language Summary of a Financial Report

**Purpose:** Translates a dense financial document into a short summary a non-finance audience (executives, board members, other departments) can actually understand.

**When to use:** Before sharing quarterly numbers, a budget variance report, or a financial model with a mixed audience.

**Example prompt:**
```
Here is our [Q3 financial summary / budget variance report]: "[paste
data or key figures]." Write a 150-word summary for a non-finance
audience: what happened, why it happened (in plain terms), and
whether it's a trend to watch or a one-off. No jargon like "YoY" or
"burn multiple" without a one-clause explanation the first time it's
used.
```

**What you'll get:** A cover-note-style summary you can put at the top of a report or read aloud in a meeting, so the numbers land instead of getting skimmed past.

---

### Prompt: Draft Talking Points for a Budget Request

**Purpose:** Helps you make the case for a budget increase or new spend, anticipating the questions a finance reviewer is likely to ask.

**When to use:** Before submitting a budget request or pitching new spend to leadership.

**Example prompt:**
```
I need to request [budget amount] for [initiative]. Here's the
justification: "[explain the need, expected outcome, and any
alternative you considered]." Write talking points for a 10-minute
conversation with a finance reviewer, including the likely pushback
questions they'll ask and a short, honest answer to each.
```

**What you'll get:** A prep sheet that makes you look like you've already thought through the hard questions, because you have.

---

## 6. Legal & Compliance

### Prompt: Plain-Language Explanation of a Contract Clause

**Purpose:** Explains what a specific contract clause actually means and what it obligates you to, in plain English, before you sign or send something back for review.

**When to use:** Reviewing a vendor contract, NDA, or agreement where you want to understand a clause before looping in legal counsel, not instead of them.

**Example prompt:**
```
Here is a clause from a contract: "[paste the exact clause text]."
Explain in plain language: what it requires us to do, what it
restricts us from doing, and what happens if either side breaks it.
Flag anything unusual compared to a standard version of this type of
clause, and note that this is not legal advice.
```

**What you'll get:** A working understanding of the clause so you can ask your actual lawyer sharper, more specific questions, saving review time without replacing legal judgment.

---

### Prompt: Compliance Checklist for a New Process

**Purpose:** Builds a starting checklist of compliance considerations when you're launching something new (a data collection form, a new vendor relationship, a marketing campaign).

**When to use:** Early in planning a new process or feature, before it's built, when changes are still cheap to make.

**Example prompt:**
```
We're building [describe the new process, e.g. "a signup form that
collects email and company name"]. We operate in [region/industry].
List the compliance areas I should have someone review (e.g. data
privacy, consent, industry-specific regulation), phrased as questions
I should be able to answer, not as legal conclusions. Note this is a
starting checklist, not a substitute for actual legal review.
```

**What you'll get:** A question list to bring into a conversation with legal or compliance, so that conversation starts further along instead of from zero.

---

## 7. Data Analysis & Insights

### Prompt: Turn Raw Data into a Narrative

**Purpose:** Takes a table of numbers or a data export and explains what story it's telling, in the kind of language you'd use to brief an executive.

**When to use:** After you've pulled a report or export and need to explain what it means, not just what it says.

**Example prompt:**
```
Here is a data summary: "[paste table, key numbers, or describe the
dataset]." Identify the 3 most important takeaways, in order of
importance. For each, state the finding, why it likely matters, and
one follow-up question worth investigating. Don't just restate the
numbers back to me.
```

**What you'll get:** A short narrative that turns a spreadsheet into something you can say out loud in a meeting, with the "so what" already worked out.

---

### Prompt: Design a Simple Experiment or A/B Test

**Purpose:** Helps you structure a test properly before you run it, so you actually get a clean answer instead of ambiguous results you can't act on.

**When to use:** Before launching an A/B test, pilot, or any change you want to measure the impact of.

**Example prompt:**
```
We want to test whether [change, e.g. "a shorter signup form"]
improves [metric, e.g. "conversion rate"]. Help me design this test:
what to hold constant, what sample size or time period would give a
meaningful result given [rough traffic/volume numbers], and what
result would actually count as a clear win versus noise.
```

**What you'll get:** A test design that protects you from the common trap of declaring a "win" based on a result that isn't actually statistically meaningful.

---

## 8. Meetings & Internal Communication

### Prompt: Meeting Notes to Action Items

**Purpose:** Converts messy meeting notes or a transcript into a clean summary with clear owners and deadlines, so decisions don't get lost.

**When to use:** Right after any meeting where decisions were made or tasks were assigned.

**Example prompt:**
```
Here are my raw notes from a meeting: "[paste notes or transcript]."
Turn this into: a 3-sentence summary of what the meeting was about,
a list of decisions made, and a table of action items with owner and
deadline (mark "unclear" if either wasn't stated explicitly).
```

**What you'll get:** A shareable recap that makes it obvious who owns what next, and honestly flags anything that was left ambiguous instead of guessing.

---

### Prompt: Difficult Message, Said Clearly and Kindly

**Purpose:** Helps you write a message you're dreading (delivering bad news, pushing back on a request, setting a boundary) in a way that's direct but not harsh.

**When to use:** Before sending a message you've been putting off because you're not sure how to phrase it.

**Example prompt:**
```
I need to tell [recipient, e.g. "a client" / "my manager" / "a
teammate"] that [the difficult thing, e.g. "we're missing the
deadline" / "I can't take on this project"]. Here's the context:
"[explain the situation honestly]." Draft a message that's direct,
takes appropriate ownership, and doesn't over-apologize or bury the
point in softening language.
```

**What you'll get:** A message that respects the reader's time and doesn't dodge the point, which usually lands better than a message that's been hedged into vagueness.

---

## 9. Strategic Planning

### Prompt: Stress-Test a Business Decision

**Purpose:** Plays devil's advocate on a decision you're leaning toward, surfacing risks and blind spots before you commit, instead of after.

**When to use:** Before finalizing a significant decision (a new market, a pricing change, a major hire), when you want a real challenge, not agreement.

**Example prompt:**
```
We're considering [the decision]. Our reasoning is: "[explain your
current thinking]." Push back on this as a skeptical advisor would:
what's the strongest argument against this decision, what assumption
are we most likely wrong about, and what would have to be true for
this to fail?
```

**What you'll get:** The kind of pushback a good board member or advisor would give you, surfaced before the decision is locked in rather than in a postmortem.

---

### Prompt: SWOT Analysis from Real Inputs

**Purpose:** Structures a strengths/weaknesses/opportunities/threats analysis from what you actually know, rather than generic categories that could apply to any company.

**When to use:** Quarterly or annual planning, or when evaluating a new strategic direction.

**Example prompt:**
```
Here's what I know about our position: "[describe your product,
market, recent wins and losses, competitive landscape]." Build a SWOT
analysis with 3-4 specific points per quadrant, each grounded in
something I actually told you, not a generic business platitude.
Then suggest the single highest-leverage opportunity to act on first.
```

**What you'll get:** A SWOT that's actually specific to your situation, plus a forced prioritization instead of a flat list you still have to figure out how to act on.

---

## 10. Project Management

### Prompt: Break a Vague Goal into a Real Plan

**Purpose:** Takes a loosely defined objective ("improve onboarding," "launch in Q2") and breaks it into concrete, sequenced steps with dependencies called out.

**When to use:** At the start of a new initiative, before work gets assigned, when the goal is clear but the path isn't.

**Example prompt:**
```
The goal is: "[state the goal]." Constraints: [team size, deadline,
budget, or other limits]. Break this into phases, then concrete tasks
within each phase. Call out which tasks depend on others finishing
first, and flag anything that looks like a risk to the timeline.
```

**What you'll get:** A first-draft project plan you can review and adjust with your team, instead of starting from a blank page.

---

### Prompt: Status Update That Doesn't Bury the Lead

**Purpose:** Writes a project status update that leads with what matters (are we on track, what's blocking us) instead of a chronological list of everything that happened.

**When to use:** Weekly or biweekly project updates to stakeholders who don't need every detail, just the ones that affect them.

**Example prompt:**
```
Here's what happened on [project] this week: "[list raw updates,
completed tasks, blockers]." Write a status update: one line on
overall status (on track / at risk / blocked), 2-3 bullets on what
moved forward, any blockers with what's needed to resolve them, and
what's coming next week. Keep it under 150 words.
```

**What you'll get:** An update a busy stakeholder can read in 20 seconds and still know exactly where things stand, instead of skimming a wall of text for the one line that matters.

---

## A note on using AI prompts responsibly

Treat every output from these prompts as a first draft, not a final answer, especially for anything involving legal, financial, HR, or compliance decisions, where a qualified professional should review before you act. Always fact-check specific claims, numbers, or competitive information before publishing or sending externally. The value of these prompts is speed on the first draft, not replacing your own judgment on the final one.
