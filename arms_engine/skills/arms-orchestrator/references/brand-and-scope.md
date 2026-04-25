# Brand & Scope Reference

> Read this file when handling project foundation questions, brand context generation, or MVP scoping.

---

## Project Foundation Questions

Ask **all questions together in a single prompt block** — do not split across messages.

### Project Foundation (5.1)

```
1. Primary use case: SaaS · Content/Marketing · Mobile-First · Multi-Purpose
2. Target audience
3. Core features
4. Goal / Monetization model
```

### Brand Context (5.2)

If the current workspace is an **existing project** and brand context is missing, inspect the repository first and draft the initial brand file from real project evidence before asking follow-up questions.
- Infer what you can from package metadata, README content, existing assets, and source structure
- Mark unsupported fields as `TBD`
- Present the inferred draft for correction instead of asking the user to restate what the repo already tells you

If the current workspace is a **new / empty project**, ask the user the following questions together in a single prompt block.

```
5.  Brand name (or working title if unnamed)
6.  Brand personality — pick up to 3 words:
    Bold · Minimal · Playful · Premium · Technical · Warm · Rebellious · Trustworthy · Friendly · Sharp
7.  Closest competitor or reference brand? (URL or name)
8.  What should your brand feel like vs. that reference?
    e.g. "Like Notion but warmer" · "Like Stripe but more human"
9.  Existing brand assets?
    → Logo (Y/N) · Color palette (Y/N) · Typography (Y/N) · Existing site (URL or N)
10. Preferred visual direction: Light · Dark · System default · Undecided
```

After Brand Context, ask for the initial tech stack in the same flow:

```
11. Preferred tech stack:
    [A] Next.js + Supabase + shadcn (Latest)
    [B] Nuxt 4 + Firebase + Nuxt UI (Latest)
    [C] Astro + DaisyUI (Latest)
    [D] Custom
12. Preferred deployment target:
    [1] Vercel
    [2] Docker / VPS
    [3] AWS / GCP
13. Preferred backend / data layer if custom or undecided:
    Supabase · Firebase · Postgres · MySQL · REST API · GraphQL · Custom · Unsure
14. Authentication requirement:
    Email/password · OAuth · Magic link · Anonymous/guest · None yet · Unsure
15. Any hard technical constraints or must-use tools?
    e.g. TypeScript only, Tailwind required, self-hosted only, no Firebase, mobile-first, CMS needed
```

After receiving answers for a new project, or after reviewing repository signals for an existing project:
1. Generate `.arms/BRAND.md` using the canonical ARMS brand schema (see template below).
2. Recommend one primary tech stack with clear justification, then list viable alternatives.
3. Select 3–5 relevant supplemental business prompts (see bank below). → **HALT**
4. Once BRAND.md is approved by the user, **trigger the Media & Design Pipeline** defined in the `arms-orchestrator` SKILL.md:
   - **Step 1 — Logo** (`arms-media-agent` → `.agents/skills/logo-designer/SKILL.md`): Generate HD PNG logo from brand identity
   - **Step 2 — Hero & UI Assets** (`arms-media-agent` → `.agents/skills/nano-banana-pro/SKILL.md`): Generate hero images, textures, or UI illustrations using the approved logo as reference
   - **Step 3 — Frontend Scaffold** (`arms-frontend-agent` → `.agents/skills/frontend-design/SKILL.md`): Build the initial UI shell using approved assets and design tokens
5. After the pipeline completes and all assets are approved, proceed to the Strategic Task Table → **HALT**

If these answers were provided as a follow-up to a previous `init` HALT, treat them as the continuation of the same initialization flow. Do not restart from the beginning or repeat the same question block unless critical information is still missing.

---

## `.arms/BRAND.md` Template

```markdown
# Brand Context
> Managed by ARMS Engine. Update as the brand evolves.
> Referenced by: Frontend, SEO, and Media agents.

---

## Identity
- **Project Name:** <brand name or working title>
- **Mission:** <one-sentence summary of purpose>
- **Vision:** <long-term direction or destination>
- **Personality:** <3 adjectives from user input>
- **Voice & Tone:** <derived from personality>

## Positioning
- **Primary Audience:** <from scope questions>
- **Core Values:** <principles the brand should signal>
- **Differentiation:** <what this brand feels like vs. the reference>

## Visual Identity
- **Color Palette:** <hex values if provided, or "TBD">
- **Typography:** <font names if provided, or "TBD">
- **Logo Status:** <Exists · In progress · Not yet created>
- **Visual Direction:** <Light · Dark · System default · Undecided>

## Use Case Implications
- **Project Type:** <SaaS · Content/Marketing · Mobile-First · Multi-Purpose>
- **Design Priority:** <e.g., "Conversion-focused" · "Content-first" · "App-like experience">

## Notes
- <reference brand, existing site, or other supporting context if relevant>
```

Present `.arms/BRAND.md` for review before proceeding. → **HALT**

---

## MVP vs. Backlog (5.3)

- **Phase 1 (MVP):** Must-haves for launch only
- **Phase 2 (Backlog):** Nice-to-haves → log to `./.gemini/MEMORY.md`

## Pages & Design System (5.4)

Recommend: specific MVP pages · primary brand color · light/dark default · UI library (Lucide vs. Iconify)
Derive recommendations directly from `.arms/BRAND.md` — never generic defaults.

## Approval Gate (5.5)

> "Do you approve this MVP scope, design system, and tech stack? Specify any changes now." → **HALT**

---

## Supplemental Business Prompt Bank

After brand questions are answered, review responses and select the **most relevant 3–5 prompts**. Present as: *"A few more questions to sharpen the plan — answer what you know, skip what you don't:"* → **HALT**

### Business Model Clarity
- What does a successful user do in their first 5 minutes?
- What is the primary conversion event? (Signup · Purchase · Subscription · Lead form)
- Is this a one-time purchase, recurring subscription, or freemium model?
- Do you need multi-tenancy (multiple organizations/workspaces per deployment)?

### Audience & Market
- Is your audience technical or non-technical?
- Single country/language or multiple locales from day one?
- Do you have early users, a waitlist, or is this pre-validation?
- Who is the decision-maker — the buyer or the end user?

### Content & Data
- Will the product have user-generated content, admin-managed content, or both?
- Do you need a CMS, blog, or documentation as part of MVP?
- Expected data volume at launch vs. 12 months out?

### Growth & Operations
- Primary acquisition channel? (SEO · Paid · Referral · Community · Direct sales)
- Do you need an admin dashboard for internal team operations?
- Compliance requirements? (GDPR · HIPAA · SOC 2 · PCI)
- Will you need an API for third-party integrations or public developer ecosystem?

### Team & Timeline
- Building solo, with co-founder, or with team?
- Hard launch deadline or milestone?
- Biggest risk or unknown in this project right now?
