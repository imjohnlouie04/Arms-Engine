---
tools: ["*"]
name: seo-web-performance-expert
description: >
  Expert guidance for SEO optimization, semantic HTML structure, meta tags, and Core Web Vitals (LCP, INP, CLS). Use this skill when working on search engine optimization, improving page performance metrics, structuring HTML for better crawlability and accessibility, optimizing title tags and meta descriptions, fixing layout shifts or loading issues, improving Lighthouse scores, or implementing technical SEO improvements. Also relevant for web accessibility, structured data implementation, heading hierarchy, Open Graph tags, and any work involving Google Search Console, PageSpeed Insights, or Core Web Vitals optimization. Helps with both technical SEO fundamentals and modern performance requirements for 2026.
---

# SEO & Web Performance Expert

You're working with someone who understands how search engines parse pages, how performance impacts rankings, and how structure drives both accessibility and discoverability.

## Core Web Vitals (2026)

Three metrics define user experience and influence rankings:

**Largest Contentful Paint (LCP)** — loading performance
- Target: Under 2.5 seconds
- Measures when the largest visible content element renders
- Most common culprits: unoptimized images, slow server response, render-blocking resources
- Quick wins: preload LCP image with `fetchpriority="high"`, use modern formats (WebP/AVIF), optimize server response time

**Interaction to Next Paint (INP)** — responsiveness
- Target: Under 200 milliseconds
- Replaced FID in March 2024; measures all interactions, not just first input
- Evaluates full time until visual response appears after user interaction
- Quick wins: defer non-critical JavaScript, reduce main thread blocking, optimize event handlers

**Cumulative Layout Shift (CLS)** — visual stability
- Target: Under 0.1
- Tracks unexpected layout shifts during page load
- Common causes: images without dimensions, ads/embeds without reserved space, web fonts causing FOIT/FOUT
- Quick wins: set explicit width/height on images and embeds, use `font-display: swap`, reserve space for dynamic content

### Why They Matter

Core Web Vitals act as a tiebreaker in competitive niches. When content quality and authority are similar, the site with better performance wins. Pages ranking #1 are 10% more likely to pass CWV thresholds than those at #9. Beyond rankings, performance directly impacts conversions—every 100ms of latency can cost 1% in sales.

### Measurement

- **Field data** (real users): Chrome User Experience Report (CrUX), Google Search Console, RUM tools
- **Lab data** (controlled): Lighthouse, PageSpeed Insights, WebPageTest
- Optimize for field data—that's what Google uses for rankings. Lab data helps debug, but real user experience determines success.

## Semantic HTML

Semantic elements describe meaning, not appearance. They help crawlers understand content structure, improve accessibility for screen readers, and provide clearer context for AI systems and LLMs.

### Core Structural Elements

- `<header>` — site/section header (logo, nav)
- `<nav>` — primary navigation blocks
- `<main>` — primary page content (one per page)
- `<article>` — self-contained content (blog posts, products)
- `<section>` — thematic grouping with its own heading
- `<aside>` — tangentially related content (sidebars, related links)
- `<footer>` — site/section footer
- `<figure>` + `<figcaption>` — images, diagrams, code with captions

### Heading Hierarchy

Headings create the document outline. Search engines and assistive tech rely on logical progression:

- One `<h1>` per page matching the primary topic/keyword
- Nest headings logically: h1 → h2 → h3 → h4 (don't skip levels)
- Each heading should describe the section it introduces
- Never use headings for styling—use CSS instead

Example:
```html
<h1>SEO Best Practices for 2026</h1>
<h2>Core Web Vitals</h2>
<h3>Largest Contentful Paint</h3>
<h3>Interaction to Next Paint</h3>
<h2>Semantic HTML</h2>
<h3>Structural Elements</h3>
```

### Why It Matters

Semantic HTML reduces ambiguity for crawlers, making it easier for search engines to map content to entities and extract better snippets. It's also foundational for accessibility—screen readers navigate by landmarks and headings. In 2026, with AI-driven search and voice assistants, structured content is essential for visibility in conversational queries and AI Overviews.

## Meta Tags

Meta tags provide structured information about pages. Only a few matter in 2026.

### Title Tag (Critical)

The most important on-page SEO element. Appears in search results, browser tabs, and social shares.

- **Length**: 50-60 characters (Google uses ~600px width, not strict character count)
- **Structure**: Primary Keyword | Value Proposition | Brand Name
- **Best practices**:
  - Front-load primary keyword
  - Make it compelling—this drives CTR
  - Unique per page
  - Match search intent
  - Use power words when appropriate ("Ultimate," "Guide," "2026")

```html
<title>Core Web Vitals Guide 2026 | Improve LCP, INP & CLS</title>
```

### Meta Description (Important for CTR)

Not a ranking factor, but heavily influences click-through rate. Google rewrites ~62% of descriptions, but a well-crafted one still matters.

- **Length**: 150-160 characters
- **Best practices**:
  - Summarize page value clearly
  - Include primary keyword naturally
  - Write for humans, not algorithms
  - Include a call to action when appropriate
  - Unique per page
  - Avoid keyword stuffing

```html
<meta name="description" content="Learn how to optimize Core Web Vitals in 2026. Practical tips to improve LCP, INP, and CLS for better rankings and user experience.">
```

### Robots Meta Tag

Controls indexing and crawling behavior.

```html
<meta name="robots" content="index, follow">
<meta name="robots" content="noindex, nofollow">
```

Use `noindex` for thin content, duplicate pages, or admin sections. Use sparingly—most pages should be indexed.

### Viewport (Essential for Mobile)

```html
<meta name="viewport" content="width=device-width, initial-scale=1">
```

Required for mobile-first indexing. Without it, mobile rendering breaks.

### Canonical Tag

Points to the preferred version of duplicate/similar content.

```html
<link rel="canonical" href="https://example.com/preferred-url">
```

Use absolute URLs. Essential for e-commerce (product variants), pagination, and syndicated content.

### Open Graph & Twitter Cards

Control how content appears when shared on social platforms.

```html
<meta property="og:title" content="Your Page Title">
<meta property="og:description" content="Your description">
<meta property="og:image" content="https://example.com/image.jpg">
<meta property="og:url" content="https://example.com/page">
<meta name="twitter:card" content="summary_large_image">
```

Image dimensions: 1200x630px for Open Graph, 1200x600px for Twitter.

### Ignore These

- **Meta keywords**: Ignored by all major search engines since ~2009
- **Author meta tag**: No SEO value
- **Revisit-after**: Ignored

## Common Pitfalls

### Semantic HTML
- Using multiple `<main>` elements (only one per page)
- Wrapping everything in `<section>` when `<div>` is more appropriate
- Skipping heading levels (h1 → h3)
- Using headings for styling instead of real hierarchy
- Overusing ARIA when native HTML semantics suffice

### Meta Tags
- Duplicate titles/descriptions across pages
- Keyword stuffing in descriptions
- Titles too long (truncated in SERPs)
- Generic descriptions like "Welcome to our website"
- Missing viewport tag on mobile-optimized sites

### Core Web Vitals
- Images without explicit dimensions (causes CLS)
- Render-blocking JavaScript (hurts LCP and INP)
- No resource prioritization (missing `fetchpriority` or preload)
- Ignoring field data in favor of lab scores
- Optimizing for desktop only (mobile-first indexing matters more)

## Quick Audit Checklist

**Semantic Structure**
- [ ] One clear `<h1>` per page matching primary keyword
- [ ] Logical heading order (no skipped levels)
- [ ] `<main>` wraps primary content (once per page)
- [ ] `<article>` for standalone content, `<section>` for thematic groups
- [ ] `<nav>` for navigation, `<aside>` for sidebars
- [ ] `<figure>` + `<figcaption>` for important images

**Meta Tags**
- [ ] Title: 50-60 chars, unique, includes keyword
- [ ] Description: 150-160 chars, compelling, unique
- [ ] Viewport tag present and correct
- [ ] Canonical URL set (absolute URL)
- [ ] Open Graph tags for social sharing
- [ ] Robots tag only if needed (noindex, etc.)

**Core Web Vitals**
- [ ] LCP under 2.5s (check field data in Search Console)
- [ ] INP under 200ms (defer non-critical JS)
- [ ] CLS under 0.1 (set image dimensions, reserve space for ads)
- [ ] Images use modern formats (WebP/AVIF)
- [ ] Critical resources preloaded or prioritized

## Tools

- **Google Search Console**: Field data for CWV, indexing issues, CTR by query
- **PageSpeed Insights**: Combined field + lab data, specific recommendations
- **Lighthouse** (Chrome DevTools): Lab audit for performance, accessibility, SEO
- **Chrome UX Report (CrUX)**: Real user metrics by origin/URL
- **Screaming Frog / Sitebulb**: Crawl-based audits for meta tags, headings, structure
- **W3C Validator**: Check HTML validity
- **Web Vitals Chrome Extension**: Real-time CWV as you browse

## Philosophy

SEO in 2026 is about clarity and user experience. Search engines reward pages that load fast, make sense structurally, and match user intent. Semantic HTML and proper meta tags aren't hacks—they're the foundation of how the web communicates meaning. Core Web Vitals measure whether you're delivering on that promise.

Focus on:
- **Structure over decoration**: Use semantic elements to describe what content *is*, not how it looks
- **Performance as UX**: Fast pages convert better and rank higher
- **Intent over keywords**: Write titles and descriptions that answer real queries
- **Field data over lab scores**: Optimize for real users on real devices

When in doubt, ask: does this make the page clearer for users, crawlers, and assistive tech? If yes, you're on the right track.