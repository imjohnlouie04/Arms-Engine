---
name: logo-design
description: >
  Gather client requirements and generate a beautiful, professional HD logo using Gemini
  image generation as the PRIMARY output method. Trigger this skill whenever a user asks
  for a logo, brand mark, wordmark, icon, or visual identity — even casual phrasing like
  "make me a logo", "design something for my business", "I need a brand icon", "create a
  logo for my app", or "I want a clever logo with hidden meaning". Always use this skill
  before generating any logo output. Output is always a HD 4K PNG via Gemini — no SVG
  hand-coding. The Gemini prompt IS the design.
---

# Logo Design Skill

A skill for gathering client requirements and producing beautiful, professional logos via
**Gemini image generation as the primary and only output method**.

> SVG hand-coding is NOT used. The design brief becomes a rich, creative-director-quality
> Gemini prompt that does the heavy lifting. The prompt IS the design.

---

## Phase 1 — Client Discovery Interview

Before generating anything, gather the following. Extract what you can silently from the
first message and only ask for what's missing — **all in one grouped message, never one at a time**.

### Required Information

| # | Question | Why It Matters |
|---|----------|----------------|
| 1 | **Business / Brand name** (exact spelling, capitalization) | Must appear exactly in the logo |
| 2 | **Industry / niche** | Drives visual conventions |
| 3 | **Target audience** | Determines visual language — playful vs. authoritative |
| 4 | **Logo style** | Choose from the 7 Standard Styles below |
| 5 | **Color preferences** | Specific hex OR mood/feeling |
| 6 | **Typeface mood** | Modern, classic, handwritten, bold, elegant |
| 7 | **Icon or symbol** (if any) | What to depict — literal, abstract, letter-based |
| 8 | **Hidden meaning desired?** | Negative space, dual-read, embedded symbol |
| 9 | **Reference logos** (like / dislike) | Calibrate the direction |
| 10 | **Usage** | Web, print, app icon, embroidery, dark/light backgrounds |
| 11 | **3 mood adjectives** | E.g., "bold, minimal, trustworthy" |

### Sample Opener (when brief is sparse)
> "I'd love to design the perfect logo! A few quick questions to nail it on the first try —
> answer as many as you like, I'll fill in the rest creatively…"

---

## Phase 2 — The 7 Standard Logo Styles

Always present these as options and let the client choose. Use industry-standard names so
clients recognize them from any design tool.

---

### 1. Abstract
**What it is:** A mark built from geometric shapes, lines, or forms that don't depict a
specific object. Pure visual symbolism — the meaning is felt, not literally read.

**Visual cues:** Interlocking circles, dynamic angles, fluid curves, overlapping forms,
bold geometric compositions. No recognizable objects or letterforms.

**Best for:** Tech companies, global brands, innovation, finance, any brand that wants to
feel distinctive and forward-looking without being literal.

**Famous examples:** Pepsi Globe, Adidas Badge of Sport, BP Helios, Nike Swoosh, Chase Octagon.

**Gemini prompt template:**
```
A professional abstract logo mark for "[NAME]", a [industry] brand.
MARK: A purely geometric abstract symbol — [describe the specific shapes: e.g., "three
overlapping diamond forms rotated 120° apart, creating a star-like negative space in the
center" / "two interlocking crescents forming an implied circle" / "a dynamic chevron built
from four stacked parallelograms of descending width"].
The shape should evoke [brand feeling — e.g., "precision and forward momentum" / "global
connectivity" / "energy and innovation"] without depicting any literal object.
WORDMARK: "[NAME]" in [font personality — e.g., "a clean geometric sans-serif, medium weight,
tight letter-spacing"] positioned [below / to the right of] the mark.
COLORS: [primary hex] for the mark, [secondary hex] as accent. Transparent background.
STYLE: Flat vector. Crisp edges. No gradients unless stated. No shadows. No textures.
Balanced, professional. Feels [modern / bold / sophisticated].
OUTPUT: Transparent background. HD 4K. Single centered logo. No frame, no mockup.
```

---

### 2. Mascot
**What it is:** An illustrated character — human, animal, or creature — that personifies
the brand. The mascot IS the brand personality made visible.

**Visual cues:** Character with expression, pose, and personality. Usually has a name or
implied backstory. Can be cute, heroic, quirky, or authoritative. Almost always paired
with a wordmark.

