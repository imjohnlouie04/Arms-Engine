import datetime
import os
import re

from .bm25 import score_tokens as _bm25_score_tokens
from .paths import WorkspacePaths
from .session import (
    MEMORY_APPROVED_MARKER,
    MEMORY_ENTRY_ID_RE,
    MEMORY_PENDING_MARKER,
    build_memory_suggestion_lesson,
    choose_memory_suggestion_section,
    parse_markdown_sections,
    read_text_file,
    resolve_memory_suggestion,
    update_session,
    write_markdown_sections,
)

# ── Triage thresholds ────────────────────────────────────────────────────────
TRIAGE_AUTO_APPROVE_THRESHOLD = 0.60
TRIAGE_AUTO_DISCARD_THRESHOLD = 0.15
STALE_PENDING_DAYS = 7

# ── Required MEMORY.md sections (from MEMORY_TEMPLATE) ──────────────────────
MEMORY_REQUIRED_SECTIONS = [
    "Project Context & MVP",
    "Primary Use Case & Implications",
    "Phase 2 Backlog",
    "Developer Preferences",
    "Known Bugs & Fixes",
]

# ── Scoring vocabularies ─────────────────────────────────────────────────────
_ACTIONABILITY_VERBS = frozenset({
    "use", "avoid", "always", "never", "prefer", "run", "check", "ensure",
    "require", "set", "enable", "disable", "configure", "install", "update",
    "import", "export", "add", "remove", "fix", "test", "deploy", "build",
    "lint", "migrate", "validate", "sync", "keep", "must", "should", "replace",
    "follow", "enforce", "prevent", "instead", "do", "dont",
})

_SPECIFICITY_PATTERNS = [
    re.compile(r"\.[a-z]{2,5}\b"),              # file extensions like .py .ts .yaml
    re.compile(r"`[^`]+`"),                      # backtick-quoted code
    re.compile(r"\b\w+\.\w+\("),                 # function/method calls
    re.compile(r"\bv\d+[\.\d]*\b"),              # version numbers v1 v2.3
    re.compile(r"--[\w][\w-]*"),                 # CLI flags --flag
    re.compile(
        r"\b(npm|pip|git|arms|supabase|docker|kubectl|python|node|bash)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(sql|rls|api|jwt|orm|cli|env|ci|cd|url|uuid|json|yaml|html|css)\b",
        re.IGNORECASE,
    ),
]


# ── Memory Quality Scorer ─────────────────────────────────────────────────────

def _score_actionability(text: str) -> float:
    """Fraction of action verbs detected; capped at 1.0."""
    words = re.findall(r"[a-z']+", text.lower())
    if not words:
        return 0.0
    matches = sum(1 for w in words if w in _ACTIONABILITY_VERBS)
    return min(1.0, matches / max(1, len(words) / 5))


def _score_specificity(text: str) -> float:
    """Technical term density based on pattern hits; capped at 1.0."""
    hits = sum(len(p.findall(text)) for p in _SPECIFICITY_PATTERNS)
    length_units = max(1, len(text) / 40)
    return min(1.0, hits / length_units)


def _score_uniqueness(lesson: str, existing_approved_lessons: list) -> float:
    """1.0 = totally novel; 0.0 = identical to an existing approved lesson."""
    if not existing_approved_lessons:
        return 1.0
    lesson_tokens = re.findall(r"\w+", lesson.lower())
    if not lesson_tokens:
        return 0.0
    max_sim = 0.0
    for existing in existing_approved_lessons:
        tokens = re.findall(r"\w+", existing.lower())
        if not tokens:
            continue
        score = _bm25_score_tokens(lesson_tokens, tokens, tokens)
        max_val = max(1.0, _bm25_score_tokens(tokens, tokens, tokens))
        max_sim = max(max_sim, score / max_val)
    return max(0.0, 1.0 - max_sim)


