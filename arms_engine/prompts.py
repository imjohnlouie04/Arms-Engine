import os
import textwrap

from .brand import (
    brand_field_is_unanswered,
    brand_file_requires_bootstrap,
    collect_brand_context,
    detect_workspace_mode,
    infer_build_surface,
    normalize_brand_value,
    project_needs_backend_foundation,
    read_text_file,
    resolve_stack_recommendation,
)
from .session import assess_token_budget, format_token_budget_message, write_text_atomic


GENERATED_PROMPTS_HEADER = """# ARMS Generated Prompts

> Managed by ARMS Engine. Regenerated from `.arms/BRAND.md` during `arms init`.
> Update the brand brief and re-run `arms init` to refresh these prompts.
"""
CONTEXT_SYNTHESIS_HEADER = """# ARMS Context Synthesis

> Managed by ARMS Engine. Regenerated from `.arms/BRAND.md` during `arms init`.
> This file condenses the approved brand and stack answers into an AI-ready project brief.
"""
CONTEXT_SYNTHESIS_TOKEN_BUDGET = 2200
GENERATED_PROMPTS_TOKEN_BUDGET = 1600


def render_markdown_bullets(items, empty_message):
    if not items:
        return f"- {empty_message}"
    return "\n".join(f"- {item}" for item in items)


def render_agent_prompt_section(title, agent, prompt, skill="—"):
    lines = [
        f"## {title}",
        f"**Assigned Agent:** `{agent}`",
    ]
    if skill and skill != "—":
        lines.append(f"**Active Skill:** `{skill}`")
    lines.append(f"**Copilot CLI:** `/agent {agent}`")
    lines.append("```text")
    lines.append(prompt)
    lines.append("```")
    return "\n".join(lines)


def build_startup_tasks(data):
    rows = []
    workspace_mode = data["workspace_mode"]
    project_type = data["project_type"].lower()
    build_surface = data["build_surface"].lower()
    is_existing_project = workspace_mode == "existing-project"
    is_ui_project = any(
        token in build_surface
        for token in ("website", "landing page", "storefront", "portfolio", "experience")
    ) or "web application" in project_type or "content / marketing site" in project_type

    def add(task, agent, dependencies="—"):
        rows.append(
            {
                "task": task,
                "agent": agent,
                "dependencies": dependencies,
            }
        )

    backend_needed = project_needs_backend_foundation(data["context"], data["stack_profile"])
    if is_existing_project:
        add("Audit the current product scope, repo signals, and immediate delivery goals", "arms-product-agent")
        add(
            f"Map the current {data['stack_profile']['framework']} architecture, tooling, and environment constraints",
            "arms-devops-agent",
            "#1",
        )
        if is_ui_project:
            add(
                f"Review the current {data['build_surface']} and prioritize the first high-impact UI improvements",
                "arms-frontend-agent",
                "#1, #2",
            )
        if backend_needed:
            add("Review the current data model, schema boundaries, and migration risks", "arms-data-agent", "#2")
            backend_dependencies = "#2, #4" if is_ui_project else "#2, #3"
            add(
                "Review authentication and core backend integration points for the existing implementation",
                "arms-backend-agent",
                backend_dependencies,
            )
            add(
                "Audit auth, access control, and secret handling risks before new implementation work",
                "arms-security-agent",
                "#4, #5" if is_ui_project else "#3, #4",
            )
        if "content / marketing site" in project_type or "website" in build_surface or "landing page" in build_surface:
            seo_dependencies = "#3" if is_ui_project else "#2"
            add("Review metadata, content hierarchy, and SEO gaps in the current experience", "arms-seo-agent", seo_dependencies)

        qa_dependencies = ["#2"]
        if is_ui_project:
            qa_dependencies.append("#3")
        if backend_needed:
            qa_dependencies.extend(["#4", "#5", "#6"] if is_ui_project else ["#3", "#4", "#5"])
        elif "content / marketing site" in project_type or "website" in build_surface or "landing page" in build_surface:
            qa_dependencies.append("#4" if is_ui_project else "#3")
        add(
            "Run QA pre-flight against the current flows and highest-risk regression areas",
            "arms-qa-agent",
            ", ".join(dict.fromkeys(qa_dependencies)),
        )
        return rows

    add("Create a concise product charter, scope summary, and success metrics", "arms-product-agent")
    add(
        f"Scaffold the {data['stack_profile']['framework']} foundation with {data['stack_profile']['ui_system']}",
        "arms-devops-agent",
        "#1",
    )
    add(
        f"Design the first {data['build_surface']} and shared UI system",
        "arms-frontend-agent",
        "#1, #2",
    )

    if backend_needed:
        add("Design the initial data model, schema boundaries, and access patterns", "arms-data-agent", "#2")
        add("Implement authentication and core backend integration points", "arms-backend-agent", "#2, #4")
        add("Review auth, data access, and secrets handling assumptions", "arms-security-agent", "#4, #5")

    add("Generate the first brand asset kit and Nano Banana landing-page imagery", "arms-media-agent", "#1")
    add("Create the SEO brief, metadata direction, and content hierarchy", "arms-seo-agent", "#1, #3")

    qa_dependencies = "#3, #5"
    if backend_needed:
        qa_dependencies = "#3, #5, #6, #8"
    add("Run QA pre-flight on the scaffold and kickoff flows", "arms-qa-agent", qa_dependencies)
    return rows