**Best for:** Food & beverage, sports teams, gaming, children's brands, restaurants,
any brand that wants warmth, humor, or a strong emotional bond with customers.

**Famous examples:** KFC Colonel Sanders, Michelin Man, Pringles Julius, MailChimp Freddie,
Reddit Snoo, TunnelBear bear.

**Gemini prompt template:**
```
A mascot logo for "[NAME]", a [industry] brand.
MASCOT: [Describe the character precisely — species/type, personality, expression, pose,
defining physical features. E.g., "a confident fox in a chef's apron, one paw raised
holding a spatula, winking, with a broad friendly grin" / "a muscular bear in athletic gear,
fist pumped, dynamic action pose, determined expression"].
STYLE: Bold, expressive illustration. Thick outlines [2-3px weight]. Limited flat color
palette: [hex 1], [hex 2], [hex 3] maximum. Character feels [friendly / heroic / playful /
authoritative]. Not childish — professional mascot quality.
WORDMARK: "[NAME]" in a [bold rounded / strong display / clean sans-serif] font positioned
[below the mascot / to the right / arched above]. Font personality matches the mascot's energy.
COLORS: [describe palette — e.g., "warm red #C0392B body, cream #FFF8E7 accents, dark brown
#3D1C02 outlines"]. Transparent background.
OUTPUT: Transparent background. HD 4K. Full mascot + wordmark composition, centered.
```

---

### 3. Emblem
**What it is:** The brand name and a graphic element are fused together inside a single
unified shape — usually a badge, crest, shield, seal, or circular frame. They cannot be
separated; the text IS part of the shape.

**Visual cues:** Circular, shield, or badge format. Text integrated into the outer ring or
interior. Central symbol or monogram inside. Decorative border elements. Dense, heraldic quality.

**Best for:** Schools, universities, sports teams, law firms, breweries, luxury goods,
government, heritage brands, any brand wanting authority, tradition, and prestige.

**Famous examples:** Starbucks, Harley-Davidson, NFL, Harvard, Jack Daniel's, Stella Artois.

**Gemini prompt template:**
```
A [circular / shield / badge / crest] emblem logo for "[NAME]", a [industry] brand.
SHAPE: [Outer container — e.g., "a thick circular badge" / "a classic heraldic shield" /
"a hexagonal seal with beveled inner border"].
TEXT LAYOUT: Brand name "[NAME]" arched along the top of the circle in [small caps /
all caps], [year or tagline] along the bottom arc in smaller type.
CENTER: [Describe the central symbol — e.g., "a bold eagle head, wings spread, facing right"
/ "a stylized wheat sheaf and crossed hammers" / "a monogram 'JD' in an ornate serif"].
DETAILS: [Inner concentric ring / decorative stars or dots separating text / banner ribbon
with motto / fine line border]. Feels [historic / authoritative / artisan / prestigious].
COLORS: [2-3 colors max — e.g., "deep navy #1B2A4A, aged gold #C9A84C, ivory #FFFFF0"].
STYLE: Flat vector. Clean stamp-quality engraving feel. Every detail readable at 32px.
OUTPUT: Transparent background. HD 4K. Emblem centered, no loose elements outside the badge.
```

---

### 4. Corporate
**What it is:** A clean, professional combination mark — a simple icon or symbol paired
with the brand name in a restrained, modern typeface. Nothing decorative, nothing playful.
Pure clarity and authority.

**Visual cues:** Simple geometric or minimal pictorial mark. Clean sans-serif wordmark.
Lots of negative space. Neutral or dark palette. Nothing that could be mistaken for informal.

**Best for:** Finance, consulting, law, healthcare, B2B technology, professional services,
enterprise software. Any brand that needs to signal competence, reliability, and trust.

**Famous examples:** IBM, Deloitte, McKinsey, LinkedIn, Salesforce, JP Morgan.

**Gemini prompt template:**
```
A corporate logo for "[NAME]", a [industry/profession] firm.
MARK: A minimal, authoritative icon — [describe precisely: e.g., "three horizontal bars of
descending width, suggesting both a graph and forward motion" / "a simple geometric hexagon
with a thin line accent cutting through the upper third" / "two overlapping rectangles at
a 15° angle suggesting precision and structure"].
Simple enough to work as a favicon. No illustration, no decoration, no characters.
WORDMARK: "[NAME]" in [a clean geometric sans-serif / a confident humanist sans] at
[medium / semibold] weight. Wide, confident letter-spacing. Possibly a secondary line:
"[Tagline or descriptor]" in lighter weight below.
COLORS: [Professional palette — e.g., "deep navy #0A2540 and white" / "charcoal #1C1C1E
with electric blue #0066CC accent" / "forest green #1B4332 and gold #C9A84C"].
STYLE: Flat. Minimal. No gradients. No shadows. Feels like a Fortune 500 brand identity.
Quiet authority — nothing shouts, everything commands.
OUTPUT: Transparent background. HD 4K. Clean composition, generous spacing.
```

