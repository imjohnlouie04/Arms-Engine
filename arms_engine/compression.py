import datetime
import os
import re

from .session import (
    SESSION_ARCHIVE_TEMPLATE,
    normalize_active_tasks_table,
    parse_markdown_sections,
    read_text_file,
    write_markdown_sections,
    write_text_atomic,
)


ARCHIVE_TOKEN_LIMIT = 20000
TASK_TABLE_HEADER = "| # | Task | Assigned Agent | Active Skill | Dependencies | Status |"
TASK_TABLE_DIVIDER = "|---|------|----------------|--------------|--------------|--------|"
ARCHIVABLE_STATUSES = {"done", "cancelled", "canceled"}
STATUS_PRIORITY = {
    "blocked": 0,
    "in progress": 1,
    "pre-flight": 2,
    "pending": 3,
    "failed": 4,
}
MEMORY_STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "been",
    "being",
    "but",
    "by",
    "for",
    "from",
    "in",
    "into",
    "is",
    "just",
    "of",
    "on",
    "or",
    "really",
    "so",
    "that",
    "the",
    "then",
    "this",
    "to",
    "very",
    "was",
    "were",
    "with",
}


def compress_workspace(project_root):
    session_summary = compress_session_state(project_root)
    memory_summary = compress_memory_file(project_root)
    history_summary = maintain_archive_summary(project_root)
    return {
        "archived_tasks": session_summary["archived_tasks"],
        "archived_notes": session_summary["archived_notes"],
        "remaining_tasks": session_summary["remaining_tasks"],
        "memory_entries": memory_summary["entries"],
        "history_summary_updated": history_summary["updated"],
        "history_summary_sections": history_summary["sections"],
    }


def format_compression_summary(summary):
    lines = [
        "🗜️  Compression complete.",
        "   - Archived {} completed task(s).".format(summary["archived_tasks"]),
        "   - Compacted {} memory entry line(s).".format(summary["memory_entries"]),
        "   - Active task board now holds {} open task(s).".format(summary["remaining_tasks"]),
    ]
    if summary["archived_notes"]:
        lines.append("   - Archived {} completed note line(s).".format(summary["archived_notes"]))
    if summary["history_summary_updated"]:
        lines.append(
            "   - Refreshed `.arms/HISTORY_SUMMARY.md` from {} archive section(s).".format(
                summary["history_summary_sections"]
            )
        )
    return "\n".join(lines)


def compress_session_state(project_root):
    session_path = os.path.join(project_root, ".arms", "SESSION.md")
    if not os.path.exists(session_path):
        raise FileNotFoundError(session_path)

    preamble, sections = parse_markdown_sections(read_text_file(session_path))
    active_rows = parse_task_rows(sections.get("Active Tasks", ""))
    completed_notes = extract_completed_notes(sections.get("Completed Tasks", "- None"))

    archived_rows = []
    remaining_rows = []
    for row in active_rows:
        if row["Status"].strip().lower() in ARCHIVABLE_STATUSES:
            archived_rows.append(row)
        else:
            remaining_rows.append(row)

    remaining_rows = sort_active_rows(remaining_rows)
    if archived_rows or completed_notes:
        append_archive_entry(project_root, archived_rows, completed_notes)

    sections["Active Tasks"] = render_task_table(remaining_rows)
    sections["Completed Tasks"] = "- None"
    write_markdown_sections(session_path, preamble, sections)

    return {
        "archived_tasks": len(archived_rows),
        "archived_notes": len(completed_notes),
        "remaining_tasks": len(remaining_rows),
    }


def compress_memory_file(project_root):
    memory_path = os.path.join(project_root, ".arms", "MEMORY.md")
    if not os.path.exists(memory_path):
        raise FileNotFoundError(memory_path)

    preamble, sections = parse_markdown_sections(read_text_file(memory_path))
    compressed_sections = {}
    total_entries = 0

    for title, body in sections.items():
        entries = []
        for raw_line in body.splitlines():
            entry = build_memory_entry(title, raw_line)
            if not entry or entry in entries:
                continue
            entries.append(entry)
        total_entries += len(entries)
        compressed_sections[title] = "\n".join(entries)

    write_markdown_sections(memory_path, preamble, compressed_sections)
    return {"entries": total_entries}


