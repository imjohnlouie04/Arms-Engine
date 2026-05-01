from . import __version__
from .doctor import build_doctor_report
from .versioning import collect_version_diagnostics


def identify_release_validation_command(command_parts):
    normalized = tuple(part.strip().lower() for part in command_parts if part.strip())
    return normalized == ("release", "check")


def handle_release_validation_command(project_root, arms_root):
    report = build_doctor_report(project_root, arms_root)
    emit_release_validation_response(report, arms_root)
    if report["counts"]["fail"] > 0:
        raise SystemExit(1)


def emit_release_validation_response(report, arms_root):
    counts = report["counts"]
    gate = summarize_release_gate(counts)
    category_status = {
        category: summarize_category_status(checks)
        for category, checks in report["categories"].items()
        if checks
    }
    blocking_categories = [
        category for category, status in category_status.items() if status == "fail"
    ]
    warning_categories = [
        category for category, status in category_status.items() if status == "warn"
    ]
    ready_categories = [
        category for category, status in category_status.items() if status == "ok"
    ]
    version_diagnostics = collect_version_diagnostics(arms_root, __version__)

    body_lines = [
        "## Release Validation",
        "",
        "**Project Root:** `{}`".format(report["project_root"]),
        "**Engine Root:** `{}`".format(report["arms_root"]),
        "**Result:** {}".format("FAIL" if counts["fail"] else "PASS"),
        "**Release Gate:** {}".format(gate),
        "**Checks:** {} ok / {} warn / {} fail".format(
            counts["ok"],
            counts["warn"],
            counts["fail"],
        ),
        "",
        "### Shipping Summary",
        "- Blocking categories{}: {}.".format(
            format_count_label(len(blocking_categories)),
            ", ".join(blocking_categories) if blocking_categories else "none",
        ),
        "- Warning categories{}: {}.".format(
            format_count_label(len(warning_categories)),
            ", ".join(warning_categories) if warning_categories else "none",
        ),
        "- Ready categories{}: {}.".format(
            format_count_label(len(ready_categories)),
            ", ".join(ready_categories) if ready_categories else "none",
        ),
        "- Version snapshot: runtime `{}`, git describe `{}`, latest tag `{}`.".format(
            version_diagnostics["runtime_version"] or "unavailable",
            version_diagnostics["git_describe_raw"] or "unavailable",
            version_diagnostics["latest_tag"] or "unavailable",
        ),
        "- Recommended next command: {}.".format(
            recommend_next_command(counts, blocking_categories)
        ),
        "",
    ]

    for category, checks in report["categories"].items():
        if not checks:
            continue
        body_lines.append("### {}".format(category))
        for check in checks:
            body_lines.append("- [{}] {}".format(check["status"].upper(), check["summary"]))
            if check["fix"]:
                body_lines.append("  Fix: {}".format(check["fix"]))
        body_lines.append("")

    next_step = build_next_step(counts)

    print("[Speaking Agent]: arms-main-agent")
    print("[Active Skill]:   arms-orchestrator")
    print()
    print("[State Updates]: None")
    print()
    print("[Action / Code]:")
    print("\n".join(body_lines).rstrip())
    print()
    print("[Next Step / Blocker]: {}".format(next_step))


def summarize_release_gate(counts):
    if counts["fail"]:
        return "BLOCKED"
    if counts["warn"]:
        return "READY WITH WARNINGS"
    return "READY"


def summarize_category_status(checks):
    if any(check["status"] == "fail" for check in checks):
        return "fail"
    if any(check["status"] == "warn" for check in checks):
        return "warn"
    return "ok"


def format_count_label(count):
    return " ({})".format(count) if count else ""


def recommend_next_command(counts, blocking_categories):
    if counts["fail"]:
        if any(category in {"Workspace Health", "Ownership Safety"} for category in blocking_categories):
            return "`arms doctor --fix` for safe mirror repairs or `arms init` if the workspace itself is missing, then `arms release check`"
        return "Resolve the blocking release issues, then rerun `arms release check`"
    if counts["warn"]:
        return "Review the warnings, then use `arms run deploy` when you are comfortable shipping"
    return "`arms run deploy` when you are ready to stage deployment work"


def build_next_step(counts):
    if counts["fail"]:
        return "Release validation found blocking issues. Resolve them and rerun `arms release check`. → HALT"
    if counts["warn"]:
        return "Release validation passed with warnings. Review the warnings, then continue to `arms run deploy` when ready. → HALT"
    return "Release validation passed. Continue to `arms run deploy` when you want to stage deployment work. → HALT"
