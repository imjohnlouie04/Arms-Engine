import json
import os
import re

from .paths import WorkspacePaths


NEW_PROJECT_BRAND_MARKER = "> New project detected."
NEW_PROJECT_BRAND_FIELDS = (
    "Mission",
    "Vision",
    "Personality",
    "Voice & Tone",
    "Primary Audience",
    "Core Values",
    "Differentiation",
    "Color Palette",
    "Typography",
    "Logo Status",
    "Visual Direction",
    "Project Type",
    "Design Priority",
    "Preferred Tech Stack",
    "Deployment Target",
    "Backend / Data Layer",
    "Authentication Requirement",
    "Technical Constraints",
    "Experience Type",
    "Industry / Business Niche",
    "Service Area / Local SEO Target",
    "Required Website Sections",
    "Primary Calls to Action",
    "Icon System",
    "Image Requirements",
    "SEO Focus",
)
BOOTSTRAP_ONLY_FILES = {
    "README.md",
    "README.mdx",
    "LICENSE",
    "LICENSE.md",
    "CHANGELOG",
    "CHANGELOG.md",
}
SOURCE_FILE_EXTENSIONS = {
    ".js",
    ".jsx",
    ".ts",
    ".tsx",
    ".py",
    ".go",
    ".rs",
    ".java",
    ".kt",
    ".rb",
    ".php",
    ".cs",
    ".swift",
    ".scala",
    ".sh",
}
PROJECT_SIGNAL_FILE_CHAR_CAP = 12000
PLACEHOLDER_BRAND_TOKENS = (
    "[Name]",
    "[Purpose]",
    "[Long-term goal]",
    "[Voice/Tone]",
    "[Approach]",
    "[Target]",
    "[Values]",
    "[Unique Factor]",
    "[HEX/OKLCH]",
    "[Google Fonts]",
    "[Generated/Pending]",
    "[Glassmorphism/Dark Mode/etc]",
    "[SaaS/Community/etc]",
    "[UX Factor]",
    "[Misc preferences]",
)
PROJECT_MARKER_FILES = (
    "package.json",
    "package-lock.json",
    "pnpm-lock.yaml",
    "yarn.lock",
    "bun.lockb",
    "pyproject.toml",
    "requirements.txt",
    "Pipfile",
    "poetry.lock",
    "go.mod",
    "Cargo.toml",
    "composer.json",
    "Gemfile",
    "pom.xml",
    "build.gradle",
    "README.md",
    "README.mdx",
    "index.html",
)
PROJECT_MARKER_DIRS = (
    "src",
    "app",
    "pages",
    "components",
    "lib",
    "server",
    "backend",
    "frontend",
    "api",
    "public",
    "docs",
)
IGNORED_PROJECT_ENTRIES = {
    ".git",
    ".github",
    ".gemini",
    ".arms",
    ".vscode",
    ".idea",
    "node_modules",
    "dist",
    "build",
    "coverage",
    "__pycache__",
    ".DS_Store",
}

NEW_PROJECT_BRAND_QUESTIONS = [
    "1. Primary use case: SaaS · Content/Marketing · Mobile-First · Multi-Purpose",
    "2. Target audience",
    "3. Core features",
    "4. Goal / Monetization model",
    "5. Brand name (or working title if unnamed)",
    "6. Brand personality — pick up to 3 words:",
    "   Bold · Minimal · Playful · Premium · Technical · Warm · Rebellious · Trustworthy · Friendly · Sharp",
    "7. Closest competitor or reference brand? (URL or name)",
    "8. What should your brand feel like vs. that reference?",
    "   e.g. \"Like Notion but warmer\" · \"Like Stripe but more human\"",
    "9. Existing brand assets?",
    "   Logo (Y/N) · Color palette (Y/N) · Typography (Y/N) · Existing site (URL or N)",
    "10. Preferred visual direction: Light · Dark · System default · Undecided",
]

NEW_PROJECT_TECH_STACK_QUESTIONS = [
    "11. Preferred tech stack:",
    "    [A] Next.js + Supabase + shadcn/ui (latest stable)",
    "    [B] Nuxt + Firebase + Nuxt UI (latest stable)",
    "    [C] Astro + Tailwind CSS + DaisyUI (latest stable)",
    "    [D] Custom",
    "12. Preferred deployment target:",
    "    [1] Vercel",
    "    [2] Docker / VPS",
    "    [3] AWS / GCP",
    "13. Preferred backend / data layer if custom or undecided:",
    "    Supabase · Firebase · Postgres · MySQL · REST API · GraphQL · Custom · Unsure",
    "14. Authentication requirement:",
    "    Email/password · OAuth · Magic link · Anonymous/guest · None yet · Unsure",
    "15. Any hard technical constraints or must-use tools?",
    "    e.g. TypeScript only, Tailwind required, self-hosted only, no Firebase, mobile-first, CMS needed",
]

NEW_PROJECT_WEBSITE_BRIEF_QUESTIONS = [
    "16. If this project needs a website or landing page, what experience type is it?",
    "    Local service business · Marketing site · Portfolio · Ecommerce · Editorial · Other · N/A",
    "17. What industry or business niche should the site speak to?",
    "    e.g. classic car restoration, dental clinic, boutique hotel, law firm, SaaS",
    "18. What location or service area matters for local SEO, if any?",
    "    e.g. Austin, Texas · Metro Manila · Nationwide · N/A",
    "19. Which sections must be present on the page?",
    "    e.g. Header/Nav, Hero, Services, Gallery, About, Process, Testimonials, Contact Form, Footer",
    "20. What are the primary calls to action?",
    "    e.g. Request a Quote, Book a Consultation, Call Now, View Recent Work",
    "21. What icon system should the UI use?",
    "    Default to Font Awesome for marketing pages unless there is a stronger requirement",
    "22. What image coverage is needed?",
    "    e.g. 5+ images, hero image, detail shots, before/after work, finished showcase pieces",
    "23. What SEO priorities should the build emphasize?",
    "    e.g. local service keywords, visible contact info, trust signals, semantic headings, descriptive alt text",
    "24. Any content or visual non-negotiables?",
    "    e.g. no emoji, premium tone, visible phone number, dark theme, editorial typography",
]

QUESTION_FIELD_SPECS = (
    (1, "Primary use case", "Primary Use Case"),
    (2, "Target audience", "Primary Audience"),
    (3, "Core features", "Core Features"),
    (4, "Goal / Monetization model", "Goal / Monetization Model"),
    (5, "Brand name", "Project Name"),
    (6, "Brand personality", "Personality"),
    (7, "Closest competitor or reference brand", "Reference Brand"),
    (8, "What should your brand feel like vs. that reference", "Brand Comparison"),
    (9, "Existing brand assets", "Existing Brand Assets"),
    (10, "Preferred visual direction", "Visual Direction"),
    (11, "Preferred tech stack", "Preferred Tech Stack"),
    (12, "Preferred deployment target", "Deployment Target"),
    (13, "Preferred backend / data layer", "Backend / Data Layer"),
    (14, "Authentication requirement", "Authentication Requirement"),
    (15, "Any hard technical constraints or must-use tools", "Technical Constraints"),
    (16, "If this project needs a website or landing page, what experience type is it", "Experience Type"),
    (17, "What industry or business niche should the site speak to", "Industry / Business Niche"),
    (18, "What location or service area matters for local SEO", "Service Area / Local SEO Target"),
    (19, "Which sections must be present on the page", "Required Website Sections"),
    (20, "What are the primary calls to action", "Primary Calls to Action"),
    (21, "What icon system should the UI use", "Icon System"),
    (22, "What image coverage is needed", "Image Requirements"),
    (23, "What SEO priorities should the build emphasize", "SEO Focus"),
    (24, "Any content or visual non-negotiables", "Content / Visual Non-Negotiables"),
)

