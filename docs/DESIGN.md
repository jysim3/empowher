---
name: E + A · Front Cover
chosen: 2026-11-24
canvas: https://pcsaur.tail7a7f12.ts.net/empowher/design-directions/#pick
colors:
  ground: "#fbf8f6"
  surface: "#ffffff"
  ink: "#1b1217"
  ink-muted: "#5f5158"
  ink-faint: "#a3979d"      # disabled controls only
  line: "#d9cfd3"
  line-strong: "#1b1217"    # section openers, nav rule, input underline
  primary: "#b80a66"
  on-primary: "#ffffff"
  link: "#1b1217"           # links are ink with a 2px primary underline
  cover-shadow: "#d9cfd3"   # the flat offset block behind covers; never under text
  cover-scrim: "#1b1217"    # gradient over cover photos, 80% to 0%
  brand-pink: "#e0097f"     # the logo's pink; logo artwork only, never text (4.7:1 on white is too close)
dark: refused
typography:
  scale: { base: 17, ratio: 1.25 }
  display:
    fontFamily: Fraunces
    fontSize: clamp(44px, 6.6vw, 84px)   # override: the headline is the cover line, larger than step 5
    fontWeight: "400"
    lineHeight: "1"
  heading:
    fontFamily: Fraunces
    fontSize: clamp(28px, 3.2vw, 40px)   # override: one size for every section heading
    fontWeight: "400"
    lineHeight: "1.05"
  title:
    fontFamily: Fraunces
    fontSize: 22px
    fontWeight: "600"
    lineHeight: "1.2"
  body:
    fontFamily: Source Sans 3
    fontSize: 17px
    fontWeight: "400"
    lineHeight: "1.6"
  small:
    fontFamily: Source Sans 3
    fontSize: 14px
    fontWeight: "400"
    lineHeight: "1.5"
  label:
    fontFamily: Oswald
    fontSize: 14px
    fontWeight: "500"
    lineHeight: "1.4"
    textTransform: uppercase
    letterSpacing: 0.06em
rounded:
  base: 4px
  multiplier: 0             # square corners everywhere
  pill: 0
  card: 0
  input: 0
  image: 0
spacing:
  unit: 4px
  density: roomy
  gutter: 20px              # phone; 64px from 1024px up
  card-padding: 24px
  section-gap: 64px         # 24px on phone
motion:
  fast: 175ms
  medium: 410ms
  slow: 975ms
  reduce: 200ms
adaptations:
  contrast-more: ink-muted → ink
  pointer-coarse: 44px minimum target
---

# E + A · Front Cover

The site reads like a calm magazine. It was chosen on 2026-11-24 from ten home-page
directions on the canvas above, as the mix of **A · Front Page** (soft white paper, one
serif, hairline rules, pink used sparingly) and **E · Cover Story** (a magazine cover
with a member on it, events as a contents list, the EmpowHER Women row, the magazine
shelf, narrow pink labels). E's beige ground and its second serif were dropped. The
other directions (B · Morning Tea, C · Rise Lead Shine, D · Plum Room, F · Anniversary
Issue, G · Issue 03, H · The Monthly, I · Two-Ink Zine, J · Her Words) stay on the
canvas for reference.

## Brand and style

**Tone.** EmpowHER's own words, unchanged: "Empowering women. Building futures.",
"A safe and supportive space where women can connect, grow, and achieve their dreams
together.", "Join the growing community". Warm and plain. Never corporate jargon, never
invented marketing claims, never emoji in headings.

**The one thing to remember.** The cover: a portrait of a real member with the
EmpowHER masthead over it, sitting beside the headline. Nothing else on a page is
allowed to be as loud as the cover, and there is one cover per page at most.

**Motifs.** Three, all typographic: (1) the flat offset block behind covers and
magazine issues; (2) big serif date numerals with a narrow pink month label; (3) the
2px pink underline under text links. No icons where a word works.

## Colors

The palette is A's paper and ink with the brand pink darkened until it passes for text.

- **Ground** `#fbf8f6`: the page. **Surface** `#ffffff`: form fields and any raised panel.
- **Primary** `#b80a66`: the one filled button, labels, the italic half of the headline,
  link underlines. 6.07:1 on ground, 6.42:1 on surface; white on it 6.42:1. The logo's
  own pink `#e0097f` was rejected for text.
