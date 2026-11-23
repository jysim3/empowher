import { defineCollection } from "astro:content";
import { glob } from "astro/loaders";
import { z } from "astro/zod";

const isoDateTime = z.coerce.date();
const webUrl = z.url();
const issueMonth = z.string().regex(/^\d{4}-(0[1-9]|1[0-2])$/);

const events = defineCollection({
  loader: glob({ pattern: "**/*.md", base: "./src/content/events" }),
  schema: ({ image }) =>
    z
      .object({
        title: z.string().min(1),
        start: isoDateTime.optional(),
        end: isoDateTime.optional(),
        dateTbd: z.boolean().optional(),
        venue: z.string().min(1),
        locality: z.string().min(1),
        address: z.string().min(1),
        summary: z.string().min(1),
        registrationUrl: webUrl,
        image: image().optional(),
        sourceImage: webUrl.optional(),
        imageAlt: z.string().min(1).optional(),
        status: z
          .enum(["scheduled", "cancelled", "sold-out", "closed"])
          .optional(),
      })
      .strict()
      .refine((event) => Boolean(event.start) !== Boolean(event.dateTbd), {
        message: "An event needs either a start date or dateTbd: true",
      }),
});

const members = defineCollection({
  loader: glob({ pattern: "**/*.md", base: "./src/content/members" }),
  schema: ({ image }) =>
    z
      .object({
        name: z.string().min(1),
        role: z.string().min(1),
        profileTitle: z.string().min(1).optional(),
        businessName: z.string().min(1).optional(),
        email: z.email().optional(),
        phone: z.string().min(1).optional(),
        address: z.string().min(1).optional(),
        languages: z.string().min(1).optional(),
        portrait: image().optional(),
        banner: image().optional(),
        sourceUrl: webUrl,
        sourcePortrait: webUrl,
        portraitAlt: z.string().min(1),
        sourceBanner: webUrl.optional(),
        bannerAlt: z.string().min(1).optional(),
        links: z
          .array(z.object({ label: z.string().min(1), url: webUrl }).strict())
          .optional(),
        featuredOnHome: z.boolean(),
        order: z.number().int().positive(),
      })
      .strict(),
});

const plans = defineCollection({
  loader: glob({ pattern: "**/*.json", base: "./src/content/plans" }),
  schema: z
    .object({
      name: z.string().min(1),
      yearlyPrice: z.number().nonnegative(),
      summary: z.string().min(1),
      description: z.string().min(1),
      summaryBenefits: z.array(z.string().min(1)).min(1),
      benefits: z.array(z.string().min(1)).min(1),
      checkoutUrl: webUrl,
      order: z.number().int().positive(),
    })
    .strict(),
});

const issues = defineCollection({
  loader: glob({ pattern: "**/*.json", base: "./src/content/issues" }),
  schema: ({ image }) =>
    z
      .object({
        title: z.string().min(1),
        issueNumber: z.number().int().positive(),
        date: issueMonth.optional(),
        cover: image(),
        issuuUrl: webUrl,
      })
      .strict(),
});

const pages = defineCollection({
  loader: glob({ pattern: "**/*.md", base: "./src/content/pages" }),
  schema: ({ image }) =>
    z
      .object({
        title: z.string().min(1),
        lede: z.string().min(1),
        sourceUrl: webUrl,
        sourceImage: webUrl.optional(),
        image: image().optional(),
      })
      .strict(),
});

const committee = defineCollection({
  loader: glob({ pattern: "**/*.md", base: "./src/content/committee" }),
  schema: ({ image }) =>
    z
      .object({
        name: z.string().min(1),
        role: z.string().min(1),
        order: z.number().int().positive(),
        photo: image().optional(),
        sourceImage: webUrl.optional(),
        photoAlt: z.string().min(1).optional(),
      })
      .strict(),
});