def render_startup_tasks_content(data):
    rows = build_startup_tasks(data)
    lines = [
        "### Priority 1",
        "| # | Task | Assigned Agent | Active Skill | Dependencies | Status |",
        "|---|------|----------------|--------------|--------------|--------|",
    ]
    for index, row in enumerate(rows, start=1):
        lines.append(
            f"| {index} | {row['task']} | {row['agent']} | — | {row['dependencies']} | Pending |"
        )
    return "\n".join(lines)


def build_context_synthesis_data(project_root):
    brand_path = os.path.join(project_root, ".arms/BRAND.md")
    brand_content = read_text_file(brand_path)
    if not brand_content.strip() or brand_file_requires_bootstrap(brand_content):
        return None

    workspace_mode = detect_workspace_mode(project_root, brand_content)
    context = collect_brand_context(brand_content, project_root)
    stack_profile = resolve_stack_recommendation(context)
    project_name = normalize_brand_value(context.get("Project Name", ""), "Project")
    mission = normalize_brand_value(context.get("Mission", ""), "Clarify the project's primary purpose.")
    vision = normalize_brand_value(context.get("Vision", ""), "Clarify the long-term direction.")
    personality = normalize_brand_value(context.get("Personality", ""), "Distinctive and cohesive")
    voice_tone = normalize_brand_value(context.get("Voice & Tone", ""), "Clear, confident, and audience-appropriate")
    primary_audience = normalize_brand_value(context.get("Primary Audience", ""), "Target audience not yet specified")
    differentiation = normalize_brand_value(
        context.get("Differentiation", ""),
        "Differentiate clearly from adjacent alternatives",
    )
    visual_direction = normalize_brand_value(context.get("Visual Direction", ""), "Undecided")
    project_type = normalize_brand_value(context.get("Project Type", ""), "Project type not yet specified")
    design_priority = normalize_brand_value(
        context.get("Design Priority", ""),
        "Clear hierarchy and execution quality",
    )
    primary_use_case = normalize_brand_value(context.get("Primary Use Case", ""), "Primary use case not yet captured")
    core_features = normalize_brand_value(context.get("Core Features", ""), "Core features not yet captured")
    monetization_model = normalize_brand_value(
        context.get("Goal / Monetization Model", ""),
        "Goal / monetization model not yet captured",
    )
    reference_brand = normalize_brand_value(
        context.get("Reference Brand", ""),
        "No explicit reference brand provided",
    )
    brand_comparison = normalize_brand_value(
        context.get("Brand Comparison", ""),
        "No explicit brand comparison provided",
    )
    existing_brand_assets = normalize_brand_value(
        context.get("Existing Brand Assets", ""),
        "No explicit asset inventory provided",
    )
    logo_status = normalize_brand_value(context.get("Logo Status", ""), "Pending / unspecified")
    experience_type = normalize_brand_value(context.get("Experience Type", ""), "N/A")
    business_niche = normalize_brand_value(
        context.get("Industry / Business Niche", ""),
        "Industry not yet specified",
    )
    service_area = normalize_brand_value(
        context.get("Service Area / Local SEO Target", ""),
        "No explicit service area captured",
    )
    required_sections = normalize_brand_value(
        context.get("Required Website Sections", ""),
        "Use the most suitable structure for the project type",
    )
    primary_ctas = normalize_brand_value(
        context.get("Primary Calls to Action", ""),
        "Define the primary conversion actions",
    )
    image_requirements = normalize_brand_value(
        context.get("Image Requirements", ""),
        "Create the minimum viable supporting image set",
    )
    seo_focus = normalize_brand_value(
        context.get("SEO Focus", ""),
        "Use semantic HTML, metadata, and descriptive copy",
    )
    technical_constraints = normalize_brand_value(
        context.get("Technical Constraints", ""),
        "No hard constraints captured",
    )
    content_non_negotiables = normalize_brand_value(
        context.get("Content / Visual Non-Negotiables", ""),
        "No additional content or visual non-negotiables captured",
    )

    icon_system_value = context.get("Icon System", "")
    if brand_field_is_unanswered(icon_system_value):
        icon_system = stack_profile["default_icon_system"]
    else:
        icon_system = icon_system_value.strip()

    build_surface = infer_build_surface(context)
    confirmed = []
    needs_attention = []

    if stack_profile["inferred"]:
        needs_attention.append(stack_profile["selection_note"])
    else:
        confirmed.append(stack_profile["selection_note"])

    if not brand_field_is_unanswered(context.get("Personality", "")):
        confirmed.append(f"Brand personality is defined as {personality}.")
    else:
        needs_attention.append("Brand personality is still vague; tighten the tone before visual polish work.")

    if not brand_field_is_unanswered(context.get("Core Features", "")):
        confirmed.append(f"Core features are captured: {core_features}.")
    else:
        needs_attention.append("Core features are still open-ended; product scope should tighten them first.")

    if not brand_field_is_unanswered(context.get("Deployment Target", "")):
        confirmed.append(f"Deployment target is explicit: {stack_profile['deployment_target']}.")
    else:
        needs_attention.append(
            f"Deployment target was not specified, so ARMS defaulted to {stack_profile['deployment_target']}."
        )

    if brand_field_is_unanswered(context.get("Existing Brand Assets", "")):
        needs_attention.append("Existing brand assets were not provided; media work should treat logo and imagery as net-new.")
    else:
        confirmed.append(f"Existing brand assets are documented: {existing_brand_assets}.")

    if brand_field_is_unanswered(context.get("Authentication Requirement", "")):
        needs_attention.append(
            f"Authentication was not specified, so the recommendation falls back to {stack_profile['auth_requirement']}."
        )
    else:
        confirmed.append(f"Authentication requirement is captured: {stack_profile['auth_requirement']}.")

    data = {
        "workspace_mode": workspace_mode,
        "context_policy": (
            "Infer from repository signals, preserve existing implementation context, and ask only for missing decisions."
            if workspace_mode == "existing-project"
            else "Use approved intake answers as source of truth and keep the starter context lean until implementation begins."
        ),
        "prompt_strategy": (
            "Thin prompts that reference synthesis and focus on audits, deltas, and safe changes."
            if workspace_mode == "existing-project"
            else "Thin prompts that reference synthesis and focus on bootstrap work, scaffold quality, and first-pass implementation."
        ),
        "context": context,
        "stack_profile": stack_profile,
        "project_name": project_name,
        "mission": mission,
        "vision": vision,
        "personality": personality,
        "voice_tone": voice_tone,
        "primary_audience": primary_audience,
        "differentiation": differentiation,
        "visual_direction": visual_direction,
        "project_type": project_type,
        "design_priority": design_priority,
        "primary_use_case": primary_use_case,
        "core_features": core_features,
        "monetization_model": monetization_model,
        "reference_brand": reference_brand,
        "brand_comparison": brand_comparison,
        "existing_brand_assets": existing_brand_assets,
        "logo_status": logo_status,
        "experience_type": experience_type,
        "business_niche": business_niche,
        "service_area": service_area,
        "required_sections": required_sections,
        "primary_ctas": primary_ctas,
        "image_requirements": image_requirements,
        "seo_focus": seo_focus,
        "technical_constraints": technical_constraints,
        "content_non_negotiables": content_non_negotiables,
        "icon_system": icon_system,
        "build_surface": build_surface,
        "confirmed_signals": confirmed,
        "needs_attention_signals": needs_attention,
    }
    data["startup_tasks"] = build_startup_tasks(data)
    return data


