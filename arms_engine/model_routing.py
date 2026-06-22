"""Model tier routing: maps agent model tiers to per-platform model identifiers.

The single source of truth for tier -> model mappings lives in
`model_routing.yaml`. `agents.yaml` declares a `model_tier` per agent
(economy/standard/power); this module resolves that tier to the concrete
model directive a given AI CLI platform expects, so specialist agents run on
right-sized models instead of always inheriting the host session's model.
"""

import os

try:
    import yaml
except ImportError as import_error:
    yaml = None
    YAML_IMPORT_ERROR = import_error
else:
    YAML_IMPORT_ERROR = None


MODEL_TIERS = ("economy", "standard", "power")
DEFAULT_MODEL_TIER = "standard"


def normalize_model_tier(value):
    """Return *value* if it is a recognised tier, else the default tier."""
    candidate = str(value or "").strip().lower()
    return candidate if candidate in MODEL_TIERS else DEFAULT_MODEL_TIER


def load_model_routing(arms_root):
    """Parse `model_routing.yaml`, returning {} if the file is missing."""
    yaml_path = os.path.join(arms_root, "model_routing.yaml")
    if not os.path.exists(yaml_path):
        return {}

    if yaml is None:
        raise ImportError(
            "PyYAML is required by arms-engine but could not be imported. "
            "Reinstall dependencies with `pip install -e .` or `pip install pyyaml`."
        ) from YAML_IMPORT_ERROR

    with open(yaml_path, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()

    try:
        parsed = yaml.safe_load(content) or {}
    except yaml.YAMLError as error:
        raise ValueError("Invalid YAML in `{}`: {}".format(yaml_path, error)) from error
    if not isinstance(parsed, dict):
        raise ValueError("Top-level YAML in `{}` must parse to a mapping.".format(yaml_path))
    return parsed


def resolve_agent_model(agent_info, platform, routing):
    """Resolve the model directive for *agent_info* on *platform*.

    Returns a plain model name string for simple platforms (claude, gemini),
    a dict (e.g. ``{"model": ..., "model_reasoning_effort": ...}``) for
    platforms with extra knobs (codex), or `None` if no mapping is configured.
    """
    tier = normalize_model_tier((agent_info or {}).get("model_tier"))
    platform_map = (routing or {}).get("platforms", {}) or {}
    tier_map = platform_map.get(platform, {}) or {}
    return tier_map.get(tier)
