import argparse
import hashlib
import os
import sys
import time

from . import __version__
from .brand import (
    IGNORED_PROJECT_ENTRIES,
    PROJECT_PRESETS,
    apply_brand_inputs,
    format_available_presets,
    initialize_brand_context,
)
from .prompts import (
    build_context_synthesis_data,
    render_startup_tasks_content,
    sync_context_synthesis,
    sync_generated_prompts,
)
from .session import (
    SessionContextMismatchError,
    bootstrap_runtime_files,
    enforce_engine_version_guard,
    migrate_legacy_state,
    setup_folders,
    update_session,
)
from .skills import (
    clean_legacy_gemini_skill_mirror,
    create_skills_registry,
    discover_agents_and_skills,
    discover_skills,
    sync_agents,
    sync_agents_copilot,
    sync_copilot_instructions,
    sync_engine_instructions,
    sync_skills_copilot,
    sync_workflow,
)


WATCH_POLL_INTERVAL_SECONDS = 2.0
CURRENT_PROJECT_ROOT_MARKERS = (".git", ".arms", ".gemini", "package.json")
LEGACY_PROJECT_ROOT_STRONG_MARKERS = (
    "SESSION.md",
    "session.md",
    "SESSION_ARCHIVE.md",
    "session_archive.md",
    "BRAND.md",
    "brand.md",
    "brand-context.md",
)
LEGACY_PROJECT_ROOT_HINT_MARKERS = (
    "MEMORY.md",
    "memory.md",
    "RULES.md",
    "rules.md",
    "GEMINI.md",
    "gemini.md",
    "agents.yaml",
    "agents",
)


def get_arms_root():
    return os.path.dirname(os.path.abspath(__file__))


def normalize_arms_root(path):
    candidate = os.path.abspath(path)
    package_root = os.path.join(candidate, "arms_engine")
    if os.path.isdir(package_root) and os.path.exists(os.path.join(package_root, "agents.yaml")):
        return package_root
    return candidate


def has_project_root_markers(path):
    if any(os.path.exists(os.path.join(path, marker)) for marker in CURRENT_PROJECT_ROOT_MARKERS):
        return True

    if any(os.path.exists(os.path.join(path, marker)) for marker in LEGACY_PROJECT_ROOT_STRONG_MARKERS):
        return True

    hint_count = sum(
        1
        for marker in LEGACY_PROJECT_ROOT_HINT_MARKERS
        if os.path.exists(os.path.join(path, marker))
    )
    return hint_count >= 2


def get_project_root():
    curr = os.getcwd()
    original_cwd = curr

    meaningful_entries = [
        name for name in os.listdir(original_cwd)
        if name not in IGNORED_PROJECT_ENTRIES and not name.startswith(".")
    ]
    if not meaningful_entries and not has_project_root_markers(original_cwd):
        probe = os.path.dirname(original_cwd)
        while probe != os.path.dirname(probe):
            if has_project_root_markers(probe):
                return probe
            probe = os.path.dirname(probe)
        return original_cwd

    while curr != os.path.dirname(curr):
        if has_project_root_markers(curr):
            return curr
        curr = os.path.dirname(curr)
    return original_cwd


def read_answers_input(args):
    if args.answers_text:
        return args.answers_text
    if not args.answers_file:
        return ""
    if args.answers_file == "-":
        return sys.stdin.read()
    with open(args.answers_file, "r", encoding="utf-8") as f:
        return f.read()


def capture_file_signature(path):
    if not os.path.exists(path):
        return None
    try:
        with open(path, "rb") as f:
            return hashlib.sha1(f.read()).hexdigest()
    except OSError:
        return None


