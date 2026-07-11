"""Tests for arms_engine.brand module."""
import os
import tempfile
import unittest

from arms_engine.brand import (
    apply_answers_to_brand_content,
    apply_project_preset,
    brand_field_is_not_applicable,
    brand_field_is_unanswered,
    brand_file_requires_bootstrap,
    classify_project_type,
    collect_structured_answer_entries,
    detect_existing_project,
    detect_workspace_mode,
    extract_brand_field,
    extract_first_meaningful_paragraph,
    format_available_presets,
    get_missing_new_project_brand_fields,
    infer_build_surface,
    infer_explicit_stack_key,
    infer_logo_status_from_assets,
    infer_project_type_from_primary_use_case,
    infer_stack_recommendation_key,
    is_new_project_brand_questionnaire,
    normalize_answer_key,
    normalize_brand_value,
    normalize_structured_answer,
    parse_pyproject_metadata,
    parse_structured_answers,
    render_compact_intake_answer_block,
    render_new_project_brand_prompt,
    render_new_project_brand_questionnaire,
    run_interactive_brand_intake,
    update_brand_field,
    upsert_note_entry,
    COMPACT_INTAKE_FIELDS,
    NEW_PROJECT_BRAND_MARKER,
)


class TestBrandFieldHelpers(unittest.TestCase):
    def test_brand_field_is_unanswered_empty(self):
        self.assertTrue(brand_field_is_unanswered(""))

    def test_brand_field_is_unanswered_tbd(self):
        self.assertTrue(brand_field_is_unanswered("TBD"))
        self.assertTrue(brand_field_is_unanswered("tbd"))
        self.assertTrue(brand_field_is_unanswered("  TBD  "))

    def test_brand_field_is_unanswered_unknown_variants(self):
        for v in ("unknown", "undecided", "unsure"):
            self.assertTrue(brand_field_is_unanswered(v))

    def test_brand_field_is_unanswered_real_value(self):
        self.assertFalse(brand_field_is_unanswered("Awesome SaaS"))

    def test_brand_field_is_not_applicable_variants(self):
        for v in ("N/A", "na", "not applicable", "none"):
            self.assertTrue(brand_field_is_not_applicable(v))

    def test_brand_field_is_not_applicable_real_value(self):
        self.assertFalse(brand_field_is_not_applicable("Font Awesome"))

    def test_normalize_brand_value_uses_fallback_when_unanswered(self):
        result = normalize_brand_value("TBD", "default-value")
        self.assertEqual(result, "default-value")

    def test_normalize_brand_value_uses_real_value(self):
        result = normalize_brand_value("Vercel", "default-value")
        self.assertEqual(result, "Vercel")


class TestExtractBrandField(unittest.TestCase):
    CONTENT = "- **Mission:** Build tools that matter.\n- **Vision:** TBD\n"

    def test_extracts_existing_field(self):
        self.assertEqual(extract_brand_field(self.CONTENT, "Mission"), "Build tools that matter.")

    def test_returns_empty_for_missing_field(self):
        self.assertEqual(extract_brand_field(self.CONTENT, "Nonexistent"), "")

    def test_extracts_tbd_field(self):
        self.assertEqual(extract_brand_field(self.CONTENT, "Vision"), "TBD")


class TestUpdateBrandField(unittest.TestCase):
    CONTENT = "- **Mission:** TBD\n- **Vision:** Long term goal.\n"

    def test_updates_unanswered_field(self):
        updated, changed = update_brand_field(self.CONTENT, "Mission", "Empower devs.")
        self.assertTrue(changed)
        self.assertIn("Empower devs.", updated)

    def test_does_not_overwrite_answered_field_by_default(self):
        updated, changed = update_brand_field(self.CONTENT, "Vision", "New vision.")
        self.assertFalse(changed)
        self.assertIn("Long term goal.", updated)

    def test_overwrites_answered_field_when_forced(self):
        updated, changed = update_brand_field(self.CONTENT, "Vision", "New vision.", overwrite=True)
        self.assertTrue(changed)
        self.assertIn("New vision.", updated)

    def test_no_change_for_missing_field(self):
        updated, changed = update_brand_field(self.CONTENT, "Nonexistent", "value")
        self.assertFalse(changed)
        self.assertEqual(updated, self.CONTENT)


