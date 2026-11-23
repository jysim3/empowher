# Rewrite chat

For a session whose prompt starts with `[persona rewrite]`. It is started when a pattern is
due (by the chat hook through tools/persona/adapters/tmux.py). It is the only thing
that edits a page under `docs/personas/`.

**Started by hand.** On a machine that cannot open the chat by itself, the owner opens one
and says `persona rewrite`. Follow the same steps. If `due` prints `(nothing due)`, say so
in one line and stop. If you are not in a worktree or on a branch, make one first, the way
this repo's rules say.

You are the better model the owner asked for: investigate, then rewrite. You are in a worktree.

1. **Read** `docs/personas/README.md`, then `python3 tools/persona/adapters/tmux.py pending` and the same command with
   `due`. Work on the personas that have something due; read each one's page.
2. **Investigate each due pattern.** A log line with a `sid` came from a chat: read that
   chat around the remark (the Claude Code transcript for the recorded session id) to
   see what the person was looking at and whether the small model read it right. Drop a
   line it got wrong; say so in your reply.
   - A line marked `relayed` is the owner passing on what the person said. Read it the same way.
   - A line marked `handed over` came from the app's own log as a pattern sentence and its
     days. The words behind it stay on the app's side: do not go looking for them, and do
     not ask for a way in. Work from the sentence.
3. **Rewrite the page.** The analysis is the page; never just append a quote.
   - **A new pattern or observation with 3 days** becomes a trait: a short analysis paragraph
     in "you" form, with the remarks as examples (at most 5). Delete the observation. A
     handed-over pattern has no words to quote: its examples are dated lines such as
     "Asked for this on the Change page (2026-11-20, 11-21, 11-22)".
   - **A trait gone against on 3 days** is rewritten to fit, or removed. If the remarks split
     by scope (phone and desk, one screen and all screens), the trait carries the scope.
   - **A trait marked "(guess)" that now has an example** loses the mark and gains the example.
   - **A `direct` line** (a `DECISION`) goes into "Settled facts" or "Already turned down",
     replacing what it reverses.
   - **A pending pattern below 3 days** becomes an Observations line with its dates, so the
     count carries on from the page. A line against a trait below 3 days becomes an
     `Against T<n>` line there.
   - **A trait seen again** changes nothing, unless the words show it better than an example
     already there: then swap.
   - Add each remark you used to "What you have told us", newest first. For a group persona,
     keep the made-up label for who said it; never a name.
   - Strip anything private before it reaches the page (names, addresses, tokens, secrets and anything not already public on the site).
4. **Commit** the pages on their own (nothing but `docs/personas/`), land the commit with
   `a parent-session squash-merge; the commit-footer hook exempts docs/personas-only commits`, then run
   `python3 tools/persona/adapters/tmux.py pending` with `folded` in place of `pending`.
5. **Reply in a few lines**: which traits were added, rewritten or removed, for which
   persona, with the remark behind each, and which already-built screens now look wrong for
   this person (those become tracker items; they are not fixed silently). Never ask anyone
   to read, check or approve a page.
6. **If the owner says "undo"** (or "revert", "take that back") in this chat: `git revert`
   your page commit, land it the same way, and say in one line that the page is back as it
   was. Leave the log lines folded, so the same remarks do not start the same rewrite again.