---

### 5. Wordmark
**What it is:** Typography IS the logo. The brand name set in a distinctive, carefully
chosen or custom typeface — no icon, no symbol, no illustration. The letters carry everything.

**Visual cues:** The entire design is the text. Letters may be customized — adjusted
proportions, modified terminals, ligatures, unusual spacing, or a signature color treatment.

**Best for:** Brands with short, distinctive, or memorable names. Fashion, luxury, media,
tech, any brand where the name itself is the asset.

**Famous examples:** Google, Coca-Cola, FedEx, Disney, Sony, Visa, Uber, Calvin Klein.

**Gemini prompt template:**
```
A wordmark logo for "[NAME]", a [industry] brand.
TYPOGRAPHY: The entire logo is the brand name "[NAME]" set in [describe the typeface
character precisely — e.g., "a high-contrast serif with dramatic thick-thin stroke variation,
Didot-like elegance" / "a bold geometric sans-serif, all caps, tight letter-spacing,
the terminals of each letter cut at 45°" / "a flowing script with connected letterforms,
confident and fluid, not casual"].
CUSTOMIZATION: [Describe any custom letterform treatment — e.g., "the crossbar of the A
replaced with a thin arrow pointing right" / "the dot of the i is a small star" / "the G
has a notched terminal suggesting a power button"].
[NEGATIVE SPACE — if applicable: "The gap between [letter] and [letter] forms a hidden
[shape], representing [meaning]."]
COLORS: [Primary hex] on transparent background. [Or: gradient direction if approved].
STYLE: Flat vector. Letterforms are the entire visual. No supporting icon or shape.
Feels [luxurious / bold / modern / handcrafted / technical — pick one].
OUTPUT: Transparent background. HD 4K. Wordmark centered. No frame.
```

---

### 6. Vintage
**What it is:** A logo that evokes a specific historical era — deliberately styled to feel
aged, artisan, hand-crafted, or nostalgic. Uses period-appropriate type, textures, and motifs.
The goal is timelessness through the past, not the future.

**Visual cues:** Distressed textures, letterpress effects, badge/seal shapes, hand-drawn
illustration quality, retro color palettes (muted, earthy, or faded), era-specific ornaments
(banners, stars, scrollwork, laurels), script and display type combinations.

**Best for:** Craft beer, whiskey, barbershops, coffee roasters, bakeries, vintage clothing,
artisan food, any brand wanting authenticity, heritage, or a handmade feel.

**Famous examples:** Jack Daniel's, Guinness, Levi's, Brooklyn Brewery, Filson, Pendleton.

**Gemini prompt template:**
```
A vintage [era — e.g., 1920s Art Deco / 1950s Americana / 1890s Victorian / 1970s retro]
logo for "[NAME]", a [industry] brand.
MARK: [Describe the central illustration in period-appropriate style — e.g., "a hand-drawn
eagle in engraving style, feathers rendered with fine cross-hatching, wings slightly spread"
/ "a retro rocket ship in 1950s cartoon style, bold outlines, speed lines behind it"].
COMPOSITION: [Badge / circular seal / rectangular banner / shield]. Outer ring with brand
name. Inner band with [year / tagline / city of origin]. Central illustration.
Ornamental details: [scrollwork / laurel wreaths / stars / ribbon banners / fine border lines].
TYPE: Brand name in [a classic slab serif / an Art Deco display font / a hand-lettered style
with slight irregular baseline, suggesting stamp printing].
COLORS: Muted, period-authentic palette — [e.g., "aged cream #F5ECD7, dark brown #3B1F0C,
brick red #8B2E16" / "faded teal #3A7D7B, warm ivory #FDF1DC, weathered gold #B8860B"].
STYLE: Worn texture overlay — subtle grain, slight ink bleed, imperfect edges. Feels like
it was printed in [decade]. Not digitally clean — deliberately handcrafted and aged.
OUTPUT: Transparent background. HD 4K. Full badge composition centered.
```