class TestUpsertNoteEntry(unittest.TestCase):
    def test_adds_note_section_when_missing(self):
        content = "# Brand\n\nsome content"
        updated, changed = upsert_note_entry(content, "Core Features", "Auth and CRUD")
        self.assertTrue(changed)
        self.assertIn("Core Features: Auth and CRUD", updated)
        self.assertIn("## Notes", updated)

    def test_updates_existing_note(self):
        content = "# Brand\n\n## Notes\n- Core Features: old value\n"
        updated, changed = upsert_note_entry(content, "Core Features", "new value")
        self.assertTrue(changed)
        self.assertIn("Core Features: new value", updated)
        self.assertNotIn("old value", updated)

    def test_appends_to_existing_notes_section(self):
        content = "# Brand\n\n## Notes\n- First: something\n"
        updated, changed = upsert_note_entry(content, "Second", "another thing")
        self.assertTrue(changed)
        self.assertIn("First: something", updated)
        self.assertIn("Second: another thing", updated)


class TestIsNewProjectBrandQuestionnaire(unittest.TestCase):
    def test_detects_marker(self):
        self.assertTrue(is_new_project_brand_questionnaire(f"prefix {NEW_PROJECT_BRAND_MARKER} suffix"))

    def test_returns_false_without_marker(self):
        self.assertFalse(is_new_project_brand_questionnaire("No marker here"))


class TestGetMissingFields(unittest.TestCase):
    def test_returns_all_fields_when_tbd(self):
        content = NEW_PROJECT_BRAND_MARKER + "\n- **Mission:** TBD\n- **Vision:** TBD\n"
        missing = get_missing_new_project_brand_fields(content)
        self.assertIn("Mission", missing)
        self.assertIn("Vision", missing)

    def test_does_not_include_answered_fields(self):
        content = NEW_PROJECT_BRAND_MARKER + "\n- **Mission:** Build things.\n- **Vision:** TBD\n"
        missing = get_missing_new_project_brand_fields(content)
        self.assertNotIn("Mission", missing)
        self.assertIn("Vision", missing)


class TestBrandFileRequiresBootstrap(unittest.TestCase):
    def test_empty_content_requires_bootstrap(self):
        self.assertTrue(brand_file_requires_bootstrap(""))

    def test_placeholder_tokens_require_bootstrap(self):
        self.assertTrue(brand_file_requires_bootstrap("- **Mission:** [Name]"))

    def test_answered_content_does_not_require_bootstrap(self):
        content = "- **Mission:** Build tools.\n- **Vision:** Empower devs.\n"
        self.assertFalse(brand_file_requires_bootstrap(content))


class TestNormalizeAnswerKey(unittest.TestCase):
    def test_lowercase_and_collapses_special_chars(self):
        self.assertEqual(normalize_answer_key("Voice & Tone"), "voice tone")

    def test_trims_whitespace(self):
        self.assertEqual(normalize_answer_key("  Mission  "), "mission")


class TestNormalizeStructuredAnswer(unittest.TestCase):
    def test_resolves_choice_alias(self):
        result = normalize_structured_answer("Preferred Tech Stack", "a")
        self.assertEqual(result, "Next.js + Supabase + shadcn/ui (latest stable)")

    def test_resolves_deployment_alias(self):
        result = normalize_structured_answer("Deployment Target", "1")
        self.assertEqual(result, "Vercel")

    def test_passthrough_for_unknown_field(self):
        result = normalize_structured_answer("Mission", "Build things")
        self.assertEqual(result, "Build things")

    def test_collapses_whitespace(self):
        result = normalize_structured_answer("Mission", "  Build   things  ")
        self.assertEqual(result, "Build things")


