import os
import textwrap

from .brand import (
    brand_field_is_unanswered,
    brand_file_requires_bootstrap,
    collect_brand_context,
    infer_build_surface,
    normalize_brand_value,
    project_needs_backend_foundation,
    read_text_file,
    resolve_stack_recommendation,
)
from .session import write_text_atomic


GENERATED_PROMPTS_HEADER = """# ARMS Generated Prompts

> Managed by ARMS Engine. Regenerated from `.arms/BRAND.md` during `arms init`.
> Update the brand brief and re-run `arms init` to refresh these prompts.
"""
CONTEXT_SYNTHESIS_HEADER = """# ARMS Context Synthesis

> Managed by ARMS Engine. Regenerated from `.arms/BRAND.md` during `arms init`.
> This file condenses the approved brand and stack answers into an AI-ready project brief.
"""


def render_markdown_bullets(items, empty_message):
    if not items:
        return f"- {empty_message}"
    return "\n".join(f"- {item}" for item in items)


def build_startup_tasks(data):
    rows = []

    def add(task, agent, dependencies="—"):
        rows.append(
            {
                "task": task,
                "agent": agent,
                "dependencies": dependencies,
            }
        )

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

    backend_needed = project_needs_backend_foundation(data["context"], data["stack_profile"])
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
    kickoff_summary = "\n".join(
        f"{index}. **{row['agent']}** — {row['task']}"
        for index, row in enumerate(data["startup_tasks"], start=1)
    )

    return (
        CONTEXT_SYNTHESIS_HEADER.strip()
        + "\n\n## Project Overview\n"
        + textwrap.dedent(
            f"""\
            - **Project Name:** {data['project_name']}
            - **Mission:** {data['mission']}
            - **Vision:** {data['vision']}
            - **Primary Use Case:** {data['primary_use_case']}
            - **Primary Audience:** {data['primary_audience']}
            - **Project Type:** {data['project_type']}
            - **Build Surface:** {data['build_surface']}
            """
        ).strip()
        + "\n\n## Recommended Build Profile\n"
        + textwrap.dedent(
            f"""\
            - **Requested Stack:** {stack_profile['requested_stack']}
            - **Recommended Stack:** {stack_profile['label']}
            - **Framework:** {stack_profile['framework']}
            - **UI System:** {stack_profile['ui_system']}
            - **Backend / Data Layer:** {stack_profile['data_layer']}
            - **Deployment Target:** {stack_profile['deployment_target']}
            - **Authentication:** {stack_profile['auth_requirement']}
            - **Best Fit:** {stack_profile['best_for']}
            - **Why This Recommendation:** {stack_profile['reason']}
            - **Recommendation Source:** {stack_profile['source']}
            """
        ).strip()
        + "\n\n## Brand & Experience Direction\n"
        + textwrap.dedent(
            f"""\
            - **Personality:** {data['personality']}
            - **Voice & Tone:** {data['voice_tone']}
            - **Differentiation:** {data['differentiation']}
            - **Visual Direction:** {data['visual_direction']}
            - **Reference Brand:** {data['reference_brand']}
            - **Brand Comparison:** {data['brand_comparison']}
            - **Logo Status:** {data['logo_status']}
            - **Existing Brand Assets:** {data['existing_brand_assets']}
            """
        ).strip()
        + "\n\n## Delivery Priorities\n"
        + textwrap.dedent(
            f"""\
            - **Core Features:** {data['core_features']}
            - **Goal / Monetization Model:** {data['monetization_model']}
            - **Required Sections:** {data['required_sections']}
            - **Primary CTAs:** {data['primary_ctas']}
            - **SEO Focus:** {data['seo_focus']}
            - **Technical Constraints:** {data['technical_constraints']}
            - **Image Requirements:** {data['image_requirements']}
            - **Content / Visual Non-Negotiables:** {data['content_non_negotiables']}
            - **Icon System:** {data['icon_system']}
            """
        ).strip()
        + "\n\n## Confidence Signals\n### Confirmed\n"
        + render_markdown_bullets(data["confirmed_signals"], "Core project signals still need confirmation.")
        + "\n\n### Needs Attention\n"
        + render_markdown_bullets(data["needs_attention_signals"], "No major gaps detected.")
        + "\n\n## Agent Kickoff Summary\n"
        + kickoff_summary
        + "\n"
    )


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
    return True