def maintain_archive_summary(project_root):
    archive_path = os.path.join(project_root, ".arms", "SESSION_ARCHIVE.md")
    if not os.path.exists(archive_path):
        return {"updated": False, "sections": 0}

    archive_content = read_text_file(archive_path)
    if count_tokens(archive_content) <= ARCHIVE_TOKEN_LIMIT:
        return {"updated": False, "sections": 0}

    archive_sections = extract_archive_sections(archive_content)
    if not archive_sections:
        return {"updated": False, "sections": 0}

    summarized_sections = archive_sections[:-1] or archive_sections
    summary_lines = []
    for section in summarized_sections:
        date_text = extract_archive_date(section)
        context = extract_archive_context(section)
        task_count = count_archive_tasks(section)
        note_count = count_archive_notes(section)
        summary_lines.append(
            "- {} | {} | {} task(s) | {} note line(s)".format(
                date_text,
                context,
                task_count,
                note_count,
            )
        )

    history_summary_path = os.path.join(project_root, ".arms", "HISTORY_SUMMARY.md")
    history_summary_content = """# ARMS History Summary

> Generated by `arms init compress`. Older archive slices are summarized here while full records remain in `.arms/SESSION_ARCHIVE.md`.

## Summary
{}
""".format(
        "\n".join(summary_lines)
    )
    write_text_atomic(history_summary_path, history_summary_content)
    return {"updated": True, "sections": len(summarized_sections)}


def append_archive_entry(project_root, archived_rows, completed_notes):
    archive_path = os.path.join(project_root, ".arms", "SESSION_ARCHIVE.md")
    if os.path.exists(archive_path):
        archive_content = read_text_file(archive_path).rstrip()
    else:
        archive_content = SESSION_ARCHIVE_TEMPLATE.rstrip()

    timestamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    block_lines = [
        "## Archive — {}".format(timestamp),
        "### Context: Compression pass",
    ]
    if archived_rows:
        block_lines.extend(
            [
                "",
                "| # | Task | Agent | Status | Completed |",
                "|---|------|-------|--------|-----------|",
            ]
        )
        for index, row in enumerate(archived_rows, start=1):
            block_lines.append(
                "| {index} | {task} | {agent} | {status} | {completed} |".format(
                    index=index,
                    task=row["Task"],
                    agent=row["Assigned Agent"],
                    status=row["Status"],
                    completed=timestamp,
                )
            )
    if completed_notes:
        block_lines.extend(["", "### Completed Notes"])
        block_lines.extend(completed_notes)

    new_content = "{}\n\n{}\n".format(archive_content, "\n".join(block_lines))
    write_text_atomic(archive_path, new_content)


def parse_task_rows(content):
    rows = []
    for raw_line in content.splitlines():
        line = raw_line.strip()
        if not (line.startswith("|") and line.endswith("|")):
            continue
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        if len(cells) != 6:
            continue
        first_cell = cells[0].replace(" ", "")
        if cells[0] == "#" or set(first_cell) <= {"-"}:
            continue
        rows.append(
            {
                "#": cells[0],
                "Task": cells[1],
                "Assigned Agent": cells[2],
                "Active Skill": cells[3],
                "Dependencies": cells[4],
                "Status": cells[5],
            }
        )
    return rows


def render_task_table(rows):
    lines = [TASK_TABLE_HEADER, TASK_TABLE_DIVIDER]
    for index, row in enumerate(rows, start=1):
        lines.append(
            "| {index} | {task} | {agent} | {skill} | {deps} | {status} |".format(
                index=index,
                task=row["Task"],
                agent=row["Assigned Agent"],
                skill=row["Active Skill"],
                deps=row["Dependencies"],
                status=row["Status"],
            )
        )
    return normalize_active_tasks_table("\n".join(lines))


