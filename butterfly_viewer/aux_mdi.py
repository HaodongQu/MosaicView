"""Compatibility wrapper for the migrated MDI module."""

try:
    from .ui.mdi import *  # noqa: F401,F403
except ImportError:
    from ui.mdi import *  # noqa: F401,F403