def wait_for_brand_change(project_root, previous_signature, poll_interval=WATCH_POLL_INTERVAL_SECONDS):
    brand_path = os.path.join(project_root, ".arms/BRAND.md")
    print()
    print(f"👀 Watch mode active. Waiting for changes to {brand_path} ...")
    print("   Press Ctrl+C to stop watching.")
    while True:
        time.sleep(poll_interval)
        current_signature = capture_file_signature(brand_path)
        if current_signature != previous_signature:
            print("🔄 Detected BRAND.md change. Re-running init...")
            return


def prompt_context_overwrite(error):
    print()
    print(f"⚠️  Context Mismatch: Session file points to '{error.existing_root}'")
    print(f"   Current root: {error.current_root}")
    if not sys.stdin.isatty():
        print("   Non-interactive input detected. Refusing to overwrite session context automatically.")
        return False
    try:
        confirm = input("Overwrite session with current context? (y/n): ")
    except (EOFError, KeyboardInterrupt):
        print()
        return False
    return confirm.strip().lower() == "y"


def run_init_once(
    project_root,
    arms_root,
    full_command,
    is_yolo,
    preset_name="",
    answers_text="",
    allow_engine_downgrade=False,
    show_banner=True,
    context_overwrite=None,
):
    arms_root = normalize_arms_root(arms_root)
    if show_banner:
        print("🚀 Initializing ARMS Engine...")
        print(f"📂 Project: {project_root}")
        print(f"🛡️  Engine:  {arms_root}")
        if is_yolo:
            print("⚡ Mode:    YOLO (Full Automation)")

    setup_folders(project_root)
    migrate_legacy_state(project_root)
    enforce_engine_version_guard(
        project_root,
        arms_root,
        allow_engine_downgrade=allow_engine_downgrade,
    )
    bootstrap_runtime_files(project_root)
    clean_legacy_gemini_skill_mirror(project_root)
    sync_agents(arms_root, project_root)
    sync_agents_copilot(arms_root, project_root)
    sync_skills_copilot(arms_root, project_root)
    create_skills_registry(arms_root, project_root)
    sync_workflow(arms_root, project_root)
    brand_context_state = initialize_brand_context(project_root)
    if preset_name or answers_text:
        inputs_applied = apply_brand_inputs(
            project_root,
            preset_name=preset_name,
            answers_text=answers_text,
        )
        if inputs_applied:
            brand_context_state = initialize_brand_context(project_root)
    context_synthesis_ready = False
    generated_prompts_ready = False
    if brand_context_state and brand_context_state.get("status") == "questions_required":
        sync_context_synthesis(project_root)
        sync_generated_prompts(project_root)
    else:
        context_synthesis_ready = sync_context_synthesis(project_root)
        generated_prompts_ready = sync_generated_prompts(project_root)

    skills_list = discover_skills(arms_root)
    agents_list = discover_agents_and_skills(arms_root)
    synthesis_data = build_context_synthesis_data(project_root)
    startup_tasks_content = ""
    if synthesis_data is not None:
        startup_tasks_content = render_startup_tasks_content(synthesis_data)
    session_updated = update_session(
        project_root,
        arms_root,
        skills_list,
        agents_list,
        yolo=is_yolo,
        startup_tasks_content=startup_tasks_content,
        context_overwrite=context_overwrite,
    )
    if not session_updated:
        return {
            "status": "aborted",
            "brand_signature": capture_file_signature(os.path.join(project_root, ".arms/BRAND.md")),
        }

    sync_engine_instructions(arms_root, project_root)
    sync_copilot_instructions(arms_root, project_root)

    if "compress" in full_command.lower():
        print("🗜️  Optimization mode triggered. (Caveman skill stub activated)")

    brand_signature = capture_file_signature(os.path.join(project_root, ".arms/BRAND.md"))
    if brand_context_state and brand_context_state.get("status") == "questions_required":
        print()
        print(brand_context_state["prompt"])
        print("\n✅ ARMS Engine sequence complete. Awaiting Brand Context answers. → HALT")
        return {
            "status": "questions_required",
            "brand_signature": brand_signature,
        }
    if is_yolo:
        if context_synthesis_ready:
            print("📋 Context synthesis refreshed at .arms/CONTEXT_SYNTHESIS.md")
        if generated_prompts_ready:
            print("🧠 Agent-ready prompts refreshed at .arms/GENERATED_PROMPTS.md")
        print("\n✅ ARMS Engine ready. Fleet mode activated.")
    else:
        if context_synthesis_ready:
            print("📋 Context synthesis refreshed at .arms/CONTEXT_SYNTHESIS.md")
        if generated_prompts_ready:
            print("🧠 Agent-ready prompts refreshed at .arms/GENERATED_PROMPTS.md")
        print("\n✅ ARMS Engine sequence complete. → HALT")
    return {
        "status": "complete",
        "brand_signature": brand_signature,
    }