def build_media_asset_brief(data):
    surface = data["build_surface"]
    showcase_focus = (
        "Include at least two images that showcase their best work, strongest outcomes, or most impressive finished results."
    )
    return textwrap.dedent(
        f"""\
        Use nano-banana-pro for image generation.
        Generate at least five production-ready images that directly support the first {surface}.
        Cover the hero, supporting content sections, and proof/showcase areas so the frontend can place assets immediately.
        {showcase_focus}
        Keep the set visually consistent and tailored to {data['business_niche']} rather than relying on generic stock-photo patterns.
        """
    ).strip()


def render_context_synthesis(project_root):
    data = build_context_synthesis_data(project_root)
    if data is None:
        return None

    stack_profile = data["stack_profile"]
    workspace_mode_label = "Existing Repository" if data["workspace_mode"] == "existing-project" else "New Project"
    kickoff_summary = "\n".join(
        f"{index}. **{row['agent']}** — {row['task']}"
        for index, row in enumerate(data["startup_tasks"], start=1)
    )

    return (
        CONTEXT_SYNTHESIS_HEADER.strip()
        + "\n\n## Execution Profile\n"
        + textwrap.dedent(
            f"""\
            - **Workspace Mode:** {workspace_mode_label}
            - **Context Policy:** {data['context_policy']}
            - **Prompt Strategy:** {data['prompt_strategy']}
            - **Build Surface:** {data['build_surface']}
            """
        ).strip()
        + "\n\n## Core Brief\n"
        + textwrap.dedent(
            f"""\
            - **Project Name:** {data['project_name']}
            - **Mission:** {data['mission']}
            - **Vision:** {data['vision']}
            - **Primary Audience:** {data['primary_audience']}
            - **Primary Use Case:** {data['primary_use_case']}
            - **Core Features:** {data['core_features']}
            - **Differentiation:** {data['differentiation']}
            """
        ).strip()
        + "\n\n## Build Profile\n"
        + textwrap.dedent(
            f"""\
            - **Requested Stack:** {stack_profile['requested_stack']}
            - **Recommended Stack:** {stack_profile['label']}
            - **Framework:** {stack_profile['framework']}
            - **UI System:** {stack_profile['ui_system']}
            - **Backend / Data Layer:** {stack_profile['data_layer']}
            - **Deployment Target:** {stack_profile['deployment_target']}
            - **Authentication:** {stack_profile['auth_requirement']}
            - **Recommendation Source:** {stack_profile['source']}
            - **Recommendation Note:** {stack_profile['selection_note']}
            """
        ).strip()
        + "\n\n## Experience & Delivery Signals\n"
        + textwrap.dedent(
            f"""\
            - **Project Type:** {data['project_type']}
            - **Experience Type:** {data['experience_type']}
            - **Personality:** {data['personality']}
            - **Voice & Tone:** {data['voice_tone']}
            - **Visual Direction:** {data['visual_direction']}
            - **Required Sections:** {data['required_sections']}
            - **Primary CTAs:** {data['primary_ctas']}
            - **SEO Focus:** {data['seo_focus']}
            - **Technical Constraints:** {data['technical_constraints']}
            - **Content / Visual Non-Negotiables:** {data['content_non_negotiables']}
            - **Icon System:** {data['icon_system']}
            - **Logo Status:** {data['logo_status']}
            - **Existing Brand Assets:** {data['existing_brand_assets']}
            """
        ).strip()
        + "\n\n## Confidence Signals\n### Confirmed\n"
        + render_markdown_bullets(data["confirmed_signals"], "Core project signals still need confirmation.")
        + "\n\n### Needs Attention\n"
        + render_markdown_bullets(data["needs_attention_signals"], "No major gaps detected.")
        + "\n\n## Startup Sequence\n"
        + kickoff_summary
        + "\n"
    )


