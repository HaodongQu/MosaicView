"""MosaicView package."""

from .app.bootstrap import main
from .ui.main_window import APPNAME, VERSION, MultiViewMainWindow

__all__ = ["APPNAME", "VERSION", "MultiViewMainWindow", "main"]
