import importlib.util
import os
import re
import subprocess


def resolve_git_describe_raw(package_dir):
    repo_root = os.path.dirname(os.path.abspath(package_dir))
    if not os.path.isdir(os.path.join(repo_root, ".git")):
        return ""
    try:
        completed = subprocess.run(
            ["git", "-C", repo_root, "describe", "--tags", "--dirty", "--always"],
            capture_output=True,
            text=True,
            check=True,
        )
    except (FileNotFoundError, subprocess.CalledProcessError):
        return ""
    return completed.stdout.strip()


def resolve_latest_git_tag(package_dir):
    repo_root = os.path.dirname(os.path.abspath(package_dir))
    if not os.path.isdir(os.path.join(repo_root, ".git")):
        return ""
    try:
        completed = subprocess.run(
            ["git", "-C", repo_root, "describe", "--tags", "--abbrev=0"],
            capture_output=True,
            text=True,
            check=True,
        )
    except (FileNotFoundError, subprocess.CalledProcessError):
        return ""
    return completed.stdout.strip()


def format_git_describe_version(raw_version):
    value = raw_version.strip()
    if not value:
        return ""
    if value.startswith("v"):
        value = value[1:]

    dirty = value.endswith("-dirty")
    if dirty:
        value = value[: -len("-dirty")]

    exact_match = re.match(r"^\d+\.\d+\.\d+$", value)
    if exact_match:
        return exact_match.group(0) + ("+dirty" if dirty else "")

    described_match = re.match(r"^(\d+\.\d+\.\d+)-(\d+)-g([0-9a-f]+)$", value)
    if described_match:
        base_version = described_match.group(1)
        distance = described_match.group(2)
        commit = described_match.group(3)
        suffix = f".dev{distance}+g{commit}"
        if dirty:
            suffix += ".dirty"
        return base_version + suffix

    # Untagged repo — commit hash only; treat as dev
    if re.match(r"^[0-9a-f]{7,}(-dirty)?$", value):
        return f"0.0.0.dev0+g{value.replace('-dirty', '')}" + ("+dirty" if dirty else "")

    return raw_version.strip()


def resolve_git_version(package_dir):
    return format_git_describe_version(resolve_git_describe_raw(package_dir))


def _read_version_file(package_dir):
    """Read _version.py without a relative import, so it works in any execution context."""
    version_path = os.path.join(package_dir, "_version.py")
    if not os.path.isfile(version_path):
        return ""
    spec = importlib.util.spec_from_file_location("_version", version_path)
    if spec is None or spec.loader is None:
        return ""
    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
    except (ImportError, SyntaxError, OSError, AttributeError):
        return ""
    return getattr(module, "version", "") or getattr(module, "__version__", "") or ""


def resolve_generated_version(package_dir):
    return _read_version_file(package_dir)


def resolve_installed_package_version():
    try:
        from importlib.metadata import PackageNotFoundError, version as package_version
    except ImportError:
        PackageNotFoundError = Exception
        package_version = None

    if package_version is None:
        return ""
    try:
        return package_version("arms-engine")
    except PackageNotFoundError:
        return ""


def collect_version_diagnostics(package_dir, runtime_version):
    git_describe_raw = resolve_git_describe_raw(package_dir)
    git_describe_version = format_git_describe_version(git_describe_raw)
    latest_tag = resolve_latest_git_tag(package_dir)
    generated_version = resolve_generated_version(package_dir)
    installed_version = resolve_installed_package_version()
    return {
        "runtime_version": runtime_version or "",
        "git_describe_raw": git_describe_raw,
        "git_describe_version": git_describe_version,
        "latest_tag": latest_tag,
        "generated_version": generated_version,
        "installed_version": installed_version,
    }


def resolve_version(package_dir):
    # 1. Git describe — most accurate for dev checkouts
    git_version = resolve_git_version(package_dir)
    if git_version:
        return git_version

    # 2. Generated _version.py — present in built wheels and editable installs
    generated_version = resolve_generated_version(package_dir)
    if generated_version:
        return generated_version

    # 3. Installed package metadata
    installed_version = resolve_installed_package_version()
    if installed_version:
        return installed_version

    return "0.0.0-dev"


def is_unresolved_version(value):
    normalized = (value or "").strip().lower()
    return normalized in {"0.0.0-dev", "0.0.0-dev0"}
