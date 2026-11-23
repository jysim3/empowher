---
name: persona-round
description: The persona round for EmpowHER Sydney - start a persona review with one fresh subagent per affected persona, each playing a person from docs/personas/ and saying in under 200 words whether they would want the change. Every session working on EmpowHER Sydney runs it before proposing, mocking or building ANY change to what a persona sees or does, including a suggestion you thought of yourself, and again on a screenshot of the result. Also load it for "persona round", "persona review", "what would the committee think", and in a session whose prompt starts with "[persona rewrite]" or where the owner says "persona rewrite". Needs on the machine - Claude Code with this repo's hooks trusted, the claude command, python3; optional jig-start. Keeping the pages up to date is NOT a working session's job - code does it.
---

# Persona round

`docs/personas/` holds one page per person or role EmpowHER Sydney is built for, and an index
(`README.md`) with one line each. A page is an analysis of who they are and what they look
for: traits, each with their own words as examples.

**This skill is the round**: you start a persona review with one fresh subagent per persona
the change touches. Every session working on EmpowHER Sydney runs it (the rule is in
`AGENTS.md`, "Changes Get A Persona Round"); it is not optional and not a matter of
noticing. The skill belongs to this project: it lives in this repo's own skills folder.

Keeping the pages true is not your job. Code logs what people say (section 2) and a rewrite
chat folds it in (`rewrite.md`, read it only in a session whose prompt starts with
`[persona rewrite]`, or when the owner says `persona rewrite`).

The round is a guess that saves the person a question. It never replaces their say.

## 1. The quick round (about 2 minutes, one agent per persona)

**When.** Before you propose, mock or build a change to what a persona sees or does. Your
own suggestions count: run the round before you offer one, so you offer fewer and better ones.

**Skip it, and say so in one line** (`Persona round: skipped, <reason>`), for:
- a fix that puts back behaviour the person already had
- a change with nothing to see or do (refactor, test, log, speed)
- the person's exact instruction with no design choice left in it ("remove the Timeline tab")


**Steps.**

1. **Write the request down word for word.** The person's message, the owner's message, or
   for your own idea a plain description with no selling. If there are options, list them
   as A, B, C without saying which you like.
2. **Pick the personas.** Read `docs/personas/README.md`. Take every persona whose "theirs"
   part the change touches. One is the usual case. If none fits, skip the round and say so.
3. **Take a screenshot of today's screen** if the change touches one:
   `chromium --headless --disable-gpu --screenshot=<scratchpad>/screen.png --window-size=390,844 http://localhost:4321`. Save it in the
   scratchpad. Skip this when there is no screen yet.
4. **Get the remarks not on the pages yet**: `python3 tools/persona/adapters/tmux.py pending`.
   If it prints anything but `(nothing waiting)`, save each persona's lines to its own file
   in the scratchpad.
   - **A first line that starts with `REWRITE DUE:`** means a rewrite is due and this
     machine could not open a chat for it. It is not a remark: leave it out of the files,
     and pass it on in step 6. Do not do the rewrite yourself.
5. **Launch one fresh subagent per persona**, all in one message, each pinned to the work
   model. Each gets only: the request, the path of its own page, its pending file if there
   is one, and the screenshot path if any. No code, no plan, no diff, none of your opinion,
   and not another persona's page. Use the prompt below as it is.
6. **Report it in your reply** under a `Persona round` header: one line per persona side by
   side (who, verdict, the one reason), then at most 3 bullets: what you changed because of
   it, any clash, any gap. If step 4 printed `REWRITE DUE:`, add one more line:
   `A persona rewrite is due: open a chat and say "persona rewrite".` Then carry on.

**One agent per persona, one pass.** No files are saved for a quick round.

**The prompt.**

```
You are playing <the persona's title from the index>, a person an app called EmpowHER Sydney
is built for. Read <path to their page> first; it is written to you. <Then read <path to
the pending file>: things you said since the page was written. A DECISION line there beats
the page.> Read nothing else<, except the screenshot at <path>, which shows the app today>.

Someone proposes this change to EmpowHER Sydney:

<the request, word for word; options as A/B/C>

Answer as that person, in the first person, in under 200 words, in exactly this shape:

Verdict: want it | want it with a change | don't want it | can't tell
Because: one or two sentences, in my own way of talking.
I expect: up to 3 steps of what I would see and do.
Would annoy me: up to 3 things.
Traits I used: the ids from the page (T1, T4, ...).
Clashes: any trait, quoted example, settled fact or "turned down" item this goes against, or "none".
Can't tell: what the page does not say and you would have to guess, or "none".

Rules: answer from who this person is, not by matching quotes. Where an analysis and a quoted
example disagree, the example wins. A trait marked "(guess)" is weaker than any example. If
the page does not cover something, put it under "Can't tell"; do not invent a taste. Do not
be polite about a bad idea.
```

**Reading the answers.**

