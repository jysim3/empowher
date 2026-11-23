# Architecture

## Stack

Astro 7.4 static output, strict TypeScript and plain Astro components/CSS. Images are imported from `src/assets/` and processed by Astro; Fraunces, Source Sans 3 and Oswald are self-hosted from installed Fontsource packages. There is no client framework, backend, runtime state or external font request. Wix remains the transaction service during Phase 1.

## Surfaces by route

```text
/                    Home page, built now
/events              Event list, Phase 1
/events/[slug]       Event detail with Wix registration link, Phase 1
/women               EmpowHER Women directory, Phase 1
/women/[slug]        Woman profile, Phase 1
/membership          Membership with Wix checkout links, Phase 1
/magazine            Magazine shelf, Phase 1
/blog                 Blog list, Phase 1
/blog/[slug]          Blog post, Phase 1
/about and others     Committee, speakers, sponsors, FAQ, contact and hotline, Phase 1
```

Only `/` is implemented now. Future-route header links point to the corresponding live Wix page until the local route exists.

## Content layout

This is a single-tenant site. Home events, members, plans and issues are typed in `src/data/home.ts`; images live in `src/assets/`. As route families are built, page-shaped Markdown will move into Astro content collections with schemas in `src/content.config.ts`.

| Data | Shape | Source of truth |
|---|---|---|
| `events` | `Event[]` | Typed home data; later event collection |
| `members` | `Member[]` | Typed home data; later women collection |
| `plans` | `Plan[]` | Typed home data and Wix checkout |
| `issues` | `Issue[]` | Typed home data; later magazine collection |

All content is public and build-time only. Repository write access controls editing; there is no browser write path.

## Local development

Astro requires Node 22.23.4 or newer. Prefix every command with the pinned Node path:

```sh
PATH=/home/jysim/.nvm/versions/node/v22.23.5/bin:$PATH npm run dev
PATH=/home/jysim/.nvm/versions/node/v22.23.5/bin:$PATH npm run check
PATH=/home/jysim/.nvm/versions/node/v22.23.5/bin:$PATH npm run build
PATH=/home/jysim/.nvm/versions/node/v22.23.5/bin:$PATH npm run preview
PATH=/home/jysim/.nvm/versions/node/v22.23.5/bin:$PATH npm run validate
```

`validate` checks types/content and then produces `dist/`. Deployment, domain changes, redirects and production Wix configuration belong to the owner.

## Later-phase boundary

Transactions stay behind outbound HTTPS links, so the static information architecture does not depend on a future provider. Replacing Wix requires separate decisions on identity, privacy, payments, refunds, migration and administration.
