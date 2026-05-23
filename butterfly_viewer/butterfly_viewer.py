"""Compatibility entry point for the migrated application structure."""

try:
    from .app.bootstrap import main
    from .ui.main_window import APPNAME, COMPANY, DOMAIN, VERSION, MultiViewMainWindow, SplitViewMdiChild
except ImportError:
    from app.bootstrap import main
    from ui.main_window import APPNAME, COMPANY, DOMAIN, VERSION, MultiViewMainWindow, SplitViewMdiChild


if __name__ == "__main__":
    main()