def render_generated_prompts(project_root):
    data = build_context_synthesis_data(project_root)
    if data is None:
        return None

    stack_profile = data["stack_profile"]
    backend_needed = project_needs_backend_foundation(data["context"], stack_profile)
    media_asset_brief = build_media_asset_brief(data)

    quick_reference = textwrap.dedent(
        f"""\
        ## Quick Reference
        - **Project Name:** {data['project_name']}
        - **Recommended Stack:** {stack_profile['label']}
        - **Framework:** {stack_profile['framework']}
        - **UI System:** {stack_profile['ui_system']}
        - **Backend / Data Layer:** {stack_profile['data_layer']}
        - **Deployment Target:** {stack_profile['deployment_target']}
        - **Authentication:** {stack_profile['auth_requirement']}
        - **Build Surface:** {data['build_surface']}
        - **Core Features:** {data['core_features']}
        - **Reference:** Read `.arms/CONTEXT_SYNTHESIS.md` before executing any of the prompts below.
        """
    ).strip()

    master_prompt = textwrap.dedent(
        f"""\
        Read `.arms/CONTEXT_SYNTHESIS.md` first, then create the first production-quality {data['build_surface']} for {data['project_name']}.

        Use {stack_profile['framework']} with {stack_profile['ui_system']} and keep all package choices on the latest stable ecosystem release unless the repository already pins something else.
        Match this brand direction: {data['personality']} personality, {data['voice_tone']} voice, {data['visual_direction']} visual direction.
        Build for {data['primary_audience']} and keep the experience centered on {data['core_features']}.
        Honor these non-negotiables: {data['technical_constraints']} / {data['content_non_negotiables']}.
        """
    ).strip()

    product_prompt = textwrap.dedent(
        f"""\
        Read `.arms/CONTEXT_SYNTHESIS.md` and turn it into a concise project charter for {data['project_name']}.

        Deliverables:
        - Refine the primary problem statement and success metrics
        - Prioritize the initial feature set around {data['core_features']}
        - Flag the highest-risk ambiguities before other agents begin implementation
        Keep the output concise, decisive, and aligned to {data['monetization_model']}.
        """
    ).strip()

    devops_prompt = textwrap.dedent(
        f"""\
        Scaffold {data['project_name']} using {stack_profile['framework']} with {stack_profile['ui_system']}.

        Requirements:
        - Backend / data layer: {stack_profile['data_layer']}
        - Deployment target: {stack_profile['deployment_target']}
        - Authentication: {stack_profile['auth_requirement']}
        - Technical constraints: {data['technical_constraints']}
        - Recommendation note: {stack_profile['selection_note']}

        Choose the current best-practice setup for this stack and leave the repo ready for frontend, backend, and QA work.
        """
    ).strip()

    frontend_prompt = textwrap.dedent(
        f"""\
        Create the first responsive {data['build_surface']} for {data['project_name']}.

        Use {stack_profile['ui_system']} as the component foundation ({stack_profile['framework']} stack).
        Align the UI to this direction: {data['personality']} personality, {data['voice_tone']} tone, {data['visual_direction']} visual direction.
        Structure the experience around: {data['required_sections']}.
        Optimize the flow for these CTAs: {data['primary_ctas']}.
        Use {data['icon_system']} for icons and avoid emoji unless later requested.
        """
    ).strip()

    media_prompt = textwrap.dedent(
        f"""\
        Generate the first visual asset set for {data['project_name']}.

        Inputs:
        - Personality: {data['personality']}
        - Differentiation: {data['differentiation']}
        - Visual direction: {data['visual_direction']}
        - Existing brand assets: {data['existing_brand_assets']}
        - Logo status: {data['logo_status']}
        - Image requirements: {data['image_requirements']}

        Asset generation instructions:
        - {media_asset_brief}

        Produce assets that support the first frontend pass without falling back to generic visuals.
        """
    ).strip()

    seo_prompt = textwrap.dedent(
        f"""\
        Create the initial SEO and content brief for {data['project_name']}.

        Prioritize:
        - Audience: {data['primary_audience']}
        - Niche: {data['business_niche']}
        - Service area: {data['service_area']}
        - SEO focus: {data['seo_focus']}
        - Required sections: {data['required_sections']}
        - CTAs: {data['primary_ctas']}

        Keep the information architecture crawlable, conversion-aware, and aligned to the brand tone.
        """
    ).strip()

    sections = [
        GENERATED_PROMPTS_HEADER.strip(),
        quick_reference,
        "## Master Build Prompt\n```text\n" + master_prompt + "\n```",
        "## Product Kickoff Prompt\n```text\n" + product_prompt + "\n```",
        "## DevOps Scaffold Prompt\n```text\n" + devops_prompt + "\n```",
        "## Frontend Prompt\n```text\n" + frontend_prompt + "\n```",
    ]

    if backend_needed:
        data_prompt = textwrap.dedent(
            f"""\
            Read `.arms/CONTEXT_SYNTHESIS.md` and design the initial data model for {data['project_name']}.

            Start from {stack_profile['data_layer']} and shape the schema around {data['core_features']}.
            Preserve explicit access boundaries, future migrations, and the minimum entities required for the first milestone.
            """
        ).strip()
        backend_prompt = textwrap.dedent(
            f"""\
            Implement the first backend foundation for {data['project_name']}.

            Use {stack_profile['data_layer']} with this auth shape: {stack_profile['auth_requirement']}.
            Focus on the minimum secure path needed to support the first UI and product flows from `.arms/CONTEXT_SYNTHESIS.md`.
            """
        ).strip()
        security_prompt = textwrap.dedent(
            f"""\
            Review the planned auth and data setup for {data['project_name']} before it hardens.

            Check the recommendation stack ({stack_profile['label']}), the chosen auth model ({stack_profile['auth_requirement']}), and the planned data layer ({stack_profile['data_layer']}).
            Flag OWASP-relevant issues, access-control gaps, and secret-handling risks early.
            """
        ).strip()
        sections.extend(
            [
                "## Data Prompt\n```text\n" + data_prompt + "\n```",
                "## Backend Prompt\n```text\n" + backend_prompt + "\n```",
                "## Security Prompt\n```text\n" + security_prompt + "\n```",
            ]
        )

    qa_prompt = textwrap.dedent(
        f"""\
        Prepare the pre-flight validation plan for {data['project_name']}.

        Validate the scaffold, the primary {data['build_surface']}, and the core flows tied to {data['core_features']}.
        Keep the test plan realistic for the selected stack ({stack_profile['label']}) and the deployment target ({stack_profile['deployment_target']}).
        """
    ).strip()

    sections.extend(
        [
            "## Media Prompt\n```text\n" + media_prompt + "\n```",
            "## SEO / Content Prompt\n```text\n" + seo_prompt + "\n```",
            "## QA Prompt\n```text\n" + qa_prompt + "\n```",
        ]
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
    return True