def sort_active_rows(rows):
    def row_key(item):
        status_rank = STATUS_PRIORITY.get(item["Status"].strip().lower(), len(STATUS_PRIORITY))
        return (
            status_rank,
            item["Assigned Agent"].lower(),
            item["Task"].lower(),
        )

    return sorted(rows, key=row_key)


def extract_completed_notes(content):
    notes = []
    for raw_line in content.splitlines():
        line = raw_line.strip()
        if not line or line == "- None":
            continue
        if line.startswith("- "):
            notes.append(line)
        else:
            notes.append("- {}".format(line))
    return notes


def build_memory_entry(section_title, raw_line):
    line = strip_markdown(raw_line)
    if not line or line.startswith(">"):
        return ""
    if line.startswith("[") and ":" in line:
        return line

    topic = section_title.upper()
    left, right = split_memory_line(line)
    compact_left = compact_phrase(left)
    compact_right = compact_phrase(right)
    if compact_left and compact_right:
        return "[{}] : {} -> {}".format(topic, compact_left, compact_right)
    if compact_left:
        return "[{}] : {}".format(topic, compact_left)
    return ""


def strip_markdown(text):
    cleaned = text.strip()
    cleaned = re.sub(r"^\s*[-*]\s+", "", cleaned)
    cleaned = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", cleaned)
    cleaned = re.sub(r"`([^`]+)`", r"\1", cleaned)
    cleaned = re.sub(r"\*\*([^*]+)\*\*", r"\1", cleaned)
    cleaned = re.sub(r"\*([^*]+)\*", r"\1", cleaned)
    cleaned = re.sub(r"__([^_]+)__", r"\1", cleaned)
    cleaned = re.sub(r"_([^_]+)_", r"\1", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned.strip(" -")


def split_memory_line(line):
    for separator in ("->", "=>", ":", " — ", " - "):
        if separator in line:
            left, right = line.split(separator, 1)
            return left.strip(), right.strip()
    return line, ""


def compact_phrase(text):
    tokens = re.findall(r"<=|>=|==|!=|[A-Za-z0-9_./+-]+|[^\w\s]", text)
    compacted_tokens = []
    for token in tokens:
        if re.fullmatch(r"[A-Za-z]+", token) and token.lower() in MEMORY_STOPWORDS:
            continue
        compacted_tokens.append(token)
    compacted = " ".join(compacted_tokens).strip()
    compacted = re.sub(r"\s+([,.;:!?])", r"\1", compacted)
    compacted = re.sub(r"\s+", " ", compacted)
    if len(compacted) < 6:
        return text.strip()
    return compacted


def count_tokens(text):
    return len(re.findall(r"\S+", text))


def extract_archive_sections(content):
    sections = []
    for chunk in re.split(r"(?=^## Archive — )", content, flags=re.MULTILINE):
        stripped = chunk.strip()
        if stripped.startswith("## Archive — "):
            sections.append(stripped)
    return sections


def extract_archive_date(section):
    first_line = section.splitlines()[0].strip()
    return first_line.replace("## Archive — ", "", 1)


def extract_archive_context(section):
    match = re.search(r"^### Context:\s*(.*)$", section, re.MULTILINE)
    return match.group(1).strip() if match else "Archive"


def count_archive_tasks(section):
    count = 0
    for raw_line in section.splitlines():
        line = raw_line.strip()
        if not (line.startswith("|") and line.endswith("|")):
            continue
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        if len(cells) != 5:
            continue
        first_cell = cells[0].replace(" ", "")
        if cells[0] == "#" or set(first_cell) <= {"-"}:
            continue
        count += 1
    return count


def count_archive_notes(section):
    count = 0
    inside_notes = False
    for raw_line in section.splitlines():
        line = raw_line.strip()
        if line.startswith("### Completed Notes"):
            inside_notes = True
            continue
        if line.startswith("### ") and not line.startswith("### Completed Notes"):
            inside_notes = False
        if inside_notes and line.startswith("- "):
            count += 1
    return count
