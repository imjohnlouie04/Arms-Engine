import datetime
import os

from .paths import WorkspacePaths
from .session import (
    MEMORY_APPROVED_MARKER,
    MEMORY_ENTRY_ID_RE,
    MEMORY_PENDING_MARKER,
    parse_markdown_sections,
    read_text_file,
    resolve_memory_suggestion,
    update_session,
    write_markdown_sections,
)


def identify_memory_command(command_parts: tuple) -> str:
    """Return ``"draft"`` or ``"append"`` for the given command parts, or empty string."""
    normalized = tuple(part.strip().lower() for part in command_parts if part.strip())
    if normalized == ("memory", "draft"):
        return "draft"
    if normalized == ("memory", "append"):
        return "append"
    return ""


def handle_memory_command(
    project_root: str,
    arms_root: str,
    command_name: str,
    section: str = "",
    lesson: str = "",
    draft_id: str = "",
    from_suggestion: str = "",
) -> None:
    """Dispatch a ``memory draft`` or ``memory append`` command and print a structured response."""
    error = validate_memory_command(project_root, command_name, section, lesson, draft_id, from_suggestion)
    if error:
        emit_memory_response(
            command_name,
            project_root,
            updates="None",
            action_lines=[error],
            next_step="Resolve the input issue and rerun the memory command. → HALT",
        )
        raise SystemExit(1)

    if command_name == "draft":
        result = create_memory_draft(project_root, section, lesson, from_suggestion=from_suggestion)
        is_duplicate = result.get("duplicate", False)
        emit_memory_response(
            command_name,
            project_root,
            updates="None" if is_duplicate else "Updated `.arms/MEMORY.md`.",
            action_lines=[
                "Duplicate draft detected — entry already pending under `{}`.".format(result["section"])
                if is_duplicate
                else "Memory draft recorded under `{}.`".format(result["section"]),
                "- Draft ID: `{}`".format(result["draft_id"]),
                "- Status: pending approval",
                "- Entry: `{}`".format(result["entry_text"]),
            ],
            next_step="Review the draft, ask for approval, then run `arms memory append --draft-id {}`. → HALT".format(
                result["draft_id"]
            ),
        )
        return

    result = append_memory_entry(project_root, arms_root, section, lesson, draft_id)
    emit_memory_response(
        command_name,
        project_root,
        updates="Updated `.arms/MEMORY.md` and `.arms/SESSION.md`.",
        action_lines=[
            "Memory lesson approved under `{}.`".format(result["section"]),
            "- Entry ID: `{}`".format(result["draft_id"]),
            "- Status: approved",
            "- Entry: `{}`".format(result["entry_text"]),
            "- Session memory signals refreshed from approved memory.",
        ],
        next_step="Memory workflow complete. Continue with the next task when ready. → HALT",
    )


def validate_memory_command(
    project_root: str,
    command_name: str,
    section: str,
    lesson: str,
    draft_id: str,
    from_suggestion: str,
) -> str:
    """Validate inputs for a memory command; return an error message string or empty string on success."""
    wp = WorkspacePaths(project_root)
    session_path = wp.session
    memory_path = wp.memory
    if not os.path.isfile(session_path) or not os.path.isfile(memory_path):
        return "Structured memory commands require an initialized workspace. Run `arms init` first."
    if command_name == "draft":
        if from_suggestion.strip():
            return ""
        if not section.strip():
            return "`arms memory draft` requires `--section`."
        if not lesson.strip():
            return "`arms memory draft` requires `--lesson`."
        return ""
    if draft_id.strip():
        return ""
    if not section.strip():
        return "`arms memory append` requires either `--draft-id` or `--section` plus `--lesson`."
    if not lesson.strip():
        return "`arms memory append` requires either `--draft-id` or `--section` plus `--lesson`."
    return ""


