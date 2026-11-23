# EmpowHER Sydney: product spec

A static public website for EmpowHER Sydney Inc, helping women discover the network, its people, events and resources while existing Wix services continue to handle transactions.

| Surface | Who | How they get it | Phase |
|---|---|---|---|
| Public website | Visitors and prospective members | Public web URL, no sign-in | 1 |
| Wix checkout and forms | Event attendees, members and shoppers | Links from the public website | 1 |
| Managed transactions and accounts | Members and administrators | Future authenticated service | Later |

The public site is useful without an account. Until a later-phase replacement is approved, every transactional action hands off clearly to the existing Wix service.

## Feature map (parity with empowhersydney.com)

### Phase 1: pages first

- **Home**: mission, current event links, EmpowHER Women, magazine, memberships and newsletter prompt.
- **Events (built)**: list and detail pages for all 72 captured coffee meetups, networking, business workshops and showcases, wellness and fitness activities, International Women's Day, R U OK? programs, community fundraisers, Dress 4 Success, galleries and recurring classes. Registration continues on each matching Wix event page.
- **Blog (built)**: all 11 captured posts, a newest-first post list, six category pages, and per-post tag labels.
- **EmpowHER Women (built)**: directory and individual profiles for the six featured women, with public contact and business details from their current profiles.
- **Magazine (built)**: issue shelf and reading links for the existing digital issues, plus the announced next issue date.
- **Organisation (built)**: About, committee/Our Team, speakers, sponsors, FAQ, contact, help hotline, women's health and get involved.
- **Programs and resources**: Dress 4 Success information and galleries, Coffee Meetup, Fitness Buddy, courses/workshops, Empowering Showcase, surveys and public campaign pages.
- **Membership (built)**: explain Bronze, Silver and Gold · Biz plans and every current benefit; Join links to Wix checkout.
- **Navigation continuity**: unbuilt Phase 1 routes link to their matching current-site URL until migrated.

### Later: transactions and participation tools

- **Committee editing**: a git-based editing screen creates and updates one content file per event, member, plan or magazine issue, then rebuilds the static site. Open questions: which editor to use and how committee members sign in; GitHub Pages has no server, so authentication and repository writes require an external service.
- **Event registration**: native registration, capacity, confirmation and attendee workflows.
- **Membership payments**: native checkout, renewals and plan management.
- **Shop**: product catalogue, cart, checkout and orders.
- **Forms**: contact, inquiry, survey, volunteer and campaign registration forms.
- **Member accounts**: sign-in, profile, subscription and purchase history after privacy requirements are defined.

### Kept on Wix in Phase 1

- Event registration, membership checkout, shop, forms and member accounts — public pages deliver value without taking on payment, identity or operational risk.

## Non-goals

- No backend, database, member login, payment processing or administration interface in Phase 1.
- No redesign of Wix transactional pages.
- No invented programs, claims, testimonials or stock photography.
- No dark mode and no multi-organisation support.

## Open questions for the owner

- Can a clean SVG logo be supplied? Default: use the typographic wordmark.
- Which git-based editor should the committee use, and how should members sign in? Default: keep direct repository editing during the build; do not add credentials or an editor until the external authentication flow is approved.
- Which domain and hosting provider will be used? Default: prepare a provider-neutral static build.
- Do we have permission to reuse every captured photo? Default: publish only images whose permission is confirmed.
- What is the approved redirect map from old URLs? Default: preserve meaningful slugs and document every redirect before launch.
