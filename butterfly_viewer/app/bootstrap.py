"""Application bootstrap and CLI entry points."""

import argparse
import sys

from PyQt5 import QtCore, QtGui, QtWidgets

try:
    from ..ui.main_window import APPNAME, COMPANY, DOMAIN, VERSION, MultiViewMainWindow
except ImportError:
    from ui.main_window import APPNAME, COMPANY, DOMAIN, VERSION, MultiViewMainWindow


def create_argument_parser():
    """Create the Butterfly Viewer CLI parser."""
    parser = argparse.ArgumentParser(
        prog="Butterfly Viewer",
        description="Side-by-side image viewer with synchronized zoom and sliding overlays. Further info: https://olive-groves.github.io/butterfly_viewer/",
    )
    parser.add_argument("--hide", help="If provided, hides the interface on start.", action="store_true")
    parser.add_argument("--fullscreen", help="If provided, fullscreens the app on start.", action="store_true")
    parser.add_argument("--paths", nargs="*", help="If provided, automatically starts with individual (side by side) image windows supplied by these paths.")
    parser.add_argument("--overlay_path_main_topleft", help="If provided, automatically starts with the main image (top left) supplied by this path.")
    parser.add_argument("--overlay_path_topright", help="If provided, automatically starts with the top right image supplied by this path.")
    parser.add_argument("--overlay_path_bottomleft", help="If provided, automatically starts with the bottom left image supplied by this path.")
    parser.add_argument("--overlay_path_bottomright", help="If provided, automatically starts with the bottom right image supplied by this path.")
    return parser


def create_application(argv=None):
    """Create the QApplication and parsed CLI arguments."""
    parser = create_argument_parser()
    args = parser.parse_args(argv)

    app = QtWidgets.QApplication(sys.argv if argv is None else [sys.argv[0], *argv])
    QtCore.QSettings.setDefaultFormat(QtCore.QSettings.IniFormat)
    app.setOrganizationName(COMPANY)
    app.setOrganizationDomain(DOMAIN)
    app.setApplicationName(APPNAME)
    app.setApplicationVersion(VERSION)
    app.setWindowIcon(QtGui.QIcon(":/icons/icon.png"))
    return app, args


def configure_main_window(main_window, args):
    """Apply CLI-provided startup state to the main window."""
    if args.paths:
        for path in args.paths:
            main_window.loadFile(path)

    dda = main_window._splitview_creator.drag_drop_area
    preloaded_image_count = 0
    if args.overlay_path_main_topleft:
        dda.app_main_topleft.load_image(args.overlay_path_main_topleft)
        preloaded_image_count += 1
    if args.overlay_path_bottomleft:
        dda.app_bottomleft.load_image(args.overlay_path_bottomleft)
        preloaded_image_count += 1
    if args.overlay_path_topright:
        dda.app_topright.load_image(args.overlay_path_topright)
        preloaded_image_count += 1
    if args.overlay_path_bottomright:
        dda.app_bottomright.load_image(args.overlay_path_bottomright)
        preloaded_image_count += 1

    if preloaded_image_count >= 2:
        main_window.on_create_splitview()

    if args.hide:
        main_window.show_interface_off()
    if args.fullscreen:
        main_window.set_fullscreen_on()


def main(argv=None):
    """Run the Butterfly Viewer application."""
    app, args = create_application(argv)
    main_window = MultiViewMainWindow()
    main_window.setWindowTitle(APPNAME)
    configure_main_window(main_window, args)
    main_window.show()
    sys.exit(app.exec_())