def create_memory_draft(project_root: str, section: str, lesson: str, from_suggestion: str = "") -> dict:
    """Append a ``[PENDING APPROVAL]`` memory entry to MEMORY.md and return draft metadata."""
    preamble, sections = load_memory_sections(project_root)
    if from_suggestion.strip():
        suggestion = resolve_memory_suggestion(project_root, from_suggestion)
        if suggestion is None:
            raise SystemExit(emit_and_exit_missing_suggestion(project_root, from_suggestion))
        normalized_section = suggestion["section"]
        normalized_lesson = normalize_lesson_text(suggestion["lesson"])
    else:
        normalized_section = normalize_section_name(section)
        normalized_lesson = normalize_lesson_text(lesson)
    draft_id = next_memory_entry_id(sections)
    existing = find_pending_entry_by_text(sections, normalized_section, normalized_lesson)
    if existing is not None:
        return {
            "section": existing["section"],
            "draft_id": existing["draft_id"],
            "entry_text": normalized_lesson,
            "duplicate": True,
        }
    entry = render_memory_entry(MEMORY_PENDING_MARKER, draft_id, normalized_lesson)
    append_section_entry(sections, normalized_section, entry)
    write_memory_sections(project_root, preamble, sections)
    return {
        "section": normalized_section,
        "draft_id": draft_id,
        "entry_text": normalized_lesson,
    }


def append_memory_entry(project_root: str, arms_root: str, section: str, lesson: str, draft_id: str) -> dict:
    """Approve and promote a pending memory draft (or write a new approved entry) to MEMORY.md."""
    preamble, sections = load_memory_sections(project_root)
    normalized_section = normalize_section_name(section) if section.strip() else ""
    normalized_lesson = normalize_lesson_text(lesson) if lesson.strip() else ""
    normalized_draft_id = draft_id.strip()

    if normalized_draft_id:
        located = replace_pending_entry_with_approved(sections, normalized_draft_id)
        if located is None:
            if approved_entry_exists(sections, normalized_draft_id):
                result = find_entry_by_id(sections, normalized_draft_id, approved_only=True)
                refresh_memory_session(project_root, arms_root)
                return result
            raise SystemExit(emit_and_exit_not_found(project_root, normalized_draft_id))
        normalized_section = located["section"]
        normalized_lesson = located["entry_text"]
    else:
        normalized_draft_id = next_memory_entry_id(sections)
        matching_pending = find_pending_entry_by_text(sections, normalized_section, normalized_lesson)
        approved_entry = render_memory_entry(MEMORY_APPROVED_MARKER, normalized_draft_id, normalized_lesson)
        if matching_pending is not None:
            section_body = split_section_lines(sections.get(matching_pending["section"], ""))
            section_body[matching_pending["index"]] = approved_entry
            sections[matching_pending["section"]] = "\n".join(section_body).strip()
            normalized_section = matching_pending["section"]
            normalized_draft_id = matching_pending["draft_id"]
        elif not approved_entry_text_exists(sections, normalized_section, normalized_lesson):
            append_section_entry(sections, normalized_section, approved_entry)

    write_memory_sections(project_root, preamble, sections)
    refresh_memory_session(project_root, arms_root)
    return {
        "section": normalized_section,
        "draft_id": normalized_draft_id,
        "entry_text": normalized_lesson,
    }


def emit_and_exit_not_found(project_root, draft_id):
    emit_memory_response(
        "append",
        project_root,
        updates="None",
        action_lines=[
            "No pending memory draft matched `{}`.".format(draft_id),
            "Use `arms memory draft --section ... --lesson ...` first or inspect `.arms/MEMORY.md`.",
        ],
        next_step="Create or locate the correct draft before appending. → HALT",
    )
    return 1


def emit_and_exit_missing_suggestion(project_root, suggestion_ref):
    emit_memory_response(
        "draft",
        project_root,
        updates="None",
        action_lines=[
            "No session-derived memory suggestion matched `{}`.".format(suggestion_ref),
            "Review `## Memory Suggestions` in `.arms/SESSION.md` and choose a current suggestion index.",
        ],
        next_step="Pick a valid suggestion and rerun `arms memory draft --from-suggestion <n>`. → HALT",
    )
    return 1


def emit_memory_response(command_name, project_root, updates, action_lines, next_step):
    print("[Speaking Agent]: arms-main-agent")
    print("[Active Skill]:   arms-orchestrator")
    print()
    print("[State Updates]: {}".format(updates))
    print()
    print("[Action / Code]:")
    print("## Memory {}".format("Draft" if command_name == "draft" else "Append"))
    print()
    print("**Project Root:** `{}`".format(project_root))
    print()
    for line in action_lines:
        print(line)
    print()
    print("[Next Step / Blocker]: {}".format(next_step))


def load_memory_sections(project_root):
    memory_path = WorkspacePaths(project_root).memory
    return parse_markdown_sections(read_text_file(memory_path))