NOTE_DRIVEN_INTAKE_FIELDS = (
    "Primary Use Case",
    "Core Features",
    "Goal / Monetization Model",
    "Reference Brand",
    "Brand Comparison",
    "Existing Brand Assets",
    "Content / Visual Non-Negotiables",
)

PROJECT_PRESETS = {
    "local-business": {
        "description": "Local service business marketing site defaults with SEO, CTA, and contact visibility baked in.",
        "fields": {
            "Project Type": "Content / Marketing Site",
            "Design Priority": "Conversion-focused trust and local discoverability",
            "Voice & Tone": "Clear, trustworthy, and benefits-first for local buyers",
            "Typography": "Distinctive display typography paired with a highly readable body font",
            "Icon System": "Font Awesome",
            "Experience Type": "Local service business",
            "Required Website Sections": "Header/Nav, Hero, Services, Recent Work/Gallery, About/History, Our Process, Testimonials, Contact Info with Form, Footer",
            "Primary Calls to Action": "Request a Quote, Book a Consultation, Call Now",
            "Image Requirements": "At least 5 images including hero imagery, supporting detail shots, and showcase work",
            "SEO Focus": "Local search intent, visible contact information, trust signals, semantic headings, and descriptive alt text",
            "Technical Constraints": "Mobile-first, clear contact visibility, and no emoji unless explicitly requested",
        },
    },
    "saas": {
        "description": "Product-led SaaS website defaults for conversion, onboarding clarity, and feature communication.",
        "fields": {
            "Project Type": "Web Application",
            "Design Priority": "Conversion-focused product clarity and onboarding confidence",
            "Voice & Tone": "Clear, confident, and product-literate without sounding inflated",
            "Typography": "Modern display typography paired with a clean, highly legible interface body font",
            "Icon System": "Font Awesome",
            "Experience Type": "Marketing site",
            "Required Website Sections": "Header/Nav, Hero, Problem/Solution, Features, Integrations, Social Proof, Pricing, FAQ, CTA, Footer",
            "Primary Calls to Action": "Start Free, Book a Demo, View Product Tour",
            "Image Requirements": "Product UI screenshots, dashboard mockups, and supporting hero imagery",
            "SEO Focus": "Category keywords, product value propositions, semantic headings, metadata, and strong internal linking",
            "Technical Constraints": "Mobile-first, accessible interaction states, and performance-conscious media usage",
        },
    },
    "portfolio": {
        "description": "Portfolio-site defaults emphasizing featured work, case studies, and credibility.",
        "fields": {
            "Project Type": "Content / Marketing Site",
            "Design Priority": "Visual storytelling and clear proof of work",
            "Voice & Tone": "Confident, articulate, and craft-aware",
            "Typography": "Expressive display typography paired with a polished editorial body font",
            "Icon System": "Font Awesome",
            "Experience Type": "Portfolio",
            "Required Website Sections": "Header/Nav, Hero, Featured Work, Case Studies, About, Process, Testimonials, Contact, Footer",
            "Primary Calls to Action": "View Work, Start a Project, Contact",
            "Image Requirements": "Project hero imagery, gallery coverage, and detail shots for featured work",
            "SEO Focus": "Service keywords, portfolio discoverability, semantic case-study structure, and descriptive alt text",
            "Technical Constraints": "Strong mobile layout hierarchy and no decorative noise that obscures work samples",
        },
    },
    "ecommerce": {
        "description": "Ecommerce storefront defaults focused on trust, merchandising, and conversion.",
        "fields": {
            "Project Type": "Web Application",
            "Design Priority": "Merchandising clarity and purchase conversion",
            "Voice & Tone": "Clear, persuasive, and product-focused",
            "Typography": "Bold product-facing display typography with a clean commerce-friendly body font",
            "Icon System": "Font Awesome",
            "Experience Type": "Ecommerce",
            "Required Website Sections": "Header/Nav, Hero, Featured Collections, Product Highlights, Reviews, FAQ, Shipping/Returns, CTA, Footer",
            "Primary Calls to Action": "Shop Now, View Collection, Add to Cart",
            "Image Requirements": "Collection hero images, product closeups, and supporting merchandising visuals",
            "SEO Focus": "Transactional keywords, collection discoverability, structured product content, and strong metadata",
            "Technical Constraints": "Mobile-first commerce flows, clear pricing visibility, and performant product imagery",
        },
    },
    "content-site": {
        "description": "Editorial and content-marketing defaults with strong structure and discoverability.",
        "fields": {
            "Project Type": "Content / Marketing Site",
            "Design Priority": "Readable editorial hierarchy and search visibility",
            "Voice & Tone": "Authoritative, readable, and structured",
            "Typography": "Editorial display typography paired with a comfortable long-form reading font",
            "Icon System": "Font Awesome",
            "Experience Type": "Editorial",
            "Required Website Sections": "Header/Nav, Hero, Featured Content, Topic Sections, Newsletter CTA, About, FAQ, Footer",
            "Primary Calls to Action": "Read More, Subscribe, Explore Topics",
            "Image Requirements": "Hero artwork, article feature imagery, and section-supporting visuals",
            "SEO Focus": "Informational keywords, semantic content structure, internal linking, and metadata discipline",
            "Technical Constraints": "Readable typography scales, strong content hierarchy, and lightweight page performance",
        },
    },
}

QUESTION_VALUE_ALIASES = {
    "Preferred Tech Stack": {
        "a": "Next.js + Supabase + shadcn/ui (latest stable)",
        "b": "Nuxt + Firebase + Nuxt UI (latest stable)",
        "c": "Astro + Tailwind CSS + DaisyUI (latest stable)",
        "d": "Custom",
    },
    "Deployment Target": {
        "1": "Vercel",
        "2": "Docker / VPS",
        "3": "AWS / GCP",
    },
}