| An agent says | You do |
|---|---|
| want it | Go on. For a go-ahead the owner has not given, the ask stays: the round is not a yes. |
| want it with a change | Make the change in the proposal, and say that you did. |
| don't want it | Your own idea: drop it or reshape it, and say so in one line. The person's or owner's request: do not drop it; tell the owner the clash and ask. |
| a clash with a trait or a settled fact | Never pick a side silently. Name it and ask the owner. |
| can't tell | That is a real question for the owner. Ask it once, short, with the option you would pick. |
| **two personas disagree** | Send it to the owner: both verdicts side by side, one line each, and the option you would pick. Never average them, and never let one persona win because their page is longer. |

**After the build**, when there is a screen to look at: screenshot it, Read it yourself,
then run one more fresh agent per persona with the same prompt plus the new screenshot and
this line added: `This is now built. Verdict: ship | not yet, and what is wrong, ranked.`
At most 2 passes; after that it goes to the owner. The owner still looks at the review
artifact before it lands.

### When the fuller round is still right

Use it for **a new screen, tool or area for a person who cannot be asked cheaply** (their
words arrive relayed, or not at all). A wrong guess there costs a whole build, so it is
worth 15 minutes:

- 2 or more fresh agents per persona, each with a different **scenario**: a moment in the
  person's day (what just arrived, what is due, what went wrong an hour ago), not a feature.
- Each returns what they expect to see and do as steps, their wishes ranked, what would
  send them back to the current public Wix site and the committee’s existing process, the words they would use for buttons, then out of character a builder's
  translation as plain requirements.
- **Save it** under `docs/design/<feature>/`: `BRIEF.md` (the request word for word, what
  exists today), one `persona-<n>-<scenario>.md` per agent, and `SYNTHESIS.md` with three
  lists: agreed by most, splits, clashes with recorded decisions
  (docs/DECISIONS.md, docs/PRODUCT_SPEC.md and docs/DESIGN.md). Design from the synthesis.
- After the build, one fresh agent reviews the screenshots until one says ship; after 3
  rounds without a ship, ask the owner.

For everything else, the quick round. When the person can be asked cheaply (the owner's own
persona), a short question to them beats a fuller round.

## 2. Feedback: code logs it

A session working on a feature does not keep the personas up to date. You do not edit a
page, and you do not log remarks. This is what happens instead:

- **Every remark is offered to the kit** (`tools/persona/core.py`): this repo’s UserPromptSubmit hook runs tools/persona/adapters/tmux.py in the background and discovers the app through docs/personas/kit.json.
- **A small model** reads the index (to say whose remark it is), then that persona's page,
  what the remark replied to and the words, and answers one line: `none`, `trait` (for or
  against `T<n>`), `observation` (for or against `O<n>` or a pending `N<n>`), `new` (a
  pattern nothing covers), or `direct` (a decision about the app). Short go-aheads, pastes,
  briefs and injected text are dropped before the call.
- **The answer is one line in that persona's log**, `.persona-logs/<persona>.jsonl` (ignored by git). The model never edits a page.
- **Relayed words count the same.** What the owner passes on ("they said…") is logged for
  that persona like any other remark.
- **Code counts**: different days per pattern, from the log plus the dates on the page's
  Observations lines. Due means: an observation or new pattern seen on 3 days, a trait gone
  against on 3 days, or 15 remarks waiting.
- **When something is due**, the hook starts a visible persona-update chat; without jig-start, pending and due report REWRITE DUE until the owner opens a chat and says persona rewrite.

**Needs on this machine** (everything else is in this repo, and no other repo or list has
to know about it): Claude Code with this repo's hooks trusted (it asks once after a
clone; until then the round works but remarks are not logged), the `claude` command
signed in (one small model call per remark), and `python3`. Optional: `jig-start`, so the
rewrite chat opens by itself.

What stays with you in a working session:
- If a remark changes what you are building, act on it as you would anyway.
- If it plainly goes against a trait and that changes the build, ask which holds. Otherwise
  say nothing about the persona.

Useful commands: `python3 tools/persona/adapters/tmux.py pending` (waiting remarks), the same with `due` (what has
reached the bar), and with `folded` (mark them done; only a rewrite chat runs this).

## Rules

- **Blind means blind.** An agent that has seen the code, the plan, your view or another
  persona's page is not the person. Start a new one.
- **The person's word beats the round**, every time. A round is never quoted to someone as
  a reason they are wrong.
- **A round's output never edits a page.** Only the person's words and dated decisions do.
- **Analysis first.** A page is a reading of the person with their words as examples. Do
  not let it turn back into a list of quotes or rules.
- **Never ask anyone to read, check or approve a persona page.**
- **Keep it quick.** If a round would take longer than asking the owner one short question,
  ask the question.
- **Private.** No names, numbers, addresses or secrets in a page or in a round's prompt.
  Agents get made-up data only, never private committee information, private files, live data or unpublished work.
- **Only a rewrite chat edits a page.** A working session never does, so parallel sessions
  cannot collide on it.
- The round shapes the request. It does not replace the e2e spec, the review artifact the
  owner looks at, or the independent review of the diff.