const speakers = defineCollection({
  loader: glob({ pattern: "**/*.md", base: "./src/content/speakers" }),
  schema: ({ image }) =>
    z
      .object({
        name: z.string().min(1),
        title: z.string().min(1),
        location: z.string().min(1).optional(),
        order: z.number().int().positive(),
        photo: image().optional(),
        sourceImage: webUrl.optional(),
        photoAlt: z.string().min(1).optional(),
      })
      .strict(),
});

const sponsors = defineCollection({
  loader: glob({ pattern: "**/*.md", base: "./src/content/sponsors" }),
  schema: ({ image }) =>
    z
      .object({
        name: z.string().min(1),
        tier: z.string().min(1).optional(),
        order: z.number().int().positive(),
        logo: image().optional(),
        sourceImage: webUrl.optional(),
        logoAlt: z.string().min(1),
        link: webUrl.optional(),
      })
      .strict(),
});

const faq = defineCollection({
  loader: glob({ pattern: "**/*.md", base: "./src/content/faq" }),
  schema: z
    .object({
      question: z.string().min(1),
      category: z.string().min(1),
      order: z.number().int().positive(),
    })
    .strict(),
});

const hotlines = defineCollection({
  loader: glob({ pattern: "**/*.md", base: "./src/content/hotlines" }),
  schema: z
    .object({
      name: z.string().min(1),
      description: z.string().min(1).optional(),
      phoneNumbers: z.array(z.string().min(1)).min(1),
      hours: z.string().min(1).optional(),
      link: webUrl.optional(),
      order: z.number().int().positive(),
    })
    .strict(),
});

const posts = defineCollection({
  loader: glob({ pattern: "**/*.md", base: "./src/content/posts" }),
  schema: ({ image }) =>
    z.object({
      title: z.string().min(1),
      published: isoDateTime,
      updated: isoDateTime.optional(),
      excerpt: z.string().min(1),
      categories: z.array(z.string().min(1)),
      tags: z.array(z.string().min(1)),
      author: z.string().min(1).optional(),
      coverImage: image().optional(),
      sourceImage: webUrl.optional(),
      imageAlt: z.string().min(1).optional(),
      sourceUrl: webUrl,
    }).strict(),
});

const programs = defineCollection({
  loader: glob({ pattern: "**/*.md", base: "./src/content/programs" }),
  schema: ({ image }) =>
    z.object({
      title: z.string().min(1),
      label: z.string().min(1),
      lede: z.string().min(1),
      order: z.number().int().positive(),
      sourceUrls: z.array(webUrl).min(1),
      hero: image().optional(),
      relatedEvents: z.array(z.string().min(1)).max(6).optional(),
      gallery: z.string().min(1).optional(),
      details: z.array(z.object({ label: z.string().min(1), value: z.string().min(1), url: z.string().min(1).optional() }).strict()).optional(),
      structuredSections: z.array(z.object({
        title: z.string().min(1),
        items: z.array(z.object({ name: z.string().min(1), description: z.string().min(1), url: z.string().min(1).optional() }).strict()).min(1),
      }).strict()).optional(),
      schedule: z.array(z.object({ time: z.string().min(1), description: z.string().min(1) }).strict()).optional(),
    }).strict(),
});

const galleries = defineCollection({
  loader: glob({ pattern: "**/*.md", base: "./src/content/galleries" }),
  schema: ({ image }) =>
    z.object({
      title: z.string().min(1),
      date: z.string().regex(/^\d{4}(?:-(?:0[1-9]|1[0-2]))?$/).optional(),
      order: z.number().int().positive(),
      sourceUrls: z.array(webUrl).min(1),
      photos: z.array(z.object({
        sourceImage: webUrl,
        image: image().optional(),
        alt: z.string().min(1),
      }).strict()),
    }).strict(),
});

export const collections = {
  events,
  members,
  plans,
  issues,
  pages,
  committee,
  speakers,
  sponsors,
  faq,
  hotlines,
  posts,
  programs,
  galleries,
};