def maybe_print_budget_warning(label, content, budget):
    budget_assessment = assess_token_budget(content, budget)
    if budget_assessment["status"] != "ok":
        print(format_token_budget_message(label, budget_assessment))


def sync_context_synthesis(project_root):
    synthesis_path = os.path.join(project_root, ".arms/CONTEXT_SYNTHESIS.md")
    synthesis_content = render_context_synthesis(project_root)

    if synthesis_content is None:
        if os.path.exists(synthesis_path):
            os.remove(synthesis_path)
            print("🧹 Removed stale .arms/CONTEXT_SYNTHESIS.md because the brand brief is incomplete.")
        return False

    write_text_atomic(synthesis_path, synthesis_content)
    print("📋 Generated .arms/CONTEXT_SYNTHESIS.md from the approved brand and stack context.")
    maybe_print_budget_warning(".arms/CONTEXT_SYNTHESIS.md", synthesis_content, CONTEXT_SYNTHESIS_TOKEN_BUDGET)
    return True


def render_generated_prompts(project_root):
    data = build_context_synthesis_data(project_root)
    if data is None:
        return None

    stack_profile = data["stack_profile"]
    backend_needed = project_needs_backend_foundation(data["context"], stack_profile)
    is_existing_project = data["workspace_mode"] == "existing-project"
    build_action = "review the current implementation and ship the highest-impact next improvement" if is_existing_project else f"create the first production-quality {data['build_surface']}"
    devops_action = "audit the existing stack, tooling, and deployment path before changing infrastructure" if is_existing_project else f"scaffold {data['project_name']} using {stack_profile['framework']} with {stack_profile['ui_system']}"
    frontend_action = f"review the current {data['build_surface']} and improve the highest-impact user flow" if is_existing_project else f"create the first responsive {data['build_surface']}"
    qa_action = "focus on regression risk and current production-critical flows" if is_existing_project else "focus on scaffold correctness and kickoff flows"

    master_prompt = textwrap.dedent(
        f"""\
        Read `.arms/CONTEXT_SYNTHESIS.md` first.
        For {data['project_name']}, {build_action}.
        Use {stack_profile['framework']} + {stack_profile['ui_system']}.
        Honor: {data['technical_constraints']} / {data['content_non_negotiables']}.
        """
    ).strip()

    product_prompt = textwrap.dedent(
        f"""\
        Read `.arms/CONTEXT_SYNTHESIS.md`.
        Turn it into a concise charter for {data['project_name']}.
        Prioritize around {data['core_features']} and flag the highest-risk ambiguities early.
        """
    ).strip()

    devops_prompt = textwrap.dedent(
        f"""\
        Read `.arms/CONTEXT_SYNTHESIS.md`.
        {devops_action}.
        Keep the recommendation anchored to {stack_profile['data_layer']}, {stack_profile['deployment_target']}, and {stack_profile['auth_requirement']}.
        """
    ).strip()

    frontend_prompt = textwrap.dedent(
        f"""\
        Read `.arms/CONTEXT_SYNTHESIS.md`.
        {frontend_action}.
        Keep the UI aligned to {data['personality']} / {data['voice_tone']} / {data['visual_direction']}.
        Structure around {data['required_sections']} and optimize for {data['primary_ctas']}.
        """
    ).strip()

    frontend_skill = "ui-ux-pro-max" if is_existing_project else "frontend-design"
    sections = [
        GENERATED_PROMPTS_HEADER.strip(),
        (
            "## Usage\n"
            "- Read `.arms/CONTEXT_SYNTHESIS.md` first.\n"
            "- These prompts stay intentionally thin so the synthesis file remains the single dense context source.\n"
            "- Use the listed specialist agent for each prompt.\n"
            "- If the user is already replying inside one of these generated/custom specialist prompts, treat clarifying questions and issue follow-ups as continuation of that active task unless they introduce a net-new ask.\n"
            "- Do not run specialist implementation prompts with `arms-main-agent`; keep `arms-main-agent` for orchestration only."
        ),
        render_agent_prompt_section("Orchestrator Prompt", "arms-main-agent", master_prompt, "arms-orchestrator"),
        render_agent_prompt_section("Product Kickoff Prompt", "arms-product-agent", product_prompt),
        render_agent_prompt_section("DevOps Prompt", "arms-devops-agent", devops_prompt, "devops-orchestrator"),
        render_agent_prompt_section("Frontend Prompt", "arms-frontend-agent", frontend_prompt, frontend_skill),
    ]

    if backend_needed:
        data_prompt = textwrap.dedent(
            f"""\
            Read `.arms/CONTEXT_SYNTHESIS.md`.
            {"Review the current data model and identify the safest next schema changes." if is_existing_project else f"Design the initial data model for {data['project_name']}."}
            Shape the work around {data['core_features']} and preserve explicit access boundaries.
            """
        ).strip()
        backend_prompt = textwrap.dedent(
            f"""\
            Read `.arms/CONTEXT_SYNTHESIS.md`.
            {"Review the current backend/auth implementation and patch the highest-risk gaps." if is_existing_project else f"Implement the first backend foundation for {data['project_name']}."}
            Use {stack_profile['data_layer']} with auth shaped around {stack_profile['auth_requirement']}.
            """
        ).strip()
        security_prompt = textwrap.dedent(
            f"""\
            Read `.arms/CONTEXT_SYNTHESIS.md`.
            Review auth, access control, and secret handling for {data['project_name']}.
            Check {stack_profile['label']} / {stack_profile['auth_requirement']} / {stack_profile['data_layer']} and flag OWASP-relevant risks early.
            """
        ).strip()
        sections.extend(
            [
                render_agent_prompt_section("Data Prompt", "arms-data-agent", data_prompt),
                render_agent_prompt_section(
                    "Backend Prompt",
                    "arms-backend-agent",
                    backend_prompt,
                    "backend-system-architect",
                ),
                render_agent_prompt_section(
                    "Security Prompt",
                    "arms-security-agent",
                    security_prompt,
                    "security-code-review",
                ),
            ]
        )

    if not is_existing_project:
        media_prompt = textwrap.dedent(
            f"""\
            Read `.arms/CONTEXT_SYNTHESIS.md`.
            Generate the first asset set for {data['project_name']}.
            Use nano-banana-pro and {build_media_asset_brief(data)}
            """
        ).strip()
        sections.append(
            render_agent_prompt_section(
                "Media Prompt",
                "arms-media-agent",
                media_prompt,
                "nano-banana-pro",
            )
        )

    if "content / marketing site" in data["project_type"].lower() or "website" in data["build_surface"].lower() or "landing page" in data["build_surface"].lower():
        seo_prompt = textwrap.dedent(
            f"""\
            Read `.arms/CONTEXT_SYNTHESIS.md`.
            {"Review the current metadata, information hierarchy, and SEO gaps." if is_existing_project else "Create the initial SEO and content brief."}
            Keep recommendations aligned to {data['primary_audience']}, {data['seo_focus']}, and {data['primary_ctas']}.
            """
        ).strip()
        sections.append(
            render_agent_prompt_section(
                "SEO / Content Prompt",
                "arms-seo-agent",
                seo_prompt,
                "seo-web-performance-expert",
            )
        )

    qa_prompt = textwrap.dedent(
        f"""\
        Read `.arms/CONTEXT_SYNTHESIS.md`.
        Prepare the pre-flight validation plan for {data['project_name']}.
        Validate the primary {data['build_surface']} and core flows tied to {data['core_features']}; {qa_action}.
        Prefer Cypress for browser E2E. Escalate to Playwright only if the project is already configured for it or the flow explicitly needs cross-browser, multi-tab, multi-origin, or OAuth coverage.
        """
    ).strip()

    sections.append(
        render_agent_prompt_section(
            "QA Prompt",
            "arms-qa-agent",
            qa_prompt,
            "qa-automation-testing",
        )
    )

    return "\n\n".join(sections) + "\n"


def sync_generated_prompts(project_root):
    prompts_path = os.path.join(project_root, ".arms/GENERATED_PROMPTS.md")
    prompts_content = render_generated_prompts(project_root)

    if prompts_content is None:
        if os.path.exists(prompts_path):
            os.remove(prompts_path)
            print("🧹 Removed stale .arms/GENERATED_PROMPTS.md because the brand brief is incomplete.")
        return False

    write_text_atomic(prompts_path, prompts_content)
    print("🧠 Generated .arms/GENERATED_PROMPTS.md from the approved brand and stack context.")
    maybe_print_budget_warning(".arms/GENERATED_PROMPTS.md", prompts_content, GENERATED_PROMPTS_TOKEN_BUDGET)
    return True