STACK_RECOMMENDATIONS = {
    "nextjs": {
        "label": "Next.js + Supabase + shadcn/ui",
        "framework": "Next.js (latest stable)",
        "ui_system": "shadcn/ui",
        "default_data_layer": "Supabase",
        "default_deployment": "Vercel",
        "default_auth": "Email/password or OAuth via Supabase Auth",
        "default_icon_system": "lucide-react",
        "best_for": "SaaS products, dashboards, ecommerce, and authenticated application flows",
        "reason": (
            "Best default for modern full-stack products that need strong application UI primitives, "
            "flexible rendering, and a fast path from landing page to product surface."
        ),
    },
    "nuxt": {
        "label": "Nuxt + Firebase + Nuxt UI",
        "framework": "Nuxt (latest stable)",
        "ui_system": "Nuxt UI",
        "default_data_layer": "Firebase",
        "default_deployment": "AWS / GCP",
        "default_auth": "OAuth, email/password, or magic link via Firebase Auth",
        "default_icon_system": "Nuxt Icon",
        "best_for": "mobile-first experiences, content-plus-app hybrids, and teams that prefer the Nuxt ecosystem",
        "reason": (
            "Strong fit for teams that want Vue/Nuxt ergonomics, a polished first-party UI system, "
            "and a backend that scales quickly with managed services."
        ),
    },
    "astro": {
        "label": "Astro + Tailwind CSS + DaisyUI",
        "framework": "Astro (latest stable)",
        "ui_system": "DaisyUI",
        "default_data_layer": "Astro content collections or a lightweight CMS/API",
        "default_deployment": "Vercel",
        "default_auth": "None by default unless the product needs gated content",
        "default_icon_system": "Font Awesome",
        "best_for": "marketing sites, local-service websites, editorial experiences, and portfolio projects",
        "reason": (
            "Best recommendation for content-heavy or marketing-led builds where performance, clarity, "
            "and fast static delivery matter more than complex application state."
        ),
    },
}


def read_text_file(path: str, max_chars: int = 40000) -> str:
    """Read up to *max_chars* bytes from *path*; return empty string on any error."""
    if not os.path.exists(path):
        return ""
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read(max_chars)
    except OSError:
        return ""


def read_project_signal_file(path: str, max_chars: int = PROJECT_SIGNAL_FILE_CHAR_CAP) -> tuple:
    """Read a project signal file, returning (content, status).

    Status values: ``"ok"``, ``"missing"``, ``"too_large"``, ``"unreadable"``.
    """
    if not os.path.exists(path):
        return "", "missing"
    try:
        if os.path.getsize(path) > max_chars:
            return "", "too_large"
    except OSError:
        return "", "unreadable"
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read(max_chars), "ok"
    except OSError:
        return "", "unreadable"


def is_new_project_brand_questionnaire(content: str) -> bool:
    """Return True if *content* contains the new-project brand questionnaire marker."""
    return NEW_PROJECT_BRAND_MARKER in content


def extract_brand_field(content: str, field_name: str) -> str:
    """Extract the value of a ``- **Field:** value`` line from *content*."""
    pattern = rf"(?m)^- \*\*{re.escape(field_name)}:\*\* (.*)$"
    match = re.search(pattern, content)
    return match.group(1).strip() if match else ""


def normalize_answer_key(value: str) -> str:
    """Normalise a field label to a lowercase, collapsed-whitespace key for dict lookups."""
    return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()


def build_answer_field_aliases() -> dict:
    """Build a mapping of normalised label variants → canonical BRAND.md field names."""
    aliases = {}
    direct_fields = ("Project Name",) + NEW_PROJECT_BRAND_FIELDS + NOTE_DRIVEN_INTAKE_FIELDS

    for field_name in direct_fields:
        aliases[normalize_answer_key(field_name)] = field_name

    for _, label, field_name in QUESTION_FIELD_SPECS:
        aliases[normalize_answer_key(label)] = field_name

    aliases.update(
        {
            "brand name": "Project Name",
            "working title": "Project Name",
            "mission": "Mission",
            "vision": "Vision",
            "voice tone": "Voice & Tone",
            "voice and tone": "Voice & Tone",
            "target audience": "Primary Audience",
            "goal monetization model": "Goal / Monetization Model",
            "closest competitor": "Reference Brand",
            "reference brand": "Reference Brand",
            "brand comparison": "Brand Comparison",
            "existing assets": "Existing Brand Assets",
            "non negotiables": "Content / Visual Non-Negotiables",
            "content visual non negotiables": "Content / Visual Non-Negotiables",
        }
    )
    return aliases


def normalize_structured_answer(field_name: str, value: str) -> str:
    """Resolve single-letter choice aliases and normalise whitespace in *value*."""
    normalized_value = " ".join(value.split()).strip()
    if not normalized_value:
        return normalized_value

    aliases = QUESTION_VALUE_ALIASES.get(field_name, {})
    lowered = re.sub(r"^option\s+", "", normalized_value.lower()).strip()
    choice_match = re.match(r"^\[?([a-z0-9])\]?(?:\s*(?:[-:.)]|$).*)?$", lowered)
    if choice_match:
        choice_key = choice_match.group(1)
        if choice_key in aliases:
            return aliases[choice_key]

    return normalized_value


def update_brand_field(content: str, field_name: str, value: str, overwrite: bool = False) -> tuple:
    """Set *field_name* to *value* in *content* if the field exists and is unanswered (or *overwrite* is True).

    Returns ``(updated_content, changed: bool)``.
    """
    pattern = rf"(?m)^- \*\*{re.escape(field_name)}:\*\* .*$"
    if not re.search(pattern, content):
        return content, False

    current_value = extract_brand_field(content, field_name)
    if current_value and not brand_field_is_unanswered(current_value) and not overwrite:
        return content, False

    updated_line = f"- **{field_name}:** {value}"
    return re.sub(pattern, updated_line, content, count=1), True


def extract_note_entry(content: str, label: str) -> str:
    """Extract the value of a ``- label: value`` note line from *content*."""
    pattern = rf"(?m)^- {re.escape(label)}: (.*)$"
    match = re.search(pattern, content)
    return match.group(1).strip() if match else ""


def upsert_note_entry(content: str, label: str, value: str) -> tuple:
    """Insert or update a ``- label: value`` note line in the ``## Notes`` section.

    Returns ``(updated_content, changed: bool)``.
    """
    pattern = rf"(?m)^- {re.escape(label)}: .*$"
    note_line = f"- {label}: {value}"

    if re.search(pattern, content):
        return re.sub(pattern, note_line, content, count=1), True

    notes_header = "## Notes\n"
    if notes_header in content:
        return content.replace(notes_header, notes_header + note_line + "\n", 1), True

    return content.rstrip() + f"\n\n## Notes\n{note_line}\n", True


def brand_field_is_unanswered(value: str) -> bool:
    """Return True if *value* represents an unanswered placeholder (empty, TBD, unknown, etc.)."""
    normalized = value.strip().lower()
    return normalized in {"", "tbd", "unknown", "undecided", "unsure"}


def brand_field_is_not_applicable(value: str) -> bool:
    """Return True if *value* explicitly marks a field as not applicable (N/A, na, etc.)."""
    normalized = value.strip().lower()
    return normalized in {"n/a", "na", "not applicable", "none"}


def normalize_brand_value(value: str, fallback: str) -> str:
    """Return *value* if it is answered, otherwise *fallback*."""
    stripped = value.strip()
    if brand_field_is_unanswered(stripped):
        return fallback
    return stripped


def get_missing_new_project_brand_fields(content: str) -> list:
    """Return a list of NEW_PROJECT_BRAND_FIELDS that are still unanswered in *content*."""
    missing_fields = []
    for field_name in NEW_PROJECT_BRAND_FIELDS:
        value = extract_brand_field(content, field_name)
        if brand_field_is_unanswered(value):
            missing_fields.append(field_name)
    return missing_fields