def _score_length(text: str) -> float:
    """Optimal-length reward curve; 0.0 for very short, peak at 40–300 chars."""
    n = len(text)
    if n < 10:
        return 0.0
    if n < 20:
        return 0.2
    if n < 40:
        return 0.4 + 0.6 * ((n - 20) / 20)
    if n <= 300:
        return 1.0
    if n <= 500:
        return 1.0 - 0.5 * ((n - 300) / 200)
    return 0.3


def _score_uniqueness(lesson: str, existing_approved_lessons: list) -> float:
    """1.0 = totally novel; 0.0 = identical to an existing approved lesson."""
    if not existing_approved_lessons:
        return 1.0
    if not lesson.strip():
        return 0.0
    max_sim = 0.0
    for existing in existing_approved_lessons:
        if not existing.strip():
            continue
        score = _bm25_score_tokens(lesson, existing, existing)
        norm = max(1.0, _bm25_score_tokens(existing, existing, ""))
        max_sim = max(max_sim, score / norm)
    return max(0.0, 1.0 - max_sim)


def score_memory_entry(lesson: str, existing_approved_lessons: list) -> float:
    """Return a composite quality score 0.0–1.0 for a candidate memory lesson.

    Dimensions (weights before length multiplier):
    - actionability  0.35
    - specificity    0.30
    - uniqueness     0.35

    Length acts as a multiplier so very short entries are capped near 0.0
    regardless of other dimensions.
    """
    a = _score_actionability(lesson)
    s = _score_specificity(lesson)
    u = _score_uniqueness(lesson, existing_approved_lessons)
    ln = _score_length(lesson)
    return round((0.35 * a + 0.30 * s + 0.35 * u) * ln, 4)


# ── Memory Self-Repair ────────────────────────────────────────────────────────

def _parse_entry_date(draft_id: str):
    """Parse the date embedded in a ``memory-YYYYMMDD-NN`` ID, or None."""
    m = re.match(r"memory-(\d{8})-\d+", draft_id or "")
    if not m:
        return None
    try:
        return datetime.datetime.strptime(m.group(1), "%Y%m%d").date()
    except ValueError:
        return None


def repair_memory_file(project_root: str) -> dict:
    """Fix structural issues in MEMORY.md in-place.

    Actions performed:
    - Restore any missing required section headers.
    - Remove exact-duplicate approved entries within a section.
    - Expire stale ``[PENDING APPROVAL]`` entries older than STALE_PENDING_DAYS.
    - Strip malformed entries that have neither a valid marker nor meaningful text.

    Returns a dict with ``repaired``, ``expired``, and ``deduplicated`` lists.
    """
    wp = WorkspacePaths(project_root)
    memory_path = wp.memory
    if not os.path.isfile(memory_path):
        return {"repaired": [], "expired": [], "deduplicated": []}

    preamble, sections = load_memory_sections(project_root)
    today = datetime.date.today()
    repaired = []
    expired = []
    deduplicated = []

    # Ensure all required sections exist.
    for sec in MEMORY_REQUIRED_SECTIONS:
        if sec not in sections:
            sections[sec] = ""
            repaired.append(f"Restored missing section: {sec}")

    # Per-section cleanup.
    for sec in list(sections.keys()):
        body = sections[sec] or ""
        lines = body.splitlines()
        new_lines = []
        seen_approved = set()

        for raw_line in lines:
            stripped = raw_line.strip()
            if not stripped:
                new_lines.append(raw_line)
                continue

            is_pending = MEMORY_PENDING_MARKER in raw_line
            is_approved = MEMORY_APPROVED_MARKER in raw_line

            if is_pending:
                # Expire stale pending entries.
                m = MEMORY_ENTRY_ID_RE.search(raw_line)
                draft_id = m.group(1) if m else None
                entry_date = _parse_entry_date(draft_id) if draft_id else None
                if entry_date and (today - entry_date).days > STALE_PENDING_DAYS:
                    expired.append(draft_id or stripped[:80])
                    continue

            if is_approved:
                # Deduplicate exact approved entries within section.
                # Key on the lesson text (everything after the marker block).
                lesson_text = re.sub(r"\[APPROVED\]\[memory-[^\]]+\]:\s*", "", stripped)
                lesson_text = re.sub(r"^[-*]\s*", "", lesson_text).strip().lower()
                if lesson_text in seen_approved:
                    deduplicated.append(stripped[:80])
                    continue
                seen_approved.add(lesson_text)

            new_lines.append(raw_line)

        sections[sec] = "\n".join(new_lines)

    write_memory_sections(project_root, preamble, sections)
    return {"repaired": repaired, "expired": expired, "deduplicated": deduplicated}