class TestParseStructuredAnswers(unittest.TestCase):
    def test_parses_markdown_field_format(self):
        text = "- **Mission:** Build tools that matter.\n- **Vision:** Empower devs.\n"
        answers = parse_structured_answers(text)
        self.assertEqual(answers["Mission"], "Build tools that matter.")
        self.assertEqual(answers["Vision"], "Empower devs.")

    def test_parses_numbered_format(self):
        text = "1. Build tools\n2. Developers\n"
        answers = parse_structured_answers(text)
        # Q1 → Primary Use Case, Q2 → Primary Audience
        self.assertIn("Primary Use Case", answers)
        self.assertIn("Primary Audience", answers)

    def test_parses_key_value_format(self):
        text = "Mission: Build tools.\nVision: Empower devs.\n"
        answers = parse_structured_answers(text)
        self.assertEqual(answers.get("Mission"), "Build tools.")

    def test_returns_empty_dict_for_blank_input(self):
        self.assertEqual(parse_structured_answers(""), {})

    def test_resolves_choice_alias_inline(self):
        text = "- **Preferred Tech Stack:** a\n"
        answers = parse_structured_answers(text)
        self.assertEqual(answers["Preferred Tech Stack"], "Next.js + Supabase + shadcn/ui (latest stable)")


class TestApplyProjectPreset(unittest.TestCase):
    TEMPLATE = (
        "- **Project Type:** TBD\n"
        "- **Design Priority:** TBD\n"
        "- **Voice & Tone:** TBD\n"
        "- **Typography:** TBD\n"
        "- **Icon System:** TBD\n"
        "- **Experience Type:** TBD\n"
        "- **Required Website Sections:** TBD\n"
        "- **Primary Calls to Action:** TBD\n"
        "- **Image Requirements:** TBD\n"
        "- **SEO Focus:** TBD\n"
        "- **Technical Constraints:** TBD\n"
    )

    def test_local_business_preset_fills_fields(self):
        updated, changed_fields = apply_project_preset(self.TEMPLATE, "local-business")
        self.assertIn("Project Type", changed_fields)
        self.assertIn("Content / Marketing Site", updated)

    def test_preset_does_not_overwrite_answered_field(self):
        content = self.TEMPLATE.replace("- **Project Type:** TBD", "- **Project Type:** Custom Value")
        updated, changed_fields = apply_project_preset(content, "local-business")
        self.assertNotIn("Project Type", changed_fields)
        self.assertIn("Custom Value", updated)


