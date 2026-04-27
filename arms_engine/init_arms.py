"""Compatibility shim for the ARMS init entrypoint.

The implementation now lives in focused modules so CLI orchestration, brand
handling, prompt generation, skill sync, and session state can evolve and be
tested independently. Keep this file as the stable import surface and
`arms_engine.init_arms:main` entrypoint.
"""

from . import __version__
from .brand import *  # noqa: F401,F403
from .cli import *  # noqa: F401,F403
from .prompts import *  # noqa: F401,F403
from .session import *  # noqa: F401,F403
from .skills import *  # noqa: F401,F403
from .versioning import *  # noqa: F401,F403
from . import cli as _cli


WATCH_POLL_INTERVAL_SECONDS = _cli.WATCH_POLL_INTERVAL_SECONDS


def wait_for_brand_change(project_root, previous_signature):
    return _cli.wait_for_brand_change(
        project_root,
        previous_signature,
        poll_interval=WATCH_POLL_INTERVAL_SECONDS,
    )
