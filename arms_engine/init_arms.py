"""Compatibility shim for the ARMS init entrypoint.

The implementation now lives in focused modules so CLI orchestration, brand
handling, prompt generation, skill sync, and session state can evolve and be
tested independently. Keep this file as the stable import surface and
`arms_engine.init_arms:main` entrypoint.
"""

from . import __version__
from . import cli as _cli
from .brand import (
    apply_answers_to_brand_content,
    apply_brand_inputs,
    brand_file_requires_bootstrap,
    infer_brand_context_from_project,
    parse_structured_answers,
    render_new_project_brand_prompt,
    render_new_project_brand_questionnaire,
    resolve_stack_recommendation,
)
from .cli import capture_file_signature, get_arms_root, get_project_root, normalize_arms_root, prompt_context_overwrite, run_init_once
from .monitor import InitActivityMonitor, render_terminal_dashboard
from .prompts import build_context_synthesis_data, render_startup_tasks_content, sync_context_synthesis, sync_generated_prompts
from .session import (
    SessionContextMismatchError,
    bootstrap_runtime_files,
    enforce_engine_version_guard,
    is_development_engine,
    migrate_legacy_state,
    setup_folders,
    update_session,
)
from .skills import (
    create_skills_registry,
    load_agents_registry,
    remove_obsolete_gemini_skill_artifacts,
    resolve_agents_with_skills,
    sync_agents,
    sync_agents_copilot,
    sync_engine_instructions,
    sync_root_agents_guide,
    sync_skills_copilot,
    sync_workflow,
)
from .tasks import infer_agent_from_task
from .versioning import format_git_describe_version, is_unresolved_version


WATCH_POLL_INTERVAL_SECONDS = _cli.WATCH_POLL_INTERVAL_SECONDS

__all__ = [
    "__version__",
    "InitActivityMonitor",
    "SessionContextMismatchError",
    "WATCH_POLL_INTERVAL_SECONDS",
    "apply_answers_to_brand_content",
    "apply_brand_inputs",
    "bootstrap_runtime_files",
    "brand_file_requires_bootstrap",
    "build_context_synthesis_data",
    "capture_file_signature",
    "create_skills_registry",
    "enforce_engine_version_guard",
    "format_git_describe_version",
    "get_arms_root",
    "get_project_root",
    "infer_brand_context_from_project",
    "infer_agent_from_task",
    "is_development_engine",
    "is_unresolved_version",
    "load_agents_registry",
    "main",
    "migrate_legacy_state",
    "normalize_arms_root",
    "parse_structured_answers",
    "prompt_context_overwrite",
    "remove_obsolete_gemini_skill_artifacts",
    "render_new_project_brand_prompt",
    "render_new_project_brand_questionnaire",
    "render_startup_tasks_content",
    "render_terminal_dashboard",
    "resolve_agents_with_skills",
    "resolve_stack_recommendation",
    "run_init_once",
    "setup_folders",
    "sync_agents",
    "sync_agents_copilot",
    "sync_context_synthesis",
    "sync_engine_instructions",
    "sync_generated_prompts",
    "sync_root_agents_guide",
    "sync_skills_copilot",
    "sync_workflow",
    "update_session",
    "wait_for_brand_change",
]


def wait_for_brand_change(project_root, previous_signature):
    return _cli.wait_for_brand_change(
        project_root,
        previous_signature,
        poll_interval=WATCH_POLL_INTERVAL_SECONDS,
    )


def main():
    return _cli.main()


if __name__ == "__main__":
    main()
