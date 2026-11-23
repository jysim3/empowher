import { defineCollection } from 'astro:content';
import { glob } from 'astro/loaders';
import { z } from 'astro/zod';

const isoDateTime = z.coerce.date();
const webUrl = z.url();
const issueMonth = z.string().regex(/^\d{4}-(0[1-9]|1[0-2])$/);

const events = defineCollection({
  loader: glob({ pattern: '**/*.md', base: './src/content/events' }),
  schema: ({ image }) => z.object({
    title: z.string().min(1),
    start: isoDateTime,
    end: isoDateTime.optional(),
    venue: z.string().min(1),
    locality: z.string().min(1),
    summary: z.string().min(1),
    registrationUrl: webUrl,
    image: image().optional(),
    status: z.enum(['scheduled', 'cancelled', 'sold-out', 'closed']).optional(),
  }).strict(),
});

const members = defineCollection({
  loader: glob({ pattern: '**/*.md', base: './src/content/members' }),
  schema: ({ image }) => z.object({
    name: z.string().min(1),
    role: z.string().min(1),
    portrait: image(),
    links: z.array(z.object({ label: z.string().min(1), url: webUrl }).strict()).optional(),
    featuredOnHome: z.boolean(),
    order: z.number().int().positive(),
  }).strict(),
});

const plans = defineCollection({
  loader: glob({ pattern: '**/*.json', base: './src/content/plans' }),
  schema: z.object({
    name: z.string().min(1),
    yearlyPrice: z.number().nonnegative(),
    summary: z.string().min(1),
    benefits: z.array(z.string().min(1)).min(1),
    checkoutUrl: webUrl,
    order: z.number().int().positive(),
  }).strict(),
});

const issues = defineCollection({
  loader: glob({ pattern: '**/*.json', base: './src/content/issues' }),
  schema: ({ image }) => z.object({
    title: z.string().min(1),
    issueNumber: z.number().int().positive(),
    date: issueMonth.optional(),
    cover: image(),
    issuuUrl: webUrl,
  }).strict(),
});

export const collections = { events, members, plans, issues };
