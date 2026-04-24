# Performance & SEO Checklist

> Read by: arms-seo-agent, arms-frontend-agent
> Triggered by: `run review`, SEO tasks, Core Web Vitals optimization

---

## Core Web Vitals Targets

| Metric | Good | Needs Improvement | Poor |
|---|---|---|---|
| LCP (Largest Contentful Paint) | ≤ 2.5s | 2.5–4s | > 4s |
| INP (Interaction to Next Paint) | ≤ 200ms | 200–500ms | > 500ms |
| CLS (Cumulative Layout Shift) | ≤ 0.1 | 0.1–0.25 | > 0.25 |

**Target:** All three in "Good" range before launch.

### How to Measure
```bash
# Lighthouse CLI
npx lighthouse https://your-domain.com --output html --view

# PageSpeed Insights API
curl "https://www.googleapis.com/pagespeedonline/v5/runPagespeed?url=https://your-domain.com&strategy=mobile"
```

---

## Next.js Performance Checklist

### Images
```
[ ] All images use next/image — never raw <img> tags
[ ] Images have explicit width and height to prevent CLS
[ ] Hero/above-fold images use priority prop
[ ] Format: WebP or AVIF (next/image handles this automatically)
[ ] Lazy load below-fold images (default in next/image)
```

```tsx
// Correct
import Image from 'next/image'
<Image src="/hero.jpg" alt="Hero" width={1200} height={600} priority />

// Wrong — causes CLS, no optimization
<img src="/hero.jpg" alt="Hero" />
```

### Fonts
```
[ ] Use next/font — eliminates layout shift from custom fonts
[ ] Preload primary font
[ ] font-display: swap for fallback
```

```tsx
import { Inter } from 'next/font/google'
const inter = Inter({ subsets: ['latin'], display: 'swap' })
```

### Data Fetching
```
[ ] Static pages use generateStaticParams (App Router) or getStaticProps (Pages)
[ ] Dynamic data uses React Server Components where possible
[ ] Client-side fetching uses SWR or React Query — no useEffect fetch chains
[ ] API responses are cached appropriately (revalidate tag or time-based)
```

### Bundle Size
```bash
# Analyze bundle
ANALYZE=true npm run build
```
```
[ ] No library imported in full when tree-shakeable (e.g., import { X } from 'lib', not import lib)
[ ] Dynamic imports for heavy components (charts, editors, maps)
[ ] No duplicate dependencies (check with `npm dedupe`)
```

---

## SEO Checklist

### Meta Tags — Every Page
```tsx
// app/layout.tsx or per-page metadata
export const metadata: Metadata = {
  title: {
    default: 'Brand Name',
    template: '%s | Brand Name'  // page titles: "About | Brand Name"
  },
  description: 'Under 160 characters. Specific, not generic.',
  openGraph: {
    title: 'Brand Name',
    description: 'Same as meta description or variant',
    url: 'https://your-domain.com',
    siteName: 'Brand Name',
    images: [{ url: '/og-image.png', width: 1200, height: 630 }],
    type: 'website'
  },
  twitter: {
    card: 'summary_large_image',
    title: 'Brand Name',
    description: 'Under 160 characters',
    images: ['/og-image.png']
  },
  robots: { index: true, follow: true },
  canonical: 'https://your-domain.com/page'
}
```

```
[ ] Unique title per page — no duplicate titles
[ ] Meta description per page — under 160 characters, includes primary keyword
[ ] OG image per page or global fallback (1200×630px)
[ ] Twitter card configured
[ ] Canonical URL set (especially for paginated content)
[ ] robots meta: noindex on admin, auth, and utility pages
```

### Schema Markup
```tsx
// Add to page component
const schema = {
  '@context': 'https://schema.org',
  '@type': 'WebSite',  // or Organization, Product, Article, etc.
  name: 'Brand Name',
  url: 'https://your-domain.com'
}

// In component:
<script
  type="application/ld+json"
  dangerouslySetInnerHTML={{ __html: JSON.stringify(schema) }}
/>
```

**Schema types by project:**
| Project Type | Schema |
|---|---|
| SaaS | Organization + WebApplication |
| Blog / Content | Article + BreadcrumbList |
| E-commerce | Product + Offer + Review |
| Local Business | LocalBusiness |

### Sitemap & Robots
```tsx
// app/sitemap.ts
export default function sitemap(): MetadataRoute.Sitemap {
  return [
    { url: 'https://your-domain.com', lastModified: new Date(), changeFrequency: 'weekly', priority: 1 },
    { url: 'https://your-domain.com/about', lastModified: new Date(), changeFrequency: 'monthly', priority: 0.8 },
  ]
}

// app/robots.ts
export default function robots(): MetadataRoute.Robots {
  return {
    rules: { userAgent: '*', allow: '/', disallow: ['/admin/', '/api/'] },
    sitemap: 'https://your-domain.com/sitemap.xml'
  }
}
```

```
[ ] Sitemap generated and submitted to Google Search Console
[ ] robots.txt blocks admin, auth, and API routes
[ ] No important pages accidentally blocked by robots.txt
```

### Content SEO
```
[ ] H1 exists and is unique per page — matches page intent
[ ] Heading hierarchy: H1 → H2 → H3 (no skipped levels)
[ ] Internal links use descriptive anchor text (not "click here")
[ ] Images have descriptive alt text
[ ] URLs are descriptive and lowercase: /about-us not /page?id=3
[ ] 404 page exists and returns actual 404 status code
```

---

## Performance Review Report Format

arms-seo-agent reports findings in this format:

```markdown
## Performance & SEO Review — <date>

### Core Web Vitals
- LCP: Xs (Good / Needs Work / Poor)
- INP: Xms
- CLS: X.XX

### Critical Issues (block launch)
- [ ] Missing OG images on /pricing and /about
- [ ] LCP image not using priority prop

### Warnings (fix before launch)
- [ ] Bundle size: lodash imported in full — switch to tree-shaken imports
- [ ] No schema markup on homepage

### Passed
- ✅ next/font configured correctly
- ✅ All images use next/image
- ✅ Sitemap generated
```
