import datetime
import os
import re
import shutil

from .budgets import (
    ARCHIVE_TOKEN_LIMIT,
    AUTO_COMPACT_AGENT_OUTPUT_FILE_LIMIT,
    AUTO_COMPACT_MEMORY_CHAR_LIMIT,
    AUTO_COMPACT_REPORT_FILE_LIMIT,
    AUTO_COMPACT_SESSION_CHAR_LIMIT,
)
from .paths import WorkspacePaths
from .session import (
    SESSION_ARCHIVE_TEMPLATE,
    normalize_active_tasks_table,
    parse_markdown_sections,
    read_text_file,
    write_markdown_sections,
    write_text_atomic,
)
from .tables import parse_task_rows


TASK_TABLE_HEADER = "| # | Task | Assigned Agent | Active Skill | Dependencies | Status |"
TASK_TABLE_DIVIDER = "|---|------|----------------|--------------|--------------|--------|"
ARCHIVABLE_STATUSES = {"done", "cancelled", "canceled"}
PROTOCOL_REPORT_PREFIXES = ("review", "fix-plan", "release-notes", "release-check")
REPORT_HISTORY_HEADER = """# ARMS Report History

> Consolidated by ARMS. Older protocol report revisions are appended here while the latest revision stays in its stable `*-latest.md` file.
"""
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
    report_summary = compact_reports_directory(project_root)
    agent_output_summary = compact_agent_outputs(project_root)
    archive_diagnostics = session_summary["archive_diagnostics"]
    if archive_diagnostics and history_summary["history_summary_path"]:
        archive_diagnostics["history_summary_path"] = history_summary["history_summary_path"]
    return {
        "archived_tasks": session_summary["archived_tasks"],
        "archived_notes": session_summary["archived_notes"],
        "remaining_tasks": session_summary["remaining_tasks"],
        "memory_entries": memory_summary["entries"],
        "history_summary_updated": history_summary["updated"],
        "history_summary_sections": history_summary["sections"],
        "history_summary_path": history_summary["history_summary_path"],
        "reports_compacted": report_summary["archived_reports"],
        "report_history_path": report_summary["history_path"],
        "agent_outputs_compacted": agent_output_summary["removed_files"],
        "agent_output_groups_compacted": agent_output_summary["groups_compacted"],
        "archive_diagnostics": archive_diagnostics,
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
    if summary["reports_compacted"]:
        lines.append(
            "   - Consolidated {} older report revision(s) into `{}`.".format(
                summary["reports_compacted"],
                summary["report_history_path"],
            )
        )
    if summary["agent_outputs_compacted"]:
        lines.append(
            "   - Compacted {} older agent output file(s) across {} group(s).".format(
                summary["agent_outputs_compacted"],
                summary["agent_output_groups_compacted"],
            )
        )
    if summary["history_summary_updated"]:
        lines.append(
            "   - Refreshed `.arms/HISTORY_SUMMARY.md` from {} archive section(s).".format(
                summary["history_summary_sections"]
            )
        )
    for diagnostic_line in format_archive_diagnostics_lines(summary.get("archive_diagnostics")):
        lines.append("   - {}".format(diagnostic_line))
    if summary["history_summary_updated"] and summary.get("history_summary_path") and not summary.get("archive_diagnostics"):
        lines.append("   - History summary write: `{}`.".format(summary["history_summary_path"]))
    return "\n".join(lines)


def workspace_compression_reasons(
    project_root,
    session_char_limit=AUTO_COMPACT_SESSION_CHAR_LIMIT,
    memory_char_limit=AUTO_COMPACT_MEMORY_CHAR_LIMIT,
):
    reasons = []
    wp = WorkspacePaths(project_root)
    session_path = wp.session
    memory_path = wp.memory
    archive_path = wp.archive

    if os.path.exists(session_path) and len(read_text_file(session_path)) > session_char_limit:
        reasons.append(".arms/SESSION.md")
    if os.path.exists(memory_path) and len(read_text_file(memory_path)) > memory_char_limit:
        reasons.append(".arms/MEMORY.md")
    if os.path.exists(archive_path) and count_tokens(read_text_file(archive_path)) > ARCHIVE_TOKEN_LIMIT:
        reasons.append(".arms/SESSION_ARCHIVE.md")
    if count_protocol_report_candidates(project_root) > AUTO_COMPACT_REPORT_FILE_LIMIT:
        reasons.append(".arms/reports")
    if count_agent_output_candidates(project_root) > AUTO_COMPACT_AGENT_OUTPUT_FILE_LIMIT:
        reasons.append(".arms/agent-outputs")
    return reasons


def count_protocol_report_candidates(project_root):
    reports_dir = WorkspacePaths(project_root).reports_dir
    if not os.path.isdir(reports_dir):
        return 0
    count = 0
    for name in os.listdir(reports_dir):
        if not name.endswith(".md"):
            continue
        if name == "REPORT_HISTORY.md":
            continue
        if any(name == "{}-latest.md".format(prefix) for prefix in PROTOCOL_REPORT_PREFIXES):
            continue
        if any(name.startswith(prefix + "-") for prefix in PROTOCOL_REPORT_PREFIXES):
            count += 1
    return count


def count_agent_output_candidates(project_root):
    outputs_dir = WorkspacePaths(project_root).outputs_dir
    if not os.path.isdir(outputs_dir):
        return 0
    count = 0
    for root, _, files in os.walk(outputs_dir):
        for name in files:
            if name == "history.md":
                continue
            count += 1
    return count


def compress_session_state(project_root):
    session_path = WorkspacePaths(project_root).session
    if not os.path.exists(session_path):
        raise FileNotFoundError(session_path)

    preamble, sections = parse_markdown_sections(read_text_file(session_path))
    active_rows = parse_task_rows(sections.get("Active Tasks", ""))
    completed_notes = extract_completed_notes(sections.get("Completed Tasks", "- None"))

    archived_rows = []
    remaining_rows = []
    archive_diagnostics = None
    for row in active_rows:
        if row["Status"].strip().lower() in ARCHIVABLE_STATUSES:
            archived_rows.append(row)
        else:
            remaining_rows.append(row)

    remaining_rows = sort_active_rows(remaining_rows)
    if archived_rows or completed_notes:
        archive_diagnostics = append_archive_entry(project_root, archived_rows, completed_notes)

    sections["Active Tasks"] = render_task_table(remaining_rows)
    sections["Completed Tasks"] = "- None"
    write_markdown_sections(session_path, preamble, sections)

    return {
        "archived_tasks": len(archived_rows),
        "archived_notes": len(completed_notes),
        "remaining_tasks": len(remaining_rows),
        "archive_diagnostics": archive_diagnostics,
    }


def compress_memory_file(project_root):
    memory_path = WorkspacePaths(project_root).memory
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

    if total_entries == 0:
        return {"entries": 0, "skipped": "empty_result"}
    write_markdown_sections(memory_path, preamble, compressed_sections)
    return {"entries": total_entries}


def maintain_archive_summary(project_root):
    wp = WorkspacePaths(project_root)
    archive_path = wp.archive
    if not os.path.exists(archive_path):
        return {"updated": False, "sections": 0, "history_summary_path": ""}

    archive_content = read_text_file(archive_path)
    if count_tokens(archive_content) <= ARCHIVE_TOKEN_LIMIT:
        return {"updated": False, "sections": 0, "history_summary_path": ""}

    archive_sections = extract_archive_sections(archive_content)
    if not archive_sections:
        return {"updated": False, "sections": 0, "history_summary_path": ""}

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

    history_summary_path = WorkspacePaths(project_root).history_summary
    history_summary_content = """# ARMS History Summary

> Generated by `arms init compress`. Older archive slices are summarized here while full records remain in `.arms/SESSION_ARCHIVE.md`.

## Summary
{}
""".format(
        "\n".join(summary_lines)
    )
    write_text_atomic(history_summary_path, history_summary_content)
    return {"updated": True, "sections": len(summarized_sections), "history_summary_path": history_summary_path}


def compact_reports_directory(project_root):
    reports_dir = WorkspacePaths(project_root).reports_dir
    if not os.path.isdir(reports_dir):
        return {"archived_reports": 0, "history_path": ""}

    history_path = os.path.join(reports_dir, "REPORT_HISTORY.md")
    archived_reports = 0
    for prefix in PROTOCOL_REPORT_PREFIXES:
        latest_path = os.path.join(reports_dir, "{}-latest.md".format(prefix))
        dated_paths = sorted(
            os.path.join(reports_dir, name)
            for name in os.listdir(reports_dir)
            if name.endswith(".md")
            and name != "{}-latest.md".format(prefix)
            and name.startswith(prefix + "-")
        )
        if not dated_paths:
            continue
        newest_path = dated_paths[-1]
        newest_content = read_text_file(newest_path)
        if os.path.exists(latest_path):
            latest_content = read_text_file(latest_path)
            if latest_content != newest_content:
                append_report_history_entry(history_path, prefix, os.path.basename(latest_path), latest_content)
                archived_reports += 1
        for old_path in dated_paths[:-1]:
            append_report_history_entry(history_path, prefix, os.path.basename(old_path), read_text_file(old_path))
            os.remove(old_path)
            archived_reports += 1
        write_text_atomic(latest_path, newest_content)
        os.remove(newest_path)
    return {"archived_reports": archived_reports, "history_path": history_path}


def append_report_history_entry(history_path, prefix, source_name, content):
    if not content.strip():
        return
    if os.path.exists(history_path):
        history_content = read_text_file(history_path).rstrip()
    else:
        history_content = REPORT_HISTORY_HEADER.rstrip()
    timestamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    block = "\n".join(
        [
            "## Archived Report — {}".format(timestamp),
            "### Type: {}".format(prefix),
            "### Source: {}".format(source_name),
            "",
            "```md",
            content.rstrip(),
            "```",
        ]
    )
    write_text_atomic(history_path, "{}\n\n{}\n".format(history_content, block))


def compact_agent_outputs(project_root):
    outputs_dir = WorkspacePaths(project_root).outputs_dir
    if not os.path.isdir(outputs_dir):
        return {"removed_files": 0, "groups_compacted": 0}

    groups = []
    for name in sorted(os.listdir(outputs_dir)):
        path = os.path.join(outputs_dir, name)
        if os.path.isdir(path):
            groups.append((name, path, True))
    shared_files = [
        os.path.join(outputs_dir, name)
        for name in sorted(os.listdir(outputs_dir))
        if os.path.isfile(os.path.join(outputs_dir, name))
    ]
    if shared_files:
        shared_dir = os.path.join(outputs_dir, "shared")
        os.makedirs(shared_dir, exist_ok=True)
        for path in shared_files:
            shutil.move(path, os.path.join(shared_dir, os.path.basename(path)))
        groups.append(("shared", shared_dir, True))

    removed_files = 0
    groups_compacted = 0
    for group_name, group_dir, is_directory in groups:
        if not is_directory:
            continue
        candidate_files = collect_group_files(group_dir)
        if len(candidate_files) <= 1:
            continue
        newest_path = max(candidate_files, key=os.path.getmtime)
        latest_ext = os.path.splitext(newest_path)[1]
        latest_path = os.path.join(group_dir, "latest{}".format(latest_ext))
        if os.path.abspath(newest_path) != os.path.abspath(latest_path):
            os.makedirs(os.path.dirname(latest_path), exist_ok=True)
            shutil.copy2(newest_path, latest_path)
        history_path = os.path.join(group_dir, "history.md")
        older_paths = [path for path in candidate_files if os.path.abspath(path) != os.path.abspath(newest_path)]
        if os.path.exists(latest_path) and os.path.abspath(newest_path) != os.path.abspath(latest_path):
            older_paths.append(newest_path)
        unique_older_paths = []
        seen = set()
        for path in older_paths:
            normalized = os.path.abspath(path)
            if normalized in seen or normalized == os.path.abspath(latest_path):
                continue
            seen.add(normalized)
            unique_older_paths.append(path)
        for old_path in unique_older_paths:
            append_agent_output_history(group_name, group_dir, old_path, history_path)
            if os.path.exists(old_path):
                os.remove(old_path)
                removed_files += 1
        prune_empty_dirs(group_dir)
        groups_compacted += 1
    return {"removed_files": removed_files, "groups_compacted": groups_compacted}


def collect_group_files(group_dir):
    candidate_files = []
    for root, _, files in os.walk(group_dir):
        for name in files:
            if name == "history.md":
                continue
            candidate_files.append(os.path.join(root, name))
    return candidate_files


def append_agent_output_history(group_name, group_dir, path, history_path):
    if os.path.exists(history_path):
        history_content = read_text_file(history_path).rstrip()
    else:
        history_content = "# {} Output History\n\n> Consolidated by `arms init compress`.\n".format(group_name)
    timestamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    relative_path = os.path.relpath(path, group_dir)
    block_lines = [
        "## Archived Output — {}".format(timestamp),
        "- Source: `{}`".format(relative_path),
        "- Size: {} bytes".format(os.path.getsize(path)),
    ]
    text_content = read_text_if_possible(path)
    if text_content is None:
        block_lines.append("- Content: binary artifact omitted during consolidation.")
    else:
        block_lines.extend(["", "```text", text_content.rstrip(), "```"])
    write_text_atomic(history_path, "{}\n\n{}\n".format(history_content, "\n".join(block_lines)))


def read_text_if_possible(path):
    try:
        with open(path, "r", encoding="utf-8") as handle:
            return handle.read()
    except (UnicodeDecodeError, OSError):
        return None


def prune_empty_dirs(root_dir):
    for current_root, dirnames, _ in os.walk(root_dir, topdown=False):
        for dirname in dirnames:
            path = os.path.join(current_root, dirname)
            if os.path.isdir(path) and not os.listdir(path):
                os.rmdir(path)


def append_archive_entry(project_root, archived_rows, completed_notes, context="Compression pass"):
    archive_path = WorkspacePaths(project_root).archive
    archive_existed = os.path.exists(archive_path)
    if archive_existed:
        archive_content = read_text_file(archive_path).rstrip()
    else:
        archive_content = SESSION_ARCHIVE_TEMPLATE.rstrip()

    timestamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    block_lines = [
        "## Archive — {}".format(timestamp),
        "### Context: {}".format(context),
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
    return {
        "archive_path": archive_path,
        "archive_existed": archive_existed,
        "context": context,
        "history_summary_path": "",
    }


def format_archive_diagnostics_lines(diagnostics):
    if not diagnostics:
        return []

    archive_path = diagnostics["archive_path"]
    archive_state = "existing archive" if diagnostics["archive_existed"] else "initialized archive"
    access_mode = "read+write" if diagnostics["archive_existed"] else "write"
    lines = [
        "Archive diagnostics: {} `{}` ({}, context: {}).".format(
            access_mode,
            archive_path,
            archive_state,
            diagnostics["context"],
        )
    ]
    history_summary_path = diagnostics.get("history_summary_path") or ""
    if history_summary_path:
        lines.append("History summary write: `{}`.".format(history_summary_path))
    return lines


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