- **Ink** `#1b1217` (17.34:1 on ground). **Ink-muted** `#5f5158` (7.08:1 on ground).
- **Line** `#d9cfd3` between rows and sections; **line-strong** (ink) opens a list or a
  section and underlines inputs.
- Text on cover photos is white over the `cover-scrim` gradient only; the pink pill on a
  cover is white on primary.
- Contrast is checked, not eyeballed: any new text colour gets the WCAG ratio computed
  against every surface it sits on before it enters this table.

No gradients except the cover scrim. Dark mode is refused: the look is print on paper.

## Typography

- **Fraunces** (variable, SIL OFL): headlines, section headings, names, dates, prices,
  quotes. Italic in primary for the second half of the home headline and for quotes.
  Never below 16px, never uppercase.
- **Source Sans 3** (variable, SIL OFL): all running text, 400 and 600.
- **Oswald** (SIL OFL): labels only, uppercase, 0.06em tracking, 12 to 18px. Never for
  sentences.
- Fonts are self-hosted through npm packages (`@fontsource-variable/fraunces`,
  `@fontsource-variable/source-sans-3`, `@fontsource/oswald`), with `font-display: swap`
  and fallbacks Georgia, "Helvetica Neue", "Arial Narrow".
- Headings get `text-wrap: balance`; running text stays near 65 characters wide.

## Layout and spacing

One column up to 1280px, 64px side gutter from 1024px, 20px on phones. Sections are
separated by a hairline and 64px (24px on phones), never by cards or tinted bands.

- **Hero** (home): two columns from 900px. Left: label, display headline, lede, one
  filled "Join now" button and one underlined "Learn more" link, then the three
  highlights strip. Right: the cover, 420px wide, 3:4, with the offset block. On phones
  the cover drops below the buttons at full width.
- **Cover**: photo 3:4 with `object-fit: cover`; scrim top and bottom; masthead
  "EmpowHER" in Fraunces centred at the top with a ruled label under it; bottom-left a
  pink pill, a cover line in Oswald and the person's name and role.
- **Lists** (events, plans on phones): rows with dividers, opened by an ink rule. Event
  rows are date numeral, title and place, arrow.
- **Buttons**: one filled primary per screen (Oswald, uppercase, 12px by 22px padding,
  square). Every other action is an underlined link.
- **Inputs**: no box; ink underline, 8px vertical padding, placeholder in ink-muted.
- **Portrait row**: five across on desktop, a horizontal scroller on phones; 3:4
  photos, name in Fraunces, role in small ink-muted.
- **Magazine shelf**: real issue covers at 190px with the offset block.
- **Focus**: 2px solid primary outline, 3px offset.

## Screens

| Screen | Notes |
| --- | --- |
| `/` | Hero with cover, events (next three), EmpowHER Women row, magazine shelf, membership plans, quote and newsletter. Primary action: Join now. |
| `/events`, `/events/[slug]` | Contents-style list; an event page leads with the date numeral and title, one "Register" button linking to the Wix event page. |
| `/membership` | The three plans as columns opened by an ink rule; each "Join" links to the Wix plan checkout. |
| `/women`, `/women/[slug]` | Portrait grid; a profile is a cover-style portrait plus her details. |
| `/magazine`, `/blog`, `/about`, others | Text pages in the body measure with hairline section breaks. |

## Assets

- `src/assets/`: photos copied from the current site (`reference/original-site/`).
  Portraits are cropped 3:4, group photos 3:2. Served through Astro's image pipeline.
- The logo is only available as a CMYK JPEG in a circle; a clean SVG is an open question
  for the owner. Until then the wordmark is set in type.

## Do not

- A card per list item. Lists are rows with dividers on one surface.
- A badge for anything but a count or a fixed state.
- Status colours for decoration, or the primary colour for status.
- A literal colour, size or spacing value in page code; use the theme tokens.
- Rounded corners, drop shadows with blur, gradients (other than the cover scrim).
- A second filled button on a screen, or pink as a background area.
- A second serif, or Oswald for anything longer than a label.
- Stock photos: only EmpowHER's own photos of real members and events.