def collect_brand_context(content: str, project_root: str) -> dict:
    """Collect all brand fields and note-driven intake entries from *content* into a dict."""
    field_names = ("Project Name",) + NEW_PROJECT_BRAND_FIELDS
    fields = {field_name: extract_brand_field(content, field_name) for field_name in field_names}
    for field_name in NOTE_DRIVEN_INTAKE_FIELDS:
        fields[field_name] = extract_note_entry(content, field_name)
    if brand_field_is_unanswered(fields.get("Project Name", "")):
        fields["Project Name"] = os.path.basename(os.path.abspath(project_root)) or "Project"
    return fields


def infer_build_surface(context: dict) -> str:
    """Infer a human-readable build surface label (e.g. ``"local-service landing page"``) from *context*."""
    experience_value = context.get("Experience Type", "").strip()
    experience_type = experience_value.lower()
    project_type = context.get("Project Type", "").lower()
    required_sections = context.get("Required Website Sections", "").lower()

    if experience_type and not brand_field_is_not_applicable(experience_type):
        mapped_experiences = {
            "local service business": "local-service landing page",
            "marketing site": "marketing website",
            "portfolio": "portfolio site",
            "ecommerce": "ecommerce storefront",
            "editorial": "editorial website",
            "other": "website experience",
        }
        return mapped_experiences.get(experience_type, experience_value)
    if "content" in project_type or "marketing" in project_type:
        return "marketing website"
    if "hero" in required_sections or "footer" in required_sections or "testimonials" in required_sections:
        return "landing page"
    return "initial product experience"


def infer_explicit_stack_key(value: str) -> str:
    """Map a free-text stack preference to a ``STACK_RECOMMENDATIONS`` key (``"nextjs"``, ``"nuxt"``, ``"astro"``).

    Returns an empty string if no key is recognised.
    """
    normalized = value.strip().lower()
    if not normalized:
        return ""
    if "next" in normalized or "shadcn" in normalized:
        return "nextjs"
    if "nuxt" in normalized:
        return "nuxt"
    if "astro" in normalized or "daisyui" in normalized:
        return "astro"
    return ""


def infer_stack_recommendation_key(context: dict) -> tuple:
    """Determine the best ``STACK_RECOMMENDATIONS`` key for *context*.

    Returns ``(key, inferred: bool)`` where *inferred* is True when the key was
    auto-selected rather than explicitly requested by the user.
    """
    preferred_stack = context.get("Preferred Tech Stack", "")
    explicit_key = infer_explicit_stack_key(preferred_stack)
    if explicit_key and "custom" not in preferred_stack.lower():
        return explicit_key, False

    combined = " ".join(
        [
            context.get("Primary Use Case", ""),
            context.get("Project Type", ""),
            context.get("Experience Type", ""),
            context.get("Technical Constraints", ""),
            context.get("Required Website Sections", ""),
            context.get("SEO Focus", ""),
            context.get("Backend / Data Layer", ""),
        ]
    ).lower()

    if any(token in combined for token in ("nuxt", "vue", "firebase", "mobile-first", "mobile first")):
        return "nuxt", True
    if any(
        token in combined
        for token in (
            "content",
            "marketing",
            "editorial",
            "portfolio",
            "local service",
            "local-service",
            "seo",
            "blog",
            "newsletter",
        )
    ):
        return "astro", True
    return "nextjs", True


def resolve_stack_recommendation(context: dict) -> dict:
    """Return a fully populated stack recommendation dict for the given brand *context*."""
    stack_key, inferred = infer_stack_recommendation_key(context)
    profile = dict(STACK_RECOMMENDATIONS[stack_key])
    requested_stack = context.get("Preferred Tech Stack", "").strip()
    deployment_target = normalize_brand_value(
        context.get("Deployment Target", ""),
        profile["default_deployment"],
    )
    data_layer = normalize_brand_value(
        context.get("Backend / Data Layer", ""),
        profile["default_data_layer"],
    )
    auth_requirement = normalize_brand_value(
        context.get("Authentication Requirement", ""),
        profile["default_auth"],
    )

    if requested_stack and not brand_field_is_unanswered(requested_stack) and not inferred:
        source = "User-selected stack"
        selection_note = (
            f"Requested stack aligns with the current ARMS recommendation: {profile['label']} using "
            f"{profile['framework']} and {profile['ui_system']}."
        )
    else:
        requested_label = requested_stack if requested_stack else "Not specified"
        source = "ARMS recommendation"
        selection_note = (
            f"Requested stack was {requested_label}, so ARMS recommends {profile['label']} for this project type."
        )

    profile.update(
        {
            "key": stack_key,
            "requested_stack": requested_stack or "Not specified",
            "deployment_target": deployment_target,
            "data_layer": data_layer,
            "auth_requirement": auth_requirement,
            "summary": f"{profile['framework']} + {data_layer} + {profile['ui_system']}",
            "source": source,
            "selection_note": selection_note,
            "inferred": inferred,
        }
    )
    return profile


def project_needs_backend_foundation(context: dict, stack_profile: dict) -> bool:
    """Return True if the project context implies a backend/data layer is required."""
    auth_requirement = context.get("Authentication Requirement", "")
    if auth_requirement and not brand_field_is_unanswered(auth_requirement) and not brand_field_is_not_applicable(auth_requirement):
        if "none" not in auth_requirement.lower():
            return True

    combined = " ".join(
        [
            context.get("Primary Use Case", ""),
            context.get("Project Type", ""),
            context.get("Experience Type", ""),
            context.get("Core Features", ""),
        ]
    ).lower()
    if any(
        token in combined
        for token in (
            "saas",
            "app",
            "dashboard",
            "workspace",
            "portal",
            "ecommerce",
            "mobile-first",
            "mobile first",
        )
    ):
        return True

    return stack_profile["key"] in {"nextjs", "nuxt"} and not any(
        token in combined for token in ("marketing", "editorial", "portfolio", "local service")
    )


def format_available_presets() -> str:
    """Return a comma-separated string of available preset names."""
    return ", ".join(sorted(PROJECT_PRESETS))


def infer_project_type_from_primary_use_case(value: str) -> str:
    """Map a Primary Use Case answer to a ``Project Type`` label."""
    normalized = value.strip().lower()
    if "content" in normalized or "marketing" in normalized:
        return "Content / Marketing Site"
    if "saas" in normalized or "app" in normalized or "mobile" in normalized:
        return "Web Application"
    return value.strip()


def infer_logo_status_from_assets(value: str) -> str:
    """Infer a ``Logo Status`` string from a free-text ``Existing Brand Assets`` answer."""
    normalized = value.strip().lower()
    if not normalized:
        return ""

    explicit_logo_flag = re.search(r"logo\s*\((y|n)\)", normalized)
    if explicit_logo_flag:
        return "Existing asset detected" if explicit_logo_flag.group(1) == "y" else "Not yet created"

    if re.search(r"logo\s*[:=-]?\s*(yes|y|existing|have|true)\b", normalized):
        return "Existing asset detected"
    if re.search(r"logo\s*[:=-]?\s*(no|n|none|false)\b", normalized):
        return "Not yet created"
    if any(token in normalized for token in ("logo", "palette", "typography", "existing site")):
        return "Existing assets provided"
    return ""