def write_memory_sections(project_root, preamble, sections):
    memory_path = WorkspacePaths(project_root).memory
    write_markdown_sections(memory_path, preamble, sections)


def normalize_section_name(section):
    return " ".join((section or "").split()).strip()


def normalize_lesson_text(lesson):
    normalized = " ".join((lesson or "").split()).strip()
    normalized = normalized.lstrip("-*").strip()
    return normalized


def next_memory_entry_id(sections):
    today = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d")
    prefix = "memory-{}".format(today)
    highest = 0
    for body in sections.values():
        for match in MEMORY_ENTRY_ID_RE.findall(body or ""):
            if not match.startswith(prefix):
                continue
            try:
                highest = max(highest, int(match.rsplit("-", 1)[1]))
            except (IndexError, ValueError):
                continue
    return "{}-{:02d}".format(prefix, highest + 1)


def render_memory_entry(marker, draft_id, lesson):
    return "- {}[{}]: {}".format(marker, draft_id, lesson)


def append_section_entry(sections, section, entry):
    existing_lines = split_section_lines(sections.get(section, ""))
    existing_lines.append(entry)
    sections[section] = "\n".join(existing_lines).strip()


def split_section_lines(body):
    return [line for line in (body or "").splitlines() if line.strip()]


def replace_pending_entry_with_approved(sections, draft_id):
    pending_prefix = "{}[{}]:".format(MEMORY_PENDING_MARKER, draft_id)
    approved_prefix = "{}[{}]:".format(MEMORY_APPROVED_MARKER, draft_id)
    for section, body in sections.items():
        lines = split_section_lines(body)
        for index, line in enumerate(lines):
            stripped = line.strip()
            if pending_prefix not in stripped:
                continue
            entry_text = stripped.split(":", 1)[1].strip()
            lines[index] = "- {} {}".format(approved_prefix, entry_text)
            sections[section] = "\n".join(lines).strip()
            return {
                "section": section,
                "draft_id": draft_id,
                "entry_text": entry_text,
            }
    for section, body in sections.items():
        lines = split_section_lines(body)
        for line in lines:
            stripped = line.strip()
            if approved_prefix not in stripped:
                continue
            entry_text = stripped.split(":", 1)[1].strip()
            return {
                "section": section,
                "draft_id": draft_id,
                "entry_text": entry_text,
            }
    return None


def approved_entry_exists(sections, draft_id):
    return find_entry_by_id(sections, draft_id, approved_only=True) is not None


def find_entry_by_id(sections, draft_id, approved_only=False):
    for section, body in sections.items():
        lines = split_section_lines(body)
        for line in lines:
            stripped = line.strip()
            if "[{}]".format(draft_id) not in stripped:
                continue
            if approved_only and MEMORY_APPROVED_MARKER not in stripped:
                continue
            marker = MEMORY_APPROVED_MARKER if MEMORY_APPROVED_MARKER in stripped else MEMORY_PENDING_MARKER
            return {
                "section": section,
                "draft_id": draft_id,
                "entry_text": stripped.split(":", 1)[1].strip(),
                "marker": marker,
            }
    return None


def find_pending_entry_by_text(sections, section, lesson):
    for current_section, body in sections.items():
        if section and current_section != section:
            continue
        lines = split_section_lines(body)
        for index, line in enumerate(lines):
            stripped = line.strip()
            if MEMORY_PENDING_MARKER not in stripped or ":" not in stripped:
                continue
            if stripped.split(":", 1)[1].strip() != lesson:
                continue
            draft_id_match = MEMORY_ENTRY_ID_RE.search(stripped)
            return {
                "section": current_section,
                "index": index,
                "draft_id": draft_id_match.group(1) if draft_id_match else "",
            }
    return None


def approved_entry_text_exists(sections, section, lesson):
    for current_section, body in sections.items():
        if section and current_section != section:
            continue
        for line in split_section_lines(body):
            stripped = line.strip()
            if MEMORY_APPROVED_MARKER not in stripped or ":" not in stripped:
                continue
            if stripped.split(":", 1)[1].strip() == lesson:
                return True
    return False


def refresh_memory_session(project_root, arms_root):
    session_path = WorkspacePaths(project_root).session
    session_content = read_text_file(session_path)
    yolo_enabled = "YOLO Mode: Enabled" in session_content
    update_session(project_root, arms_root, yolo=yolo_enabled)
