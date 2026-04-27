import importlib.util
import os
import re
import subprocess


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
    return format_git_describe_version(completed.stdout)


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
    except Exception:
        return ""
    return getattr(module, "version", "") or getattr(module, "__version__", "") or ""


def resolve_version(package_dir):
    # 1. Git describe — most accurate for dev checkouts
    git_version = resolve_git_version(package_dir)
    if git_version:
        return git_version

    # 2. Generated _version.py — present in built wheels and editable installs
    generated_version = _read_version_file(package_dir)
    if generated_version:
        return generated_version

    # 3. Installed package metadata
    try:
        from importlib.metadata import PackageNotFoundError, version as package_version
    except ImportError:
        PackageNotFoundError = Exception
        package_version = None

    if package_version is not None:
        try:
            installed_version = package_version("arms-engine")
        except PackageNotFoundError:
            installed_version = ""
        if installed_version:
            return installed_version

    return "0.0.0-dev"


def is_unresolved_version(value):
    normalized = (value or "").strip().lower()
    return normalized in {"0.0.0-dev", "0.0.0-dev0"}