def parse_structured_answer_line(line: str, aliases: dict, question_map: dict, question_labels: dict) -> tuple:
    """Parse a single answer line and return ``(field_name, value)`` or ``(None, None)``."""
    markdown_match = re.match(r"^- \*\*(.+?)\:\*\*\s*(.*)$", line)
    if markdown_match:
        label = markdown_match.group(1).strip()
        value = markdown_match.group(2).strip()
        return aliases.get(normalize_answer_key(label)), value

    numbered_match = re.match(r"^(\d{1,2})[\).\:-]\s*(.*)$", line)
    if numbered_match:
        question_number = int(numbered_match.group(1))
        remainder = numbered_match.group(2).strip()
        field_name = question_map.get(question_number)
        if not field_name:
            return None, None

        label = question_labels[question_number]
        if normalize_answer_key(remainder).startswith(normalize_answer_key(label)):
            remainder = re.sub(r"^[^:]+:\s*", "", remainder, count=1).strip()
        return field_name, remainder

    key_value_match = re.match(r"^([^:]+):\s*(.*)$", line)
    if key_value_match:
        label = key_value_match.group(1).strip().lstrip("-").strip()
        value = key_value_match.group(2).strip()
        return aliases.get(normalize_answer_key(label)), value

    return None, None


def collect_structured_answer_entries(text: str) -> list:
    """Parse *text* into a list of ``{"field_name": ..., "parts": [...]}`` entry dicts."""
    aliases = build_answer_field_aliases()
    question_map = {number: field_name for number, _, field_name in QUESTION_FIELD_SPECS}
    question_labels = {number: label for number, label, _ in QUESTION_FIELD_SPECS}
    entries = []
    current_entry = None

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            current_entry = None
            continue

        field_name, value = parse_structured_answer_line(line, aliases, question_map, question_labels)
        if field_name:
            current_entry = {"field_name": field_name, "parts": []}
            if value:
                current_entry["parts"].append(value)
            entries.append(current_entry)
            continue

        if current_entry is not None:
            current_entry["parts"].append(line)

    return entries


def parse_structured_answers(text: str) -> dict:
    """Parse free-text answer *text* into a ``{field_name: value}`` dict."""
    if not text.strip():
        return {}

    answers = {}
    for entry in collect_structured_answer_entries(text):
        value = " ".join(part for part in entry["parts"] if part).strip()
        if not value:
            continue
        field_name = entry["field_name"]
        answers[field_name] = normalize_structured_answer(field_name, value)
    return answers


def apply_project_preset(content: str, preset_name: str) -> tuple:
    """Apply a named project preset to *content*, skipping already-answered fields.

    Returns ``(updated_content, changed_fields)``.
    """
    preset = PROJECT_PRESETS[preset_name]
    changed_fields = []

    for field_name, value in preset["fields"].items():
        content, changed = update_brand_field(content, field_name, value, overwrite=False)
        if changed:
            changed_fields.append(field_name)

    return content, changed_fields


def apply_answers_to_brand_content(content: str, answers: dict) -> tuple:
    """Apply a parsed *answers* dict to the BRAND.md *content*.

    Returns ``(updated_content, {"fields": [...], "notes": [...]})``.
    Direct field updates overwrite; derived fields only fill unanswered slots.
    """
    if not answers:
        return content, {"fields": [], "notes": []}

    direct_field_names = {"Project Name", *NEW_PROJECT_BRAND_FIELDS}
    note_fields = set(NOTE_DRIVEN_INTAKE_FIELDS)
    changed_fields = []
    changed_notes = []

    explicit_direct_updates = {}
    derived_updates = {}
    note_updates = {}

    for field_name, value in answers.items():
        if field_name in direct_field_names:
            explicit_direct_updates[field_name] = value
        elif field_name in note_fields:
            note_updates[field_name] = value

    primary_use_case = answers.get("Primary Use Case", "")
    if primary_use_case and brand_field_is_unanswered(extract_brand_field(content, "Project Type")):
        derived_updates["Project Type"] = infer_project_type_from_primary_use_case(primary_use_case)

    brand_comparison = answers.get("Brand Comparison", "")
    if brand_comparison and brand_field_is_unanswered(extract_brand_field(content, "Differentiation")):
        derived_updates["Differentiation"] = brand_comparison

    existing_assets = answers.get("Existing Brand Assets", "")
    if existing_assets and brand_field_is_unanswered(extract_brand_field(content, "Logo Status")):
        inferred_logo_status = infer_logo_status_from_assets(existing_assets)
        if inferred_logo_status:
            derived_updates["Logo Status"] = inferred_logo_status

    non_negotiables = answers.get("Content / Visual Non-Negotiables", "")
    if non_negotiables and brand_field_is_unanswered(extract_brand_field(content, "Technical Constraints")):
        derived_updates["Technical Constraints"] = non_negotiables

    for field_name, value in explicit_direct_updates.items():
        content, changed = update_brand_field(content, field_name, value, overwrite=True)
        if changed:
            changed_fields.append(field_name)

    for field_name, value in derived_updates.items():
        content, changed = update_brand_field(content, field_name, value, overwrite=False)
        if changed:
            changed_fields.append(field_name)

    for label, value in note_updates.items():
        content, changed = upsert_note_entry(content, label, value)
        if changed:
            changed_notes.append(label)

    return content, {"fields": changed_fields, "notes": changed_notes}


def brand_file_requires_bootstrap(content: str) -> bool:
    """Return True if BRAND.md *content* still needs user input before design work can begin."""
    if not content.strip():
        return True
    if any(token in content for token in PLACEHOLDER_BRAND_TOKENS):
        return True
    if is_new_project_brand_questionnaire(content):
        return bool(get_missing_new_project_brand_fields(content))
    return False


def extract_first_meaningful_paragraph(text: str) -> str:
    """Return the first non-heading, non-list prose paragraph from *text*."""
    lines = text.splitlines()
    paragraph = []
    in_code_block = False

    for raw_line in lines:
        line = raw_line.strip()

        if line.startswith("```"):
            in_code_block = not in_code_block
            continue
        if in_code_block:
            continue

        if not line:
            if paragraph:
                break
            continue

        if (
            line.startswith("#")
            or line.startswith("|")
            or line.startswith("- ")
            or line.startswith("* ")
            or line.startswith("> ")
        ):
            if paragraph:
                break
            continue

        paragraph.append(line)

    return " ".join(paragraph).strip()


def detect_existing_project(project_root: str) -> bool:
    """Return True if *project_root* looks like an existing (non-empty) project."""
    substantive_markers = [marker for marker in PROJECT_MARKER_FILES if marker not in {"README.md", "README.mdx"}]
    for marker in substantive_markers:
        if os.path.exists(os.path.join(project_root, marker)):
            return True

    for marker_dir in PROJECT_MARKER_DIRS:
        path = os.path.join(project_root, marker_dir)
        if os.path.isdir(path):
            try:
                with os.scandir(path) as entries:
                    if next(entries, None) is not None:
                        return True
            except OSError:
                continue

    meaningful_entries = [
        name
        for name in os.listdir(project_root)
        if name not in IGNORED_PROJECT_ENTRIES and not name.startswith(".")
    ]
    source_like_entries = [
        name for name in meaningful_entries
        if os.path.splitext(name)[1].lower() in SOURCE_FILE_EXTENSIONS
    ]
    if source_like_entries:
        return True

    substantive_entries = [name for name in meaningful_entries if name not in BOOTSTRAP_ONLY_FILES]
    return len(substantive_entries) >= 2


