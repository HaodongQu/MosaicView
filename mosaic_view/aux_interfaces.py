"""Compatibility wrapper for the migrated UI panel module."""

try:
    from .ui.panels import *  # noqa: F401,F403
except ImportError:
    from ui.panels import *  # noqa: F401,F403
