---
name: design
description: Choose or extend the app's look from a published page of rendered screens (the canvas) before building screens. Use when the user types /design, asks for "styles to choose from", "designs to look through", a restyle, or when a new screen has no entry in docs/DESIGN.md yet. First run picks a direction from the catalog and writes docs/DESIGN.md; later runs render new screens against the chosen tokens.
---

# Design

The user picks from pictures, not adjectives. Procedure and rules live in
`~/Documents/sourdough/concepts/design-directions.md`; this
skill is the per-repo runbook. The chosen system lives in `docs/DESIGN.md`
(frontmatter = tokens, prose = rules).

The canvas is a local page, slug `design`: its shape, the page rules and the check are in
`~/Documents/sourdough/concepts/local-page.md`. Publish it with
`~/Documents/reports/publish-page.sh empowher design <source-folder> <shots-dir>`.
Canvas: `https://pcsaur.tail7a7f12.ts.net/empowher/design-directions/`.

## First run — choose a direction

1. **Read the brief**: `docs/PRODUCT_SPEC.md`, the interview answers, any image the user
   offered, and the persona round's `SYNTHESIS.md` for this feature when there is one
   (`docs/design/<feature>/`). Note the real strings to render: names, date, the first
   screen's copy, and the words the persona agents used for buttons and menus.
2. **Pick 3–4 directions** from the sourdough catalog
   (`~/Documents/sourdough/catalog/design-directions.md`) that fit the brief; write a
   bespoke entry in the catalog's format when none fits. Do not show the whole catalog.
3. **Render them side by side** as a new section at the top of the canvas: one
   artboard per direction at phone width, the app's real content, the user's image in
   every hero when there is one.
4. **Publish, check, then ask.** Publish the canvas, Read the screenshots and fix what
   they show. Then ask for the pick (`AskUserQuestion`, one question, the directions by
   the names on the page with one-line descriptions, the canvas link in the message).
   Apply the user's corrections to the winning artboard only, add the key flow screen
   for it, and publish again.
5. **Compute contrast** for every text colour on every surface it sits on (WCAG
   relative luminance; a tiny script, not a guess), in both modes when the direction
   has a `dark` set. `ink-faint` is for disabled controls only and never carries content. Darken until ≥ 4.5:1 for text,
   record the ratios and any rejected first pick.
6. **Write `docs/DESIGN.md`** from
   `~/Documents/sourdough/templates/DESIGN.md.template`: tokens
   in the frontmatter, the rules in prose, the per-screen table, the Do-not list, the
   canvas link. Fill `https://pcsaur.tail7a7f12.ts.net/empowher/design-directions/` above in this skill in the same commit.
7. **Record the decision** in `docs/DECISIONS.md`: the chosen name, the rejected names,
   the hero choice, the date.
8. **Then** install fonts and the hero asset, move tokens into the app's theme file
   (colours, the `dark` set when there is one, `motion` and `adaptations` too), and
   build the first screens. Screen code reads the theme file; no literal colours or
   spacing. Never build screens before step 7.

## Later runs — a new screen or a restyle

1. Read `docs/DESIGN.md` first; the tokens and refusals are binding.
2. Render the new screen as a new section at the top of the canvas using the chosen
   direction (not a new direction), the real content of the screen, and the requirements
   from the persona round's `SYNTHESIS.md` when the repo runs persona rounds. Where the
   screen has more than one reasonable layout or component, render each as its own named
   artboard.
3. Publish, Read the screenshots, send the link. With one artboard the user confirms or
   corrects it; with several, ask for the pick by name. Add any new component's spec to
   the doc in the same commit as the screen.
4. A restyle request ("make it darker", "less cute") re-runs the first-run steps 2–7
   with the current direction as one of the candidates; the doc is rewritten, not
   patched.

## Rules

- Every design choice is made from the published canvas: the page exists, its
  screenshots are Read and the link is sent before the question is asked. A choice the
  user is asked to make from words alone is rendered first.
- Real content on every artboard; the user's own image in every hero.
- Names stay: the direction's name is used in the doc, the decisions log, the canvas
  and conversation. Letters alone get confused.
- Contrast is computed before a colour enters the doc. Decoration-only colours are
  labelled "never under text".
- The doc's frontmatter is the token source; the app's theme file mirrors it and a
  reviewer checks they match.
- The losing directions stay on the canvas; nothing is deleted.