def detect_workspace_mode(project_root: str, brand_content: str = "") -> str:
    """Return ``"new-project"`` or ``"existing-project"`` based on workspace signals."""
    if brand_content and is_new_project_brand_questionnaire(brand_content):
        return "new-project"
    if detect_existing_project(project_root):
        return "existing-project"
    return "new-project"


def detect_logo_status(project_root: str) -> str:
    """Scan *project_root* for logo/brand image assets and return a status string."""
    candidate_dirs = (
        project_root,
        os.path.join(project_root, "public"),
        os.path.join(project_root, "assets"),
        os.path.join(project_root, "static"),
        os.path.join(project_root, "src", "assets"),
    )

    for directory in candidate_dirs:
        if not os.path.isdir(directory):
            continue
        for root, _, files in os.walk(directory):
            for filename in files:
                lower = filename.lower()
                if lower.endswith((".svg", ".png", ".jpg", ".jpeg", ".webp", ".ico")) and (
                    "logo" in lower or "brand" in lower or "favicon" in lower
                ):
                    return "Existing asset detected"
    return "Pending / no explicit logo asset found"


def parse_pyproject_metadata(content: str) -> dict:
    """Extract ``name``, ``description``, and ``has_scripts`` from pyproject.toml *content*."""
    name_match = re.search(r'(?m)^name\s*=\s*["\']([^"\']+)["\']', content)
    description_match = re.search(r'(?m)^description\s*=\s*["\']([^"\']+)["\']', content)
    scripts_match = re.search(r"(?m)^\[project\.scripts\]", content)
    return {
        "name": name_match.group(1).strip() if name_match else "",
        "description": description_match.group(1).strip() if description_match else "",
        "has_scripts": bool(scripts_match),
    }


def classify_project_type(description_blob: str, frameworks: list, has_project_scripts: bool) -> str:
    """Classify the project as one of: ``"Developer Tooling"``, ``"Web Application"``, ``"Content / Marketing Site"``, ``"Backend Service"``, or ``"Software Project"``."""
    blob = description_blob.lower()
    framework_set = {framework.lower() for framework in frameworks}

    if has_project_scripts or any(
        keyword in blob for keyword in ("cli", "engine", "tool", "tooling", "framework", "sdk", "library", "orchestration")
    ):
        return "Developer Tooling"
    if "next.js" in framework_set or "react" in framework_set or "vue" in framework_set or "svelte" in framework_set or "astro" in framework_set:
        if any(keyword in blob for keyword in ("marketing", "landing page", "brand site", "content", "blog", "seo")):
            return "Content / Marketing Site"
        return "Web Application"
    if any(framework in framework_set for framework in ("fastapi", "flask", "django", "express", "nest")):
        return "Backend Service"
    return "Software Project"


def infer_personality(project_type: str) -> str:
    """Return a default personality string for the given *project_type*."""
    if project_type == "Developer Tooling":
        return "Technical, precise, efficient"
    if project_type == "Content / Marketing Site":
        return "Clear, confident, polished"
    if project_type == "Backend Service":
        return "Reliable, secure, deliberate"
    if project_type == "Web Application":
        return "Clear, modern, trustworthy"
    return "Focused, practical, adaptable"


def infer_voice_tone(project_type: str) -> str:
    """Return a default voice & tone string for the given *project_type*."""
    if project_type == "Developer Tooling":
        return "Direct, technical, low-fluff communication for builders."
    if project_type == "Content / Marketing Site":
        return "Concise, persuasive, and benefits-first without sounding generic."
    if project_type == "Backend Service":
        return "Professional, calm, and confidence-building with clear technical detail."
    if project_type == "Web Application":
        return "Friendly and clear, with emphasis on usability and trust."
    return "Plainspoken and pragmatic."


def infer_primary_audience(project_type: str) -> str:
    """Return a default primary audience string for the given *project_type*."""
    if project_type == "Developer Tooling":
        return "Developers, technical operators, and engineering teams"
    if project_type == "Content / Marketing Site":
        return "Prospective customers, buyers, and evaluators"
    if project_type == "Backend Service":
        return "Internal engineering teams and API consumers"
    if project_type == "Web Application":
        return "End users interacting with the application on web or mobile"
    return "Project stakeholders and end users"


def infer_core_values(project_type: str) -> str:
    """Return a default core values string for the given *project_type*."""
    if project_type == "Developer Tooling":
        return "Automation, consistency, maintainability"
    if project_type == "Content / Marketing Site":
        return "Clarity, credibility, conversion"
    if project_type == "Backend Service":
        return "Reliability, security, scalability"
    if project_type == "Web Application":
        return "Usability, clarity, performance"
    return "Pragmatism, quality, adaptability"


def infer_design_priority(project_type: str) -> str:
    """Return a default design priority string for the given *project_type*."""
    if project_type == "Developer Tooling":
        return "Clarity for technical workflows"
    if project_type == "Content / Marketing Site":
        return "Conversion-focused communication"
    if project_type == "Backend Service":
        return "Operational clarity and trust"
    if project_type == "Web Application":
        return "App-like usability"
    return "Clear information hierarchy"