# ── Intelligent Memory Triage ─────────────────────────────────────────────────

def _collect_approved_lessons(sections: dict) -> list:
    """Extract lesson texts from all ``[APPROVED]`` entries across sections."""
    lessons = []
    for body in sections.values():
        for raw_line in (body or "").splitlines():
            if MEMORY_APPROVED_MARKER in raw_line:
                lesson = re.sub(r"\[APPROVED\]\[memory-[^\]]+\]:\s*", "", raw_line.strip())
                lesson = re.sub(r"^[-*]\s*", "", lesson).strip()
                if lesson:
                    lessons.append(lesson)
    return lessons


def _collect_pending_entries(sections: dict) -> list:
    """Return list of dicts for every ``[PENDING APPROVAL]`` entry."""
    entries = []
    for sec, body in sections.items():
        for raw_line in (body or "").splitlines():
            if MEMORY_PENDING_MARKER not in raw_line:
                continue
            m = MEMORY_ENTRY_ID_RE.search(raw_line)
            draft_id = m.group(1) if m else None
            lesson = re.sub(r"\[PENDING APPROVAL\]\[memory-[^\]]+\]:\s*", "", raw_line.strip())
            lesson = re.sub(r"^[-*]\s*", "", lesson).strip()
            if lesson and draft_id:
                entries.append({"section": sec, "draft_id": draft_id, "lesson": lesson, "raw": raw_line})
    return entries