def main():
    parser = argparse.ArgumentParser(description="ARMS Engine Activator")
    parser.add_argument("command", nargs="*", default=["init"], help="Command to run (e.g., init, init yolo, start)")
    parser.add_argument("--root", help="Override arms root path")
    parser.add_argument(
        "--preset",
        help=f"Apply a new-project preset before resuming init (available: {format_available_presets()})",
    )
    parser.add_argument(
        "--answers-file",
        help="Apply structured intake answers from a file. Use '-' to read from stdin.",
    )
    parser.add_argument(
        "--answers-text",
        help="Apply structured intake answers inline. Supports 'Field: value' and numbered answers.",
    )
    parser.add_argument(
        "--allow-engine-downgrade",
        action="store_true",
        help="Allow init to continue even if the project was last synced by a newer engine version.",
    )
    parser.add_argument(
        "--watch",
        action="store_true",
        help="Watch .arms/BRAND.md and auto-rerun init while the project is waiting on brand context.",
    )
    parser.add_argument("--version", action="version", version=f"ARMS Engine {__version__}")
    args = parser.parse_args()

    full_command = " ".join(args.command)
    is_yolo = "yolo" in full_command.lower()
    project_root = get_project_root()

    home_dir = os.path.expanduser("~")
    if os.path.abspath(project_root) == home_dir:
        print("❌ ERROR: Cannot initialize ARMS in the home directory.")
        print("   Please navigate to a specific project folder first.")
        raise SystemExit(1)

    arms_root = normalize_arms_root(args.root) if args.root else get_arms_root()
    if args.preset and args.preset not in PROJECT_PRESETS:
        print(f"❌ ERROR: Unknown preset '{args.preset}'.")
        print(f"   Available presets: {format_available_presets()}")
        raise SystemExit(1)
    try:
        answers_text = read_answers_input(args)
    except OSError as exc:
        print(f"❌ ERROR: Unable to read answers input: {exc}")
        raise SystemExit(1)

    pending_preset = (args.preset or "").strip()
    pending_answers_text = answers_text
    pending_context_overwrite = None
    show_banner = True

    while True:
        try:
            result = run_init_once(
                project_root,
                arms_root,
                full_command,
                is_yolo,
                preset_name=pending_preset,
                answers_text=pending_answers_text,
                allow_engine_downgrade=args.allow_engine_downgrade,
                show_banner=show_banner,
                context_overwrite=pending_context_overwrite,
            )
        except SessionContextMismatchError as exc:
            if not prompt_context_overwrite(exc):
                print("Aborting to preserve session state.")
                raise SystemExit(1)
            pending_context_overwrite = True
            show_banner = False
            continue
        if result["status"] == "aborted":
            raise SystemExit(1)
        pending_context_overwrite = None
        if not args.watch or result["status"] != "questions_required":
            break
        pending_preset = ""
        pending_answers_text = ""
        show_banner = False
        try:
            wait_for_brand_change(project_root, result["brand_signature"])
        except KeyboardInterrupt:
            print("\n⏹️  Watch mode stopped.")
            raise SystemExit(130)


if __name__ == "__main__":
    main()