def infer_brand_context_from_project(project_root: str) -> dict:
    """Scan *project_root* and return an inferred brand context dict.

    Reads ``package.json``, ``pyproject.toml``, ``Cargo.toml``, ``go.mod``,
    ``README.md``, and project instruction files to populate brand, stack,
    and personality fields automatically.
    """
    evidence = []
    frameworks = []
    package_name = ""
    description = ""
    keywords = []
    has_project_scripts = False

    package_json_path = os.path.join(project_root, "package.json")
    package_json_content, package_json_state = read_project_signal_file(package_json_path)
    if package_json_state == "ok":
        evidence.append("package.json")
        try:
            package_data = json.loads(package_json_content)
            package_name = str(package_data.get("name", "")).strip()
            description = str(package_data.get("description", "")).strip()
            keywords = [str(keyword).strip() for keyword in package_data.get("keywords", []) if str(keyword).strip()]
            deps = set((package_data.get("dependencies") or {}).keys()) | set((package_data.get("devDependencies") or {}).keys())
            if "next" in deps:
                frameworks.append("Next.js")
            if "react" in deps:
                frameworks.append("React")
            if "vue" in deps:
                frameworks.append("Vue")
            if "@angular/core" in deps:
                frameworks.append("Angular")
            if "svelte" in deps or "@sveltejs/kit" in deps:
                frameworks.append("Svelte")
            if "astro" in deps:
                frameworks.append("Astro")
            if "express" in deps:
                frameworks.append("Express")
            if "@nestjs/core" in deps:
                frameworks.append("Nest")
        except json.JSONDecodeError:
            evidence[-1] = "package.json (unparsed)"
    elif package_json_state == "too_large":
        evidence.append("package.json (skipped: too large)")
    elif package_json_state == "unreadable":
        evidence.append("package.json (unreadable)")

    pyproject_path = os.path.join(project_root, "pyproject.toml")
    pyproject_content, pyproject_state = read_project_signal_file(pyproject_path)
    if pyproject_state == "ok" and pyproject_content:
        evidence.append("pyproject.toml")
        pyproject_metadata = parse_pyproject_metadata(pyproject_content)
        package_name = package_name or pyproject_metadata["name"]
        description = description or pyproject_metadata["description"]
        has_project_scripts = has_project_scripts or pyproject_metadata["has_scripts"]
        lowered = pyproject_content.lower()
        if "fastapi" in lowered:
            frameworks.append("FastAPI")
        if "flask" in lowered:
            frameworks.append("Flask")
        if "django" in lowered:
            frameworks.append("Django")
        if "typer" in lowered or "click" in lowered:
            frameworks.append("Python CLI")
    elif pyproject_state == "too_large":
        evidence.append("pyproject.toml (skipped: too large)")
    elif pyproject_state == "unreadable":
        evidence.append("pyproject.toml (unreadable)")

    cargo_toml_path = os.path.join(project_root, "Cargo.toml")
    cargo_content, cargo_state = read_project_signal_file(cargo_toml_path)
    if cargo_state == "ok" and cargo_content:
        evidence.append("Cargo.toml")
        cargo_name_match = re.search(r'(?m)^name\s*=\s*"([^"]+)"', cargo_content)
        cargo_description_match = re.search(r'(?m)^description\s*=\s*"([^"]+)"', cargo_content)
        if cargo_name_match and not package_name:
            package_name = cargo_name_match.group(1).strip()
        if cargo_description_match and not description:
            description = cargo_description_match.group(1).strip()
        frameworks.append("Rust")
    elif cargo_state == "too_large":
        evidence.append("Cargo.toml (skipped: too large)")
    elif cargo_state == "unreadable":
        evidence.append("Cargo.toml (unreadable)")

    go_mod_path = os.path.join(project_root, "go.mod")
    go_mod_content, go_mod_state = read_project_signal_file(go_mod_path)
    if go_mod_state == "ok" and go_mod_content:
        evidence.append("go.mod")
        module_match = re.search(r"(?m)^module\s+(.+)$", go_mod_content)
        if module_match and not package_name:
            package_name = module_match.group(1).strip().split("/")[-1]
        frameworks.append("Go")
    elif go_mod_state == "too_large":
        evidence.append("go.mod (skipped: too large)")
    elif go_mod_state == "unreadable":
        evidence.append("go.mod (unreadable)")

    readme_path = os.path.join(project_root, "README.md")
    readme_content, readme_state = read_project_signal_file(readme_path)
    readme_summary = ""
    if readme_state == "ok" and readme_content:
        evidence.append("README.md")
        readme_summary = extract_first_meaningful_paragraph(readme_content)
    elif readme_state == "too_large":
        evidence.append("README.md (skipped: too large)")
    elif readme_state == "unreadable":
        evidence.append("README.md (unreadable)")

    project_instruction_summary = ""
    project_instruction_candidates = (
        "GEMINI.md",
        "gemini.md",
        os.path.join(".gemini", "GEMINI.md"),
        os.path.join(".gemini", "gemini.md"),
        os.path.join(".github", "copilot-instructions.md"),
    )
    for gemini_filename in project_instruction_candidates:
        gemini_path = os.path.join(project_root, gemini_filename)
        gemini_content, gemini_state = read_project_signal_file(gemini_path)
        if gemini_state == "ok" and gemini_content:
            evidence.append(gemini_filename)
            project_instruction_summary = extract_first_meaningful_paragraph(gemini_content)
            break
        if gemini_state == "too_large":
            evidence.append(f"{gemini_filename} (skipped: too large)")
            continue
        if gemini_state == "unreadable":
            evidence.append(f"{gemini_filename} (unreadable)")

    if os.path.isdir(os.path.join(project_root, "src")):
        evidence.append("src/")
    if os.path.isdir(os.path.join(project_root, "app")):
        evidence.append("app/")
    if os.path.isdir(os.path.join(project_root, "pages")):
        evidence.append("pages/")

    frameworks = list(dict.fromkeys(frameworks))
    directory_name = os.path.basename(os.path.abspath(project_root))
    project_name = package_name or directory_name
    description_blob = " ".join(filter(None, [description, readme_summary, project_instruction_summary, " ".join(keywords)]))
    project_type = classify_project_type(description_blob, frameworks, has_project_scripts)

    if description:
        mission = description.rstrip(".") + "."
    elif readme_summary:
        mission = readme_summary.rstrip(".") + "."
    elif project_instruction_summary:
        mission = project_instruction_summary.rstrip(".") + "."
    else:
        mission = f"{project_name} is an existing {project_type.lower()} repository."

    if readme_summary and readme_summary.lower() != mission.lower():
        differentiation = readme_summary.rstrip(".") + "."
    elif project_instruction_summary and project_instruction_summary.lower() != mission.lower():
        differentiation = project_instruction_summary.rstrip(".") + "."
    elif description:
        differentiation = description.rstrip(".") + "."
    else:
        differentiation = f"Repository signals suggest a {project_type.lower()} focused on practical delivery."

    stack_summary = ", ".join(frameworks) if frameworks else "No dominant framework detected"

    return {
        "project_name": project_name,
        "mission": mission,
        "vision": "TBD - confirm the long-term product direction with the project owner.",
        "personality": infer_personality(project_type),
        "voice_tone": infer_voice_tone(project_type),
        "primary_audience": infer_primary_audience(project_type),
        "core_values": infer_core_values(project_type),
        "differentiation": differentiation,
        "color_palette": "TBD - no explicit palette found in repository files",
        "typography": "TBD - no explicit font system found in repository files",
        "logo_status": detect_logo_status(project_root),
        "visual_direction": "Undecided - confirm preferred light/dark direction",
        "project_type": project_type,
        "design_priority": infer_design_priority(project_type),
        "notes": [
            "Auto-generated from existing repository signals. Review and correct inferred fields.",
            f"Evidence reviewed: {', '.join(dict.fromkeys(evidence)) or 'directory structure only'}",
            f"Detected stack: {stack_summary}",
        ],
    }


def render_inferred_brand_context(project_root: str) -> str:
    """Render a BRAND.md template pre-filled with inferred context from *project_root*."""
    context = infer_brand_context_from_project(project_root)
    notes = "\n".join(f"- {note}" for note in context["notes"])
    return f"""# Brand Context
> Managed by ARMS Engine. Auto-generated from an existing project repository.
> Review inferred fields before relying on this as final brand truth.

---

## Identity
- **Project Name:** {context["project_name"]}
- **Mission:** {context["mission"]}
- **Vision:** {context["vision"]}
- **Personality:** {context["personality"]}
- **Voice & Tone:** {context["voice_tone"]}

## Positioning
- **Primary Audience:** {context["primary_audience"]}
- **Core Values:** {context["core_values"]}
- **Differentiation:** {context["differentiation"]}

## Visual Identity
- **Color Palette:** {context["color_palette"]}
- **Typography:** {context["typography"]}
- **Logo Status:** {context["logo_status"]}
- **Visual Direction:** {context["visual_direction"]}

## Use Case Implications
- **Project Type:** {context["project_type"]}
- **Design Priority:** {context["design_priority"]}

## Notes
{notes}
"""