def smart_triage_pending_memory(project_root: str, arms_root: str) -> dict:
    """Intelligently triage all ``[PENDING APPROVAL]`` entries in MEMORY.md.

    Decision rules:
    - score >= TRIAGE_AUTO_APPROVE_THRESHOLD  → auto-approve (append as APPROVED)
    - score <  TRIAGE_AUTO_DISCARD_THRESHOLD  → auto-discard (remove silently)
    - otherwise                               → keep pending, surface for user review

    Prints a clear summary and a per-entry review block for marginal entries so
    the user knows exactly what commands to run.

    Returns ``{"approved": [...], "discarded": [...], "needs_review": [...]}``
    """
    wp = WorkspacePaths(project_root)
    if not os.path.isfile(wp.memory):
        return {"approved": [], "discarded": [], "needs_review": []}

    # Run self-repair first so we start with a clean file.
    repair = repair_memory_file(project_root)
    if repair["expired"]:
        print(f"🔧 Memory repair: expired {len(repair['expired'])} stale pending entries.")
    if repair["deduplicated"]:
        print(f"🔧 Memory repair: removed {len(repair['deduplicated'])} duplicate approved entries.")
    if repair["repaired"]:
        for msg in repair["repaired"]:
            print(f"🔧 Memory repair: {msg}")

    preamble, sections = load_memory_sections(project_root)
    approved_lessons = _collect_approved_lessons(sections)
    pending_entries = _collect_pending_entries(sections)

    if not pending_entries:
        return {"approved": [], "discarded": [], "needs_review": []}

    approved_out = []
    discarded_out = []
    needs_review_out = []

    # Score every pending entry and collect decisions.
    for entry in pending_entries:
        score = score_memory_entry(entry["lesson"], approved_lessons)
        entry["score"] = score
        if score >= TRIAGE_AUTO_APPROVE_THRESHOLD:
            approved_out.append(entry)
        elif score < TRIAGE_AUTO_DISCARD_THRESHOLD:
            discarded_out.append(entry)
        else:
            needs_review_out.append(entry)

    # Auto-approve high-quality entries.
    for entry in approved_out:
        append_memory_entry(
            project_root, arms_root,
            section=entry["section"],
            lesson=entry["lesson"],
            draft_id=entry["draft_id"],
        )
        print(f"✅ Auto-approved [{entry['draft_id']}]: {entry['lesson'][:80]}")

    # Auto-discard low-quality entries by removing their raw lines.
    if discarded_out:
        reload_preamble, reload_sections = load_memory_sections(project_root)
        for entry in discarded_out:
            sec_body = reload_sections.get(entry["section"], "")
            lines = [ln for ln in sec_body.splitlines() if ln.strip() != entry["raw"].strip()]
            reload_sections[entry["section"]] = "\n".join(lines)
            print(f"🗑️  Auto-discarded [{entry['draft_id']}]: {entry['lesson'][:80]}")
        write_memory_sections(project_root, reload_preamble, reload_sections)

    # Surface marginal entries for user review.
    if needs_review_out:
        today = datetime.date.today()
        print()
        print("─" * 70)
        print(f"🔬 Memory Review Required — {len(needs_review_out)} entr{'y' if len(needs_review_out)==1 else 'ies'} need your decision")
        print("─" * 70)
        for i, entry in enumerate(needs_review_out, start=1):
            expiry_date = _parse_entry_date(entry["draft_id"])
            expiry_str = (
                str(expiry_date + datetime.timedelta(days=STALE_PENDING_DAYS))
                if expiry_date else "unknown"
            )
            score_bar = "🟡" if entry["score"] >= 0.35 else "🔴"
            print(f"\n  [{i}] Section:  {entry['section']}")
            print(f"      Score:    {entry['score']:.2f}  {score_bar}  (marginal)")
            lesson_display = entry["lesson"]
            if len(lesson_display) > 100:
                lesson_display = lesson_display[:97] + "..."
            print(f"      Lesson:   \"{lesson_display}\"")
            print(f"      ▶ Approve: arms memory append --draft-id {entry['draft_id']}")
            print(f"      ⌛ Expires: {expiry_str} (auto-discarded if not approved)")
        print()
        print("─" * 70)
        print(f"ℹ️  Entries above will auto-expire after {STALE_PENDING_DAYS} days.")
        print("─" * 70)
        print()

    total = len(approved_out) + len(discarded_out) + len(needs_review_out)
    if total:
        print(
            f"📊 Memory triage: {len(approved_out)} approved, "
            f"{len(discarded_out)} discarded, "
            f"{len(needs_review_out)} awaiting review  (of {total} pending)"
        )

    return {"approved": approved_out, "discarded": discarded_out, "needs_review": needs_review_out}


def identify_memory_command(command_parts: tuple) -> str:
    """Return ``"draft"``, ``"append"``, or ``"triage"`` for the given command parts, or empty string."""
    normalized = tuple(part.strip().lower() for part in command_parts if part.strip())
    if normalized == ("memory", "draft"):
        return "draft"
    if normalized == ("memory", "append"):
        return "append"
    if normalized == ("memory", "triage"):
        return "triage"
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
    """Dispatch a ``memory draft``, ``memory append``, or ``memory triage`` command."""
    if command_name == "triage":
        result = smart_triage_pending_memory(project_root, arms_root)
        if not any(result.values()):
            print("✅ No pending memory entries to triage.")
        return

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


def auto_stage_memory_draft_from_task(
    project_root: str,
    task_text: str,
    status: str,
    blockers_text: str = "None",
    dependencies: str = "",
) -> dict | None:
    """Auto-stage a pending memory draft for important task lifecycle outcomes.

    This captures lessons automatically so the user only needs to approve later.
    """
    normalized_status = (status or "").strip().lower()
    if normalized_status not in {"done", "blocked", "failed"}:
        return None

    section = choose_memory_suggestion_section(task_text, status, blockers_text, dependencies)
    lesson = build_memory_suggestion_lesson(task_text, status, blockers_text, dependencies)
    result = create_memory_draft(project_root, section, lesson)
    return {
        "section": result["section"],
        "draft_id": result["draft_id"],
        "entry_text": result["entry_text"],
        "duplicate": result.get("duplicate", False),
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