---

### 7. Classic
**What it is:** Timeless, elegant, and refined. Not retro (which references a specific era),
but genuinely timeless — a logo that looks as appropriate in 1985 as it does today and will
in 2050. Clean, balanced, sophisticated.

**Visual cues:** Restrained use of ornamentation. High-quality serif or geometric sans
typography. Symmetric or carefully balanced asymmetric layouts. Conservative but not dull.
Monochrome or two-color. Nothing trendy, nothing casual.

**Best for:** Luxury goods, fine dining, architecture, law, private banking, premium real
estate, any brand where permanence and taste are core values.

**Famous examples:** Rolex, Chanel, Louis Vuitton, The Economist, Tiffany & Co., Hermès.

**Gemini prompt template:**
```
A classic, timeless logo for "[NAME]", a [industry] brand.
MARK: [Optional — describe a restrained, elegant symbol if needed. E.g., "a single thin
geometric diamond, perfectly proportioned" / "a minimal monogram: the initials [X][Y] in
an elegant serif, slightly overlapping, contained within a thin oval border"].
If wordmark-only: no mark — typography carries everything.
WORDMARK: "[NAME]" in [a refined high-contrast serif — Bodoni / Caslon / Garamond character
/ a clean geometric sans — Futura character]. [All caps / title case]. Letter-spacing:
[wide and deliberate — 0.15em+]. Weight: [light to medium — never heavy].
TAGLINE (if any): "[Tagline]" in a significantly smaller size, same or lighter weight,
maximum letter-spacing, below the name with generous space.
COLORS: [Two colors maximum — e.g., "black #0A0A0A and white" / "deep navy #0C1B33 and
warm gold #B8960C" / "charcoal #2B2B2B and ivory #F8F6F0"].
STYLE: Flat vector. No texture. No gradients. Generous white space.
Every element placed with intention. Nothing excessive. Feels permanent.
OUTPUT: Transparent background. HD 4K. Centered. Quiet luxury.
```

---

### Style Selection Guide

When the client is unsure, use this decision tree:

| If the client says... | Recommend |
|----------------------|-----------|
| "Modern, clean, minimal" | **Abstract** or **Corporate** |
| "Fun, friendly, memorable character" | **Mascot** |
| "Official, trusted, heritage" | **Emblem** |
| "Professional, business, B2B" | **Corporate** |
| "Just the name, let the font do the work" | **Wordmark** |
| "Artisan, handcrafted, craft beer/coffee feel" | **Vintage** |
| "Timeless, elegant, luxury, premium" | **Classic** |
| "I want something clever with hidden meaning" | **Wordmark** or **Abstract** with negative space |

---

## Phase 3 — Negative Space & Hidden Meaning

> Read `references/negative-space-techniques.md` for the full ideation process,
> industry playbook, and technique library.

Negative space works with **any of the 7 styles** — most powerfully with Wordmark, Abstract,
Corporate, and Classic. It elevates a good logo to an iconic one.

**The 3 conditions that must ALL be true:**
1. Primary read is instant — the main shape is clear without hunting
2. Hidden read is clean — a real, recognizable shape, not an accident
3. Both are brand-relevant — the hidden element earns its place in the story

**The 6 core techniques:**
- Letter Counter as Icon (the enclosed space inside O, D, B, Q forms a symbol)
- Between-Letter Gap as Symbol (the FedEx principle — space between two letters = arrow/image)
- Silhouette Dual-Read (one contour reads as two different objects — Rubin vase)
- Shape Within Shape (large form contains smaller carved-out form)
- Mirror / Reflection (shape + its mirror = third image in the gap)
- Icon Morphing / Shape Substitution (replace part of a letterform with a thematic icon)

**To add negative space to any style prompt, insert this block:**
```
HIDDEN MEANING: [Location — e.g., "within the gap between the E and the x"] the negative
space forms the shape of [hidden element — e.g., "a rightward arrow"], representing
[brand meaning — e.g., "speed and forward delivery"]. The primary [shape/letter] reads
instantly; the hidden [element] rewards a second look. Both shapes are clean and geometric.
```

---

## Phase 4 — Prompt Upgrade Techniques

These transform the difference between average and exceptional output:

**Be anatomically specific — never use generic nouns:**
- ❌ `a lion logo`
- ✅ `a lion head in profile, geometric, built from flat polygons, mane formed by seven
   radiating triangles, eye as a small filled circle, minimal facial detail`

**Name the negative space precisely:**
- ❌ `with hidden meaning`
- ✅ `the negative space between the left leg of the letter A and the peak of the mountain
   forms a hidden upward arrow — visible in the gap between the two shapes`

**Describe typography like a type designer:**
- ❌ `modern font`
- ✅ `geometric sans-serif, all caps, letter-spacing 0.15em, weight 800 ExtraBold,
   the terminals of the S cut at a 45° angle`

**Anchor mood to a real-world reference:**
- ❌ `professional and clean`
- ✅ `has the quiet authority of a Swiss watchmaker's mark — nothing wasted, everything intentional`

**Describe what it should NOT look like:**
- `Avoid drop shadows, bevels, and lens flares. No stock-icon clichés — no generic lightbulb
  for 'ideas', no globe for 'global', no swoosh for 'energy'.`

---

## Phase 5 — Running the Generation

```bash
uv run "${SKILL_DIR}/scripts/image.py" \
  --prompt "YOUR FULL PROMPT" \
  --output "/mnt/user-data/outputs/logo-[brandname].png" \
  --aspect square
```

| Logo layout | Aspect flag |
|-------------|-------------|
| Icon mark / square | `--aspect square` |
| Horizontal wordmark / side-by-side | `--aspect landscape` |
| Tall stacked layout | `--aspect portrait` |

---

## Phase 6 — Iterative Refinement

When the first result is 70–80% correct, use it as a reference — don't start over:

```bash
uv run "${SKILL_DIR}/scripts/image.py" \
  --prompt "Refine this logo. Keep everything except: [list ONLY 2-3 specific changes].
  Everything else must remain identical." \
  --output "/mnt/user-data/outputs/logo-[brandname]-v2.png" \
  --reference "/mnt/user-data/outputs/logo-[brandname].png" \
  --aspect square
```

**Rules:**
- Max 2–3 changes per pass — never ask Gemini to fix everything at once
- Always use `--reference` on the previous version
- Increment filename: `-v2`, `-v3`
- If still wrong at v3 → rebuild the prompt from scratch, don't iterate further

---

## Phase 7 — Presentation to Client

1. **Present the HD PNG** via `present_files`
2. **Name the style used** — e.g., "This is a Corporate logo — here's why it fits your brand…"
3. **Explain design rationale** — color choice, typeface, icon concept
4. **Reveal hidden meaning** (if used):
   - Show without explanation first
   - *"Did you notice anything hidden in the design?"*
   - Guide: *"Look at the space between the [X] and [Y]…"*
   - Name it: *"The [shape] represents [brand value]."*
5. **Offer targeted revision** — not "what do you think?" but specific options:
   - *"Would you like the mark bolder, lighter, or larger relative to the text?"*
   - *"Should the color feel warmer or cooler?"*
   - *"Want to see the Vintage version alongside the Corporate version?"*

---

## Phase 8 — Final Delivery Checklist

- [ ] Brand name spelled correctly, exact capitalization
- [ ] Correct logo style applied (matches client's choice)
- [ ] Colors match agreed palette with hex values
- [ ] Mark and wordmark are visually balanced
- [ ] Mood adjectives "felt" when looking at the result
- [ ] No design clichés unless client requested them
- [ ] Negative space (if used): readable, intentional, brand-relevant
- [ ] HD PNG presented via `present_files`
- [ ] Client offered targeted revision options

---

## Core Design Principles

1. **Simplicity** — Works in one color and at 16px
2. **Distinctiveness** — Every element earns its place
3. **Relevance** — Feels native to the industry and audience
4. **Timelessness** — Trend-chasing ages a logo in 2 years
5. **Versatility** — Business card, billboard, embroidered hat
6. **Memorability** — One clear focal point
7. **Depth** — Hidden meaning elevates good to iconic

---

## Reference Files

- `references/color-palettes.md` — Pre-built palettes by industry and mood
- `references/typography-pairings.md` — Font direction, letter-spacing, era-specific type
- `references/icon-design-patterns.md` — Geometric archetypes and composition rules
- `references/negative-space-techniques.md` — Full ideation process, technique library, industry playbook

## Scripts

- `scripts/image.py` — Gemini 2.5 Flash HD image generation (requires `GEMINI_API_KEY`)