def render_new_project_brand_questionnaire(project_root: str) -> str:
    """Render a blank BRAND.md questionnaire template for a new project at *project_root*."""
    project_name = os.path.basename(os.path.abspath(project_root)) or "TBD"
    return f"""# Brand Context
> Managed by ARMS Engine. Referenced by: Frontend, SEO, and Media agents.
> New project detected. Fill in the questions below before design-oriented work begins.

---

## Identity
- **Project Name:** {project_name}
- **Mission:** TBD
- **Vision:** TBD
- **Personality:** TBD
- **Voice & Tone:** TBD

## Positioning
- **Primary Audience:** TBD
- **Core Values:** TBD
- **Differentiation:** TBD

## Visual Identity
- **Color Palette:** TBD
- **Typography:** TBD
- **Logo Status:** TBD
- **Visual Direction:** TBD

## Use Case Implications
- **Project Type:** TBD
- **Design Priority:** TBD

## Initial Technical Direction
- **Preferred Tech Stack:** TBD
- **Deployment Target:** TBD
- **Backend / Data Layer:** TBD
- **Authentication Requirement:** TBD
- **Technical Constraints:** TBD

## Initial Website / Landing Page Brief
- **Experience Type:** TBD
- **Industry / Business Niche:** TBD
- **Service Area / Local SEO Target:** TBD
- **Required Website Sections:** TBD
- **Primary Calls to Action:** TBD
- **Icon System:** TBD
- **Image Requirements:** TBD
- **SEO Focus:** TBD

## Notes
- Answer these before approving design or marketing work:
- What is the exact project name or working title?
- What problem does the project solve, and for whom?
- What is the long-term vision?
- Pick up to 3 brand personality words.
- What should the voice sound like?
- Who is the primary audience?
- What core values should the brand signal?
- What makes it meaningfully different from alternatives?
- Do you already have a logo, color palette, typography, or an existing site?
- Should the visual direction default to light, dark, system, or something else?
- What stack, deployment target, auth approach, and hard technical constraints should ARMS plan around?
- If this is a website or landing page, what type of experience is it and what industry does it serve?
- Which sections, CTAs, icons, images, and SEO priorities are mandatory?
- If a website brief item does not apply, explicitly write N/A so ARMS can treat the questionnaire as complete.
"""


def render_new_project_brand_prompt(missing_fields: list = None) -> str:
    """Build the brand-intake prompt shown to users who need to fill in BRAND.md."""
    brand_questions = "\n".join(NEW_PROJECT_BRAND_QUESTIONS)
    tech_stack_questions = "\n".join(NEW_PROJECT_TECH_STACK_QUESTIONS)
    website_brief_questions = "\n".join(NEW_PROJECT_WEBSITE_BRIEF_QUESTIONS)
    preset_block = (
        "Fast paths:\n"
        f"- Apply a preset: `arms init --preset <name>` (available: {format_available_presets()})\n"
        "- Apply structured answers: `arms init --answers-file path/to/answers.md`\n"
        "- Or pass a short block inline: `arms init --answers-text \"Mission: ...\"`\n"
        "- Supported answer formats: `Field: value`, `- **Field:** value`, or numbered questionnaire responses.\n\n"
    )
    missing_block = ""
    if missing_fields:
        missing_block = (
            "Still incomplete in `.arms/BRAND.md`:\n"
            + "\n".join(f"- {field}" for field in missing_fields)
            + "\n\n"
        )
    return (
        "📝 Brand Context is required for a new / empty project.\n"
        "Fill the unanswered fields in `.arms/BRAND.md` or answer these in one block, then re-run `arms init` to resume:\n\n"
        f"{preset_block}"
        f"{missing_block}"
        f"{brand_questions}\n\n"
        "After Brand Context, confirm the initial tech stack:\n\n"
        f"{tech_stack_questions}\n\n"
        "If this project includes a website or landing page, also answer this brief. Use `N/A` where it does not apply:\n\n"
        f"{website_brief_questions}\n\n"
        "The Brand Context and technical-direction questionnaire is stored in `.arms/BRAND.md`."
    )


def initialize_brand_context(project_root: str) -> dict:
    """Bootstrap or reuse BRAND.md for *project_root*.

    Returns a status dict with a ``"status"`` key (``"existing"``, ``"inferred"``,
    or ``"questions_required"``) and an optional ``"prompt"`` key.
    """
    brand_path = WorkspacePaths(project_root).brand

    existing_content = read_text_file(brand_path)
    if existing_content:
        if is_new_project_brand_questionnaire(existing_content):
            missing_fields = get_missing_new_project_brand_fields(existing_content)
            if missing_fields:
                print("📝 New-project BRAND.md is still incomplete. Reusing saved questionnaire.")
                return {
                    "status": "questions_required",
                    "prompt": render_new_project_brand_prompt(missing_fields),
                }
            print("✅ New-project BRAND.md is complete. Continuing initialization from saved answers.")
            return {"status": "existing"}
        if not brand_file_requires_bootstrap(existing_content):
            return {"status": "existing"}

    if detect_existing_project(project_root):
        print("🎨 Generating BRAND.md from existing project context...")
        with open(brand_path, "w", encoding="utf-8") as f:
            f.write(render_inferred_brand_context(project_root))
        print("📢 BRAND.md generated from repository signals. Review inferred fields and refine where needed.")
        return {"status": "inferred"}

    print("🎨 Initializing new-project BRAND.md questionnaire...")
    with open(brand_path, "w", encoding="utf-8") as f:
        f.write(render_new_project_brand_questionnaire(project_root))
    print("📢 BRAND.md created for a new project. User answers are required before high-fidelity brand work begins.")
    return {
        "status": "questions_required",
        "prompt": render_new_project_brand_prompt(),
    }


def apply_brand_inputs(project_root: str, preset_name: str = "", answers_text: str = "") -> bool:
    """Apply a *preset_name* and/or *answers_text* to BRAND.md in *project_root*.

    Returns True if any changes were written to disk.
    """
    brand_path = WorkspacePaths(project_root).brand
    content = read_text_file(brand_path)
    if not content:
        return False

    updated_content = content
    changed = False

    if preset_name:
        updated_content, changed_fields = apply_project_preset(updated_content, preset_name)
        if changed_fields:
            changed = True
            print(
                f"🧩 Applied preset '{preset_name}' to .arms/BRAND.md "
                f"({', '.join(changed_fields)})."
            )
        else:
            print(f"ℹ️  Preset '{preset_name}' had no unanswered fields left to fill.")

    if answers_text.strip():
        answers = parse_structured_answers(answers_text)
        if answers:
            updated_content, change_summary = apply_answers_to_brand_content(updated_content, answers)
            changed_fields = change_summary["fields"]
            changed_notes = change_summary["notes"]
            if changed_fields or changed_notes:
                changed = True
                summary_bits = []
                if changed_fields:
                    summary_bits.append(f"fields: {', '.join(changed_fields)}")
                if changed_notes:
                    summary_bits.append(f"notes: {', '.join(changed_notes)}")
                print(f"🧾 Applied structured answers to .arms/BRAND.md ({'; '.join(summary_bits)}).")
            else:
                print("ℹ️  Structured answers were recognized, but they did not change .arms/BRAND.md.")
        else:
            print("⚠️  No recognizable structured answers found. Use `Field: value` or numbered responses.")

    if changed and updated_content != content:
        with open(brand_path, "w", encoding="utf-8") as f:
            f.write(updated_content)

    return changed
