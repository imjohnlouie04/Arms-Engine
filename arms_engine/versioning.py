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


def resolve_version(package_dir):
    git_version = resolve_git_version(package_dir)
    if git_version:
        return git_version

    try:
        from ._version import version as generated_version
    except (ImportError, ValueError):
        generated_version = ""
    if generated_version:
        return generated_version

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
