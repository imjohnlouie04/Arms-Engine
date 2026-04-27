import os

from .versioning import resolve_version


__version__ = resolve_version(os.path.dirname(os.path.abspath(__file__)))
