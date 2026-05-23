"""Compatibility wrapper for the migrated SplitView module."""

try:
    from .ui.splitview import *  # noqa: F401,F403
except ImportError:
    from ui.splitview import *  # noqa: F401,F403