class TestApplyAnswersToBrandContent(unittest.TestCase):
    TEMPLATE = (
        "- **Mission:** TBD\n"
        "- **Primary Audience:** TBD\n"
        "- **Project Type:** TBD\n"
        "- **Differentiation:** TBD\n"
        "- **Logo Status:** TBD\n"
        "- **Technical Constraints:** TBD\n"
    )

    def test_applies_direct_field(self):
        content, summary = apply_answers_to_brand_content(self.TEMPLATE, {"Mission": "Build tools."})
        self.assertIn("Mission", summary["fields"])
        self.assertIn("Build tools.", content)

    def test_derives_project_type_from_primary_use_case(self):
        content, summary = apply_answers_to_brand_content(
            self.TEMPLATE, {"Primary Use Case": "SaaS product"}
        )
        self.assertIn("Project Type", summary["fields"])
        self.assertIn("Web Application", content)

    def test_no_change_for_empty_answers(self):
        content, summary = apply_answers_to_brand_content(self.TEMPLATE, {})
        self.assertEqual(summary["fields"], [])
        self.assertEqual(summary["notes"], [])

    def test_compact_cli_answers_complete_new_project_questionnaire(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            content = render_new_project_brand_questionnaire(tmpdir)
            answers = parse_structured_answers(
                """Project Name: OrbitOps
Primary Use Case: SaaS
Target Audience: operations teams
Core Features: approvals, task routing, analytics
Goal / Monetization Model: subscription
Brand Personality: technical, trustworthy, sharp
Visual Direction: Dark
Preferred Tech Stack: A
Deployment Target: 1
Authentication Requirement: OAuth
Website Brief: N/A
Technical Constraints: TypeScript only
"""
            )

            updated, summary = apply_answers_to_brand_content(content, answers)

            self.assertFalse(get_missing_new_project_brand_fields(updated))
            self.assertIn("Mission", summary["fields"])
            self.assertIn("- **Project Type:** Web Application", updated)
            self.assertIn("- **Experience Type:** N/A", updated)
            self.assertIn("- Website Brief: N/A", updated)

    def test_compact_cli_website_brief_fills_website_fields(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            content = render_new_project_brand_questionnaire(tmpdir)
            answers = parse_structured_answers(
                """Project Name: Harbor Dental
Primary Use Case: Content-Marketing
Target Audience: local dental patients
Core Features: service pages, appointment CTA, testimonials
Goal / Monetization Model: book consultations
Brand Personality: warm, trustworthy
Visual Direction: Light
Preferred Tech Stack: C
Deployment Target: 1
Authentication Requirement: None
Website Brief: local dental clinic site with hero, services, testimonials, contact form, appointment CTA, local SEO, real office images
Technical Constraints: mobile-first
"""
            )

            updated, _ = apply_answers_to_brand_content(content, answers)

            self.assertFalse(get_missing_new_project_brand_fields(updated))
            self.assertIn("- **Experience Type:** Website / landing page", updated)
            self.assertIn("- **Required Website Sections:** local dental clinic", updated)
            self.assertIn("- **SEO Focus:** local dental clinic", updated)


class TestClassifyProjectType(unittest.TestCase):
    def test_developer_tooling_from_scripts(self):
        result = classify_project_type("", [], has_project_scripts=True)
        self.assertEqual(result, "Developer Tooling")

    def test_web_application_from_framework(self):
        result = classify_project_type("", ["Next.js"], has_project_scripts=False)
        self.assertEqual(result, "Web Application")

    def test_content_site_from_description(self):
        result = classify_project_type("marketing blog with SEO", ["Astro"], has_project_scripts=False)
        self.assertEqual(result, "Content / Marketing Site")

    def test_backend_service_from_framework(self):
        result = classify_project_type("", ["FastAPI"], has_project_scripts=False)
        self.assertEqual(result, "Backend Service")

    def test_default_software_project(self):
        result = classify_project_type("", [], has_project_scripts=False)
        self.assertEqual(result, "Software Project")


class TestInferBuildSurface(unittest.TestCase):
    def test_local_service_mapping(self):
        result = infer_build_surface({"Experience Type": "Local service business"})
        self.assertEqual(result, "local-service landing page")

    def test_portfolio_mapping(self):
        result = infer_build_surface({"Experience Type": "Portfolio"})
        self.assertEqual(result, "portfolio site")

    def test_fallback_to_project_type(self):
        result = infer_build_surface({"Project Type": "Content / Marketing Site"})
        self.assertEqual(result, "marketing website")


class TestInferExplicitStackKey(unittest.TestCase):
    def test_nextjs(self):
        self.assertEqual(infer_explicit_stack_key("Next.js + Supabase"), "nextjs")

    def test_nuxt(self):
        self.assertEqual(infer_explicit_stack_key("Nuxt + Firebase"), "nuxt")

    def test_astro(self):
        self.assertEqual(infer_explicit_stack_key("Astro + Tailwind"), "astro")

    def test_empty_returns_empty(self):
        self.assertEqual(infer_explicit_stack_key(""), "")

    def test_unknown_returns_empty(self):
        self.assertEqual(infer_explicit_stack_key("Custom Rails setup"), "")


class TestInferStackRecommendationKey(unittest.TestCase):
    def test_explicit_nextjs_not_inferred(self):
        key, inferred = infer_stack_recommendation_key({"Preferred Tech Stack": "Next.js + Supabase"})
        self.assertEqual(key, "nextjs")
        self.assertFalse(inferred)

    def test_infers_astro_for_marketing(self):
        key, inferred = infer_stack_recommendation_key({"Primary Use Case": "content marketing"})
        self.assertEqual(key, "astro")
        self.assertTrue(inferred)

    def test_infers_nuxt_for_mobile_first(self):
        key, inferred = infer_stack_recommendation_key({"Technical Constraints": "mobile-first"})
        self.assertEqual(key, "nuxt")
        self.assertTrue(inferred)

    def test_default_nextjs(self):
        key, inferred = infer_stack_recommendation_key({})
        self.assertEqual(key, "nextjs")
        self.assertTrue(inferred)


class TestInferLogoStatusFromAssets(unittest.TestCase):
    def test_logo_yes(self):
        result = infer_logo_status_from_assets("Logo (Y)")
        self.assertEqual(result, "Existing asset detected")

    def test_logo_no(self):
        result = infer_logo_status_from_assets("Logo (N)")
        self.assertEqual(result, "Not yet created")

    def test_empty_returns_empty(self):
        self.assertEqual(infer_logo_status_from_assets(""), "")

    def test_logo_keyword_alone(self):
        result = infer_logo_status_from_assets("We have a logo already")
        self.assertIn("asset", result.lower())


class TestInferProjectTypeFromPrimaryUseCase(unittest.TestCase):
    def test_content_marketing(self):
        self.assertEqual(infer_project_type_from_primary_use_case("content marketing"), "Content / Marketing Site")

    def test_saas(self):
        self.assertEqual(infer_project_type_from_primary_use_case("SaaS product"), "Web Application")

    def test_passthrough(self):
        self.assertEqual(infer_project_type_from_primary_use_case("something else"), "something else")


class TestParsePyprojectMetadata(unittest.TestCase):
    CONTENT = '''
[project]
name = "arms-engine"
description = "ARMS orchestration tool"

[project.scripts]
arms = "arms_engine.init_arms:main"
'''

    def test_extracts_name(self):
        result = parse_pyproject_metadata(self.CONTENT)
        self.assertEqual(result["name"], "arms-engine")

    def test_extracts_description(self):
        result = parse_pyproject_metadata(self.CONTENT)
        self.assertEqual(result["description"], "ARMS orchestration tool")

    def test_detects_scripts(self):
        result = parse_pyproject_metadata(self.CONTENT)
        self.assertTrue(result["has_scripts"])

    def test_no_scripts_when_absent(self):
        result = parse_pyproject_metadata("[project]\nname = \"foo\"\n")
        self.assertFalse(result["has_scripts"])


class TestExtractFirstMeaningfulParagraph(unittest.TestCase):
    def test_skips_heading_and_returns_prose(self):
        text = "# Title\n\nThis is the first paragraph.\nContinued here.\n"
        result = extract_first_meaningful_paragraph(text)
        self.assertIn("first paragraph", result)

    def test_skips_code_blocks(self):
        text = "```python\ncode here\n```\n\nReal paragraph.\n"
        result = extract_first_meaningful_paragraph(text)
        self.assertEqual(result, "Real paragraph.")

    def test_skips_list_items(self):
        text = "- item one\n- item two\n\nParagraph after list.\n"
        result = extract_first_meaningful_paragraph(text)
        self.assertEqual(result, "Paragraph after list.")

    def test_empty_text(self):
        self.assertEqual(extract_first_meaningful_paragraph(""), "")


class TestDetectExistingProject(unittest.TestCase):
    def test_empty_directory_is_new_project(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            self.assertFalse(detect_existing_project(tmpdir))

    def test_package_json_marks_existing(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            open(os.path.join(tmpdir, "package.json"), "w").close()
            self.assertTrue(detect_existing_project(tmpdir))

    def test_pyproject_toml_marks_existing(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            open(os.path.join(tmpdir, "pyproject.toml"), "w").close()
            self.assertTrue(detect_existing_project(tmpdir))

    def test_readme_only_is_not_existing(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            open(os.path.join(tmpdir, "README.md"), "w").close()
            self.assertFalse(detect_existing_project(tmpdir))

    def test_bootstrap_only_files_are_not_existing(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            open(os.path.join(tmpdir, "AGENTS.md"), "w").close()
            open(os.path.join(tmpdir, "CLAUDE.md"), "w").close()
            open(os.path.join(tmpdir, "GEMINI.md"), "w").close()
            self.assertFalse(detect_existing_project(tmpdir))


class TestDetectWorkspaceMode(unittest.TestCase):
    def test_new_project_marker_in_brand_content(self):
        mode = detect_workspace_mode("/any/path", f"{NEW_PROJECT_BRAND_MARKER}\n")
        self.assertEqual(mode, "new-project")

    def test_existing_project_from_filesystem(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            open(os.path.join(tmpdir, "package.json"), "w").close()
            self.assertEqual(detect_workspace_mode(tmpdir), "existing-project")

    def test_empty_dir_is_new_project(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            self.assertEqual(detect_workspace_mode(tmpdir), "new-project")


class TestFormatAvailablePresets(unittest.TestCase):
    def test_returns_non_empty_string(self):
        result = format_available_presets()
        self.assertIsInstance(result, str)
        self.assertGreater(len(result), 0)

    def test_contains_known_presets(self):
        result = format_available_presets()
        self.assertIn("local-business", result)
        self.assertIn("saas", result)


class TestRenderNewProjectBrandQuestionnaire(unittest.TestCase):
    def test_contains_identity_section(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            content = render_new_project_brand_questionnaire(tmpdir)
            self.assertIn("## Identity", content)
            self.assertIn("Mission", content)

    def test_contains_project_name(self):
        with tempfile.TemporaryDirectory() as d:
            content = render_new_project_brand_questionnaire(d)
            self.assertIn(os.path.basename(d), content)


class TestResearchedStackHonoring(unittest.TestCase):
    def test_concrete_non_preset_stack_is_honored(self):
        from arms_engine.brand import resolve_stack_recommendation

        profile = resolve_stack_recommendation(
            {
                "Preferred Tech Stack": "SvelteKit + Supabase + Skeleton UI",
                "Deployment Target": "Cloudflare Pages",
            }
        )
        self.assertEqual(profile["key"], "custom")
        self.assertEqual(profile["framework"], "SvelteKit")
        self.assertEqual(profile["ui_system"], "Skeleton UI")
        self.assertEqual(profile["deployment_target"], "Cloudflare Pages")
        self.assertFalse(profile["research_recommended"])
        self.assertEqual(profile["source"], "Researched / custom stack")

    def test_custom_prefix_is_stripped(self):
        from arms_engine.brand import resolve_stack_recommendation

        profile = resolve_stack_recommendation({"Preferred Tech Stack": "Custom: Django + PostgreSQL + HTMX"})
        self.assertEqual(profile["framework"], "Django")
        self.assertEqual(profile["key"], "custom")

    def test_bare_custom_falls_back_to_preset_with_research_flag(self):
        from arms_engine.brand import resolve_stack_recommendation

        profile = resolve_stack_recommendation({"Preferred Tech Stack": "Custom"})
        self.assertIn(profile["key"], {"nextjs", "nuxt", "astro"})
        self.assertTrue(profile["research_recommended"])

    def test_unanswered_stack_recommends_research(self):
        from arms_engine.brand import resolve_stack_recommendation

        profile = resolve_stack_recommendation({"Preferred Tech Stack": "TBD"})
        self.assertTrue(profile["research_recommended"])

    def test_preset_stack_answer_keeps_preset_without_research_flag(self):
        from arms_engine.brand import resolve_stack_recommendation

        profile = resolve_stack_recommendation(
            {"Preferred Tech Stack": "Next.js + Supabase + shadcn/ui (latest stable)"}
        )
        self.assertEqual(profile["key"], "nextjs")
        self.assertFalse(profile["research_recommended"])


class TestResearchBriefLifecycle(unittest.TestCase):
    def test_brief_created_while_stack_unresolved_and_removed_after(self):
        from arms_engine.brand import (
            apply_brand_inputs,
            sync_research_brief,
        )

        with tempfile.TemporaryDirectory() as tmp:
            os.makedirs(os.path.join(tmp, ".arms"))
            brand_path = os.path.join(tmp, ".arms", "BRAND.md")
            brief_path = os.path.join(tmp, ".arms", "RESEARCH_BRIEF.md")
            with open(brand_path, "w", encoding="utf-8") as f:
                f.write(render_new_project_brand_questionnaire(tmp))

            self.assertTrue(sync_research_brief(tmp))
            self.assertTrue(os.path.exists(brief_path))
            with open(brief_path, encoding="utf-8") as f:
                brief = f.read()
            self.assertIn("Do not limit the search to ARMS presets", brief)
            self.assertIn("Stack Proposal", brief)
            self.assertIn("arms intake --answers-text", brief)

            apply_brand_inputs(
                tmp,
                answers_text="Preferred Tech Stack: SvelteKit + Supabase + Skeleton UI",
            )
            self.assertFalse(sync_research_brief(tmp))
            self.assertFalse(os.path.exists(brief_path))

    def test_no_brief_for_existing_project_brand(self):
        from arms_engine.brand import sync_research_brief

        with tempfile.TemporaryDirectory() as tmp:
            os.makedirs(os.path.join(tmp, ".arms"))
            with open(os.path.join(tmp, ".arms", "BRAND.md"), "w", encoding="utf-8") as f:
                f.write("# Brand Context\n- **Project Name:** Demo\n- **Mission:** Ship\n")
            self.assertFalse(sync_research_brief(tmp))
            self.assertFalse(os.path.exists(os.path.join(tmp, ".arms", "RESEARCH_BRIEF.md")))


class TestInteractiveBrandIntake(unittest.TestCase):
    def _scripted_input(self, answers):
        iterator = iter(answers)

        def fake_input(_prompt=""):
            try:
                return next(iterator)
            except StopIteration:
                raise EOFError

        return fake_input

    def test_compact_block_stays_in_sync_with_fields(self):
        # The printed compact answer block must be derivable from the same
        # COMPACT_INTAKE_FIELDS the interactive form iterates over.
        block = render_compact_intake_answer_block()
        for label, _hint in COMPACT_INTAKE_FIELDS:
            self.assertIn(f"{label}:", block)
        self.assertIn(render_compact_intake_answer_block(), render_new_project_brand_prompt())

    def test_interactive_intake_collects_answers(self):
        answers = [
            "Acme Tasks",
            "SaaS",
            "Indie developers",
            "Kanban, reminders",
            "Subscription",
            "sharp, calm, modern",
            "Dark",
            "A",
            "1",
            "OAuth",
            "N/A",
            "None",
        ]
        result = run_interactive_brand_intake(
            "/tmp/does-not-matter",
            input_func=self._scripted_input(answers),
            output_func=lambda *a, **k: None,
        )
        self.assertTrue(result["answered"])
        self.assertIn("Project Name: Acme Tasks", result["answers_text"])
        self.assertIn("Preferred Tech Stack: A", result["answers_text"])
        self.assertIn("Technical Constraints: None", result["answers_text"])

    def test_interactive_intake_applies_to_brand_md(self):
        with tempfile.TemporaryDirectory() as tmp:
            os.makedirs(os.path.join(tmp, ".arms"))
            brand_path = os.path.join(tmp, ".arms", "BRAND.md")
            with open(brand_path, "w", encoding="utf-8") as f:
                f.write(render_new_project_brand_questionnaire(tmp))

            answers = [
                "Acme Tasks", "SaaS", "Indie developers", "Kanban", "Subscription",
                "sharp, calm", "Dark", "A", "1", "OAuth", "N/A", "None",
            ]
            result = run_interactive_brand_intake(
                tmp,
                input_func=self._scripted_input(answers),
                output_func=lambda *a, **k: None,
            )
            answers_dict = parse_structured_answers(result["answers_text"])
            # Compact-block label "Target Audience" must resolve to Primary Audience.
            self.assertEqual(answers_dict.get("Primary Audience"), "Indie developers")
            self.assertEqual(answers_dict.get("Project Name"), "Acme Tasks")

    def test_interactive_intake_skip_stops_form(self):
        result = run_interactive_brand_intake(
            "/tmp/does-not-matter",
            input_func=self._scripted_input(["Acme", "skip", "ignored"]),
            output_func=lambda *a, **k: None,
        )
        self.assertTrue(result["answered"])
        self.assertIn("Project Name: Acme", result["answers_text"])
        self.assertNotIn("ignored", result["answers_text"])

    def test_interactive_intake_all_skipped_returns_unanswered(self):
        result = run_interactive_brand_intake(
            "/tmp/does-not-matter",
            input_func=self._scripted_input(["", "", "", "", "", "", "", "", "", "", "", ""]),
            output_func=lambda *a, **k: None,
        )
        self.assertFalse(result["answered"])
        self.assertEqual(result["answers_text"], "")


if __name__ == "__main__":
    unittest.main()
