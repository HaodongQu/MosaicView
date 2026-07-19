#!/usr/bin/env python3

"""Multi-image viewer for comparing images with synchronized zooming, panning, and sliding overlays.

Intended to be run as a script:
    $ python mosaic_view.py

Features:
    Image windows have synchronized zoom and pan by default, but can be optionally unsynced.
    Image windows will auto-arrange and can be set as a grid, column, or row. 
    Users can create sliding overlays with up to 4 images.

Credits:
    PyQt MDI Image Viewer by tpgit (http://tpgit.github.io/MDIImageViewer/) for sync pan and zoom.
"""
# SPDX-License-Identifier: GPL-3.0-or-later



try:
    import sip
except ModuleNotFoundError:
    from PyQt5 import sip
import time
import os
from datetime import datetime

from PyQt5 import QtCore, QtGui, QtWidgets

try:
    from .splitview import SplitView
    from .panels import SplitViewCreator, FileBrowserPanel
    from .mdi import QMdiAreaWithCustomSignals
    from ..aux_functions import strippedName, toBool, determineSyncSenderDimension, determineSyncAdjustmentFactor
    from ..aux_buttons import ViewerButton
    from ..services.image_loader import load_view_pixmaps
    from .. import icons_rc
except ImportError:
    from ui.splitview import SplitView
    from ui.panels import SplitViewCreator, FileBrowserPanel
    from ui.mdi import QMdiAreaWithCustomSignals
    from aux_functions import strippedName, toBool, determineSyncSenderDimension, determineSyncAdjustmentFactor
    from aux_buttons import ViewerButton
    from services.image_loader import load_view_pixmaps
    import icons_rc



os.environ["QT_ENABLE_HIGHDPI_SCALING"]   = "1"
os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"
os.environ["QT_SCALE_FACTOR"]             = "1"

if hasattr(sip, "setapi"):
    sip.setapi('QDate', 2)
    sip.setapi('QTime', 2)
    sip.setapi('QDateTime', 2)
    sip.setapi('QUrl', 2)
    sip.setapi('QTextStream', 2)
    sip.setapi('QVariant', 2)
    sip.setapi('QString', 2)

COMPANY = "MosaicView"
DOMAIN = "https://github.com/halley/MosaicView/"
APPNAME = "MosaicView"
VERSION = "1.1"

SETTING_RECENTFILELIST = "recentfilelist"
SETTING_FILEOPEN = "fileOpenDialog"
SETTING_SCROLLBARS = "scrollbars"
SETTING_STATUSBAR = "statusbar"
SETTING_SYNCHZOOM = "synchzoom"
SETTING_SYNCHPAN = "synchpan"



class SplitViewMdiChild(SplitView):
    """Extends SplitView for use in MosaicView.

    Args:
        See parent method for full documentation.
    """

    def __init__(self, pixmap, filename_main_topleft, name, pixmap_topright, pixmap_bottomleft, pixmap_bottomright, transform_mode_smooth):
        super().__init__(pixmap, filename_main_topleft, name, pixmap_topright, pixmap_bottomleft, pixmap_bottomright, transform_mode_smooth)

        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)
        self._isUntitled = True

        self._sync_this_zoom = True
        self._sync_this_pan = True
    
    @property
    def sync_this_zoom(self):
        """bool: Setting of whether to sync this by zoom (or not)."""
        return self._sync_this_zoom
    
    @sync_this_zoom.setter
    def sync_this_zoom(self, bool: bool):
        """bool: Set whether to sync this by zoom (or not)."""
        self._sync_this_zoom = bool

    @property
    def sync_this_pan(self):
        """bool: Setting of whether to sync this by pan (or not)."""
        return self._sync_this_pan
    
    @sync_this_pan.setter
    def sync_this_pan(self, bool: bool):
        """bool: Set whether to sync this by pan (or not)."""
        self._sync_this_pan = bool

class MultiViewMainWindow(QtWidgets.QMainWindow):
    """View multiple images with split-effect and synchronized panning and zooming.

    Extends QMainWindow as main window of MosaicView with user interface:

    - Create sliding overlays.
    - Change viewer settings.
    """
    
    MaxRecentFiles = 10

    def __init__(self):
        super(MultiViewMainWindow, self).__init__()

        self._recentFileActions = []
        self._handlingScrollChangedSignal = False
        self._last_accessed_fullpath = None

        self._mdiArea = QMdiAreaWithCustomSignals()
        self._mdiArea.file_path_dragged.connect(self.display_dragged_grayout)
        self._mdiArea.file_path_dragged_and_dropped.connect(self.load_from_dragged_and_dropped_file)
        self._mdiArea.first_subwindow_was_opened.connect(self.on_first_subwindow_was_opened)
        self._mdiArea.last_remaining_subwindow_was_closed.connect(self.on_last_remaining_subwindow_was_closed)
        self._reorder_drag_source_window = None
        self._reorder_drag_start_global_pos = None
        self._reorder_drag_active = False

        self.escape_shortcut = QtWidgets.QShortcut(QtGui.QKeySequence("Escape"), self)
        self.escape_shortcut.activated.connect(self.set_fullscreen_off)

        self.f_shortcut = QtWidgets.QShortcut(QtGui.QKeySequence("f"), self)
        self.f_shortcut.activated.connect(self.toggle_fullscreen)

        self.h_shortcut = QtWidgets.QShortcut(QtGui.QKeySequence("h"), self)
        self.h_shortcut.setContext(QtCore.Qt.ApplicationShortcut)
        self.h_shortcut.activated.connect(self.toggle_interface)

        self.ctrl_c_shortcut = QtWidgets.QShortcut(QtGui.QKeySequence("Ctrl+c"), self)
        self.ctrl_c_shortcut.activated.connect(self.copy_view)

        self.ctrl_s_shortcut = QtWidgets.QShortcut(QtGui.QKeySequence("Ctrl+s"), self)
        self.ctrl_s_shortcut.setContext(QtCore.Qt.ApplicationShortcut)
        self.ctrl_s_shortcut.activated.connect(self.save_view)

        app = QtWidgets.QApplication.instance()
        if app is not None:
            app.installEventFilter(self)

        self._mdiArea.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAsNeeded)
        self._mdiArea.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAsNeeded)
        self._mdiArea.subWindowActivated.connect(self.subWindowActivated)

        self._mdiArea.setBackground(QtGui.QColor(32,32,32))

        self._label_mouse = QtWidgets.QLabel() # Pixel coordinates of mouse in a view
        self._label_mouse.setText("View pixel coordinates: ( N/A , N/A )")
        self._label_mouse.setWordWrap(True)
        self._label_mouse.adjustSize()
        self._label_mouse.setVisible(False)
        self._label_mouse.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
        self._label_mouse.setStyleSheet("QLabel { color: palette(text); background-color: rgba(255, 255, 255, 0.06); border: 1px solid palette(mid); padding: 0.5em 0.7em; font-size: 8pt; border-radius: 0.45em; }")

        self._splitview_creator = SplitViewCreator()
        self._splitview_creator.clicked_create_splitview_pushbutton.connect(self.on_create_splitview)
        layout_mdiarea_topleft = QtWidgets.QVBoxLayout()
        layout_mdiarea_topleft.setContentsMargins(0, 0, 0, 0)
        layout_mdiarea_topleft.setSpacing(8)
        layout_mdiarea_topleft.addWidget(self._splitview_creator)
        self.interface_mdiarea_topleft = QtWidgets.QWidget()
        self.interface_mdiarea_topleft.setLayout(layout_mdiarea_topleft)

        self._mdiArea.subWindowActivated.connect(self.update_window_highlight)
        self._mdiArea.subWindowActivated.connect(self.update_window_labels)
        self._mdiArea.subWindowActivated.connect(self.updateMenus)
        self._mdiArea.subWindowActivated.connect(self.auto_tile_subwindows_on_close)
        self._mdiArea.subWindowActivated.connect(self.update_zoom_panel)
        
        
        self.centralwidget_during_fullscreen_pushbutton = QtWidgets.QToolButton() # Needed for users to return the image viewer to the main window if the window of the viewer is lost during fullscreen
        self.centralwidget_during_fullscreen_pushbutton.setText("Close Fullscreen") # Needed for users to return the image viewer to the main window if the window of the viewer is lost during fullscreen
        self.centralwidget_during_fullscreen_pushbutton.clicked.connect(self.set_fullscreen_off)
        self.centralwidget_during_fullscreen_pushbutton.setStyleSheet("font-size: 11pt")
        self.centralwidget_during_fullscreen_layout = QtWidgets.QVBoxLayout()
        self.centralwidget_during_fullscreen_layout.setAlignment(QtCore.Qt.AlignCenter)
        self.centralwidget_during_fullscreen_layout.addWidget(self.centralwidget_during_fullscreen_pushbutton, alignment=QtCore.Qt.AlignCenter)
        self.centralwidget_during_fullscreen = QtWidgets.QWidget()
        self.centralwidget_during_fullscreen.setLayout(self.centralwidget_during_fullscreen_layout)

        self.fullscreen_pushbutton = ViewerButton()
        self.fullscreen_pushbutton.setIcon(":/icons/full-screen.svg")
        self.fullscreen_pushbutton.setCheckedIcon(":/icons/full-screen-exit.svg")
        self.fullscreen_pushbutton.setToolTip("Fullscreen on/off (F)")
        self.fullscreen_pushbutton.setSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
        self.fullscreen_pushbutton.setMouseTracking(True)
        self.fullscreen_pushbutton.setCheckable(True)
        self.fullscreen_pushbutton.toggled.connect(self.set_fullscreen)
        self.is_fullscreen = False

        self.interface_toggle_pushbutton = ViewerButton()
        self.interface_toggle_pushbutton.setCheckedIcon(":/icons/eye.svg")
        self.interface_toggle_pushbutton.setIcon(":/icons/eye-cancelled.svg")
        self.interface_toggle_pushbutton.setToolTip("Hide interface (H)")
        self.interface_toggle_pushbutton.setSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
        self.interface_toggle_pushbutton.setMouseTracking(True)
        self.interface_toggle_pushbutton.setCheckable(True)
        self.interface_toggle_pushbutton.setChecked(True)
        self.interface_toggle_pushbutton.clicked.connect(self.show_interface)

        self.is_interface_showing = True
        self.is_quiet_mode = False
        self.is_global_transform_mode_smooth = False
        self.scene_background_color = None
        self.sync_zoom_by = "box"

        self.close_all_pushbutton = ViewerButton(style="trigger-severe")
        self.close_all_pushbutton.setIcon(":/icons/clear.svg")
        self.close_all_pushbutton.setToolTip("Close all image windows")
        self.close_all_pushbutton.setSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
        self.close_all_pushbutton.setMouseTracking(True)
        self.close_all_pushbutton.clicked.connect(self._mdiArea.closeAllSubWindows)

        self.tile_default_pushbutton = ViewerButton(style="trigger")
        self.tile_default_pushbutton.setIcon(":/icons/capacity.svg")
        self.tile_default_pushbutton.setToolTip("Grid arrange windows")
        self.tile_default_pushbutton.setSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
        self.tile_default_pushbutton.setMouseTracking(True)
        self.tile_default_pushbutton.clicked.connect(self._mdiArea.tileSubWindows)
        self.tile_default_pushbutton.clicked.connect(self.fit_to_window)
        self.tile_default_pushbutton.clicked.connect(self.refreshPan)

        self.tile_horizontally_pushbutton = ViewerButton(style="trigger")
        self.tile_horizontally_pushbutton.setIcon(":/icons/split-vertically.svg")
        self.tile_horizontally_pushbutton.setToolTip("Horizontally arrange windows in a single row")
        self.tile_horizontally_pushbutton.setSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
        self.tile_horizontally_pushbutton.setMouseTracking(True)
        self.tile_horizontally_pushbutton.clicked.connect(self._mdiArea.tile_subwindows_horizontally)
        self.tile_horizontally_pushbutton.clicked.connect(self.fit_to_window)
        self.tile_horizontally_pushbutton.clicked.connect(self.refreshPan)

        self.tile_vertically_pushbutton = ViewerButton(style="trigger")
        self.tile_vertically_pushbutton.setIcon(":/icons/split-horizontally.svg")
        self.tile_vertically_pushbutton.setToolTip("Vertically arrange windows in a single column")
        self.tile_vertically_pushbutton.setSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
        self.tile_vertically_pushbutton.setMouseTracking(True)
        self.tile_vertically_pushbutton.clicked.connect(self._mdiArea.tile_subwindows_vertically)
        self.tile_vertically_pushbutton.clicked.connect(self.fit_to_window)
        self.tile_vertically_pushbutton.clicked.connect(self.refreshPan)

        self.fit_to_window_pushbutton = ViewerButton(style="trigger")
        self.fit_to_window_pushbutton.setIcon(":/icons/pan.svg")
        self.fit_to_window_pushbutton.setToolTip("Fit and center image in active window (affects all if synced)")
        self.fit_to_window_pushbutton.setSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
        self.fit_to_window_pushbutton.setMouseTracking(True)
        self.fit_to_window_pushbutton.clicked.connect(self.fit_to_window)

        self.info_pushbutton = ViewerButton(style="trigger-transparent")
        self.info_pushbutton.setIcon(":/icons/about.svg")
        self.info_pushbutton.setToolTip("About...")
        self.info_pushbutton.setSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
        self.info_pushbutton.setMouseTracking(True)
        self.info_pushbutton.clicked.connect(self.info_button_clicked)

        self.stopsync_toggle_pushbutton = ViewerButton(style="green-yellow")
        self.stopsync_toggle_pushbutton.setIcon(":/icons/refresh.svg")
        self.stopsync_toggle_pushbutton.setCheckedIcon(":/icons/refresh-cancelled.svg")
        self.stopsync_toggle_pushbutton.setToolTip("Unsynchronize zoom and pan (currently synced)")
        self.stopsync_toggle_pushbutton.setSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
        self.stopsync_toggle_pushbutton.setMouseTracking(True)
        self.stopsync_toggle_pushbutton.setCheckable(True)
        self.stopsync_toggle_pushbutton.toggled.connect(self.set_stopsync_pushbutton)

        self.save_view_pushbutton = ViewerButton()
        self.save_view_pushbutton.setIcon(":/icons/download.svg")
        self.save_view_pushbutton.setToolTip("Save a screenshot of the viewer... (Ctrl·S) | Copy screenshot to clipboard (Ctrl·C)")
        self.save_view_pushbutton.setSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
        self.save_view_pushbutton.setMouseTracking(True)
        self.save_view_pushbutton.clicked.connect(self.save_view)

        self.open_new_pushbutton = ViewerButton()
        self.open_new_pushbutton.setIcon(":/icons/open-file.svg")
        self.open_new_pushbutton.setToolTip("Open image(s) as single windows...")
        self.open_new_pushbutton.setSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
        self.open_new_pushbutton.setMouseTracking(True)
        self.open_new_pushbutton.clicked.connect(self.open_multiple)

        self.label_mdiarea = QtWidgets.QLabel()
        self.label_mdiarea.setText("Drag images directly to create individual image windows\n\n—\n\nCreate sliding overlays to compare images directly over each other\n\n—\n\nRight-click image windows to change settings and add tools")
        self.label_mdiarea.setStyleSheet("""
            QLabel { 
                color: white;
                border: 0.13em dashed gray;
                border-radius: 0.25em;
                background-color: transparent;
                padding: 1em;
                font-size: 10pt;
                } 
            """)
        self.label_mdiarea.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents)
        self.label_mdiarea.setAlignment(QtCore.Qt.AlignCenter)

        layout_mdiarea_bottomright_vertical = QtWidgets.QGridLayout()
        layout_mdiarea_bottomright_vertical.setContentsMargins(0, 0, 0, 0)
        layout_mdiarea_bottomright_vertical.setHorizontalSpacing(8)
        layout_mdiarea_bottomright_vertical.setVerticalSpacing(8)
        layout_mdiarea_bottomright_vertical.setAlignment(QtCore.Qt.AlignLeft)
        layout_mdiarea_bottomright_vertical.addWidget(self.fit_to_window_pushbutton, 0, 0)
        layout_mdiarea_bottomright_vertical.addWidget(self.tile_default_pushbutton, 0, 1)
        layout_mdiarea_bottomright_vertical.addWidget(self.tile_horizontally_pushbutton, 0, 2)
        layout_mdiarea_bottomright_vertical.addWidget(self.tile_vertically_pushbutton, 0, 3)
        layout_mdiarea_bottomright_vertical.addWidget(self.fullscreen_pushbutton, 0, 4)
        layout_mdiarea_bottomright_vertical.addWidget(self.info_pushbutton, 0, 5)
        self.interface_mdiarea_bottomright_vertical = QtWidgets.QWidget()
        self.interface_mdiarea_bottomright_vertical.setLayout(layout_mdiarea_bottomright_vertical)

        layout_mdiarea_bottomright_horizontal = QtWidgets.QGridLayout()
        layout_mdiarea_bottomright_horizontal.setContentsMargins(0, 0, 0, 0)
        layout_mdiarea_bottomright_horizontal.setHorizontalSpacing(8)
        layout_mdiarea_bottomright_horizontal.setVerticalSpacing(8)
        layout_mdiarea_bottomright_horizontal.setAlignment(QtCore.Qt.AlignLeft)
        layout_mdiarea_bottomright_horizontal.addWidget(self.open_new_pushbutton, 0, 0)
        layout_mdiarea_bottomright_horizontal.addWidget(self.save_view_pushbutton, 0, 1)
        layout_mdiarea_bottomright_horizontal.addWidget(self.stopsync_toggle_pushbutton, 0, 2)
        layout_mdiarea_bottomright_horizontal.addWidget(self.close_all_pushbutton, 0, 3)
        layout_mdiarea_bottomright_horizontal.addWidget(self.interface_toggle_pushbutton, 0, 4)
        self.interface_mdiarea_bottomright_horizontal = QtWidgets.QWidget()
        self.interface_mdiarea_bottomright_horizontal.setLayout(layout_mdiarea_bottomright_horizontal)


        self.loading_grayout_label = QtWidgets.QLabel("Loading...") # Needed to give users feedback when loading views
        self.loading_grayout_label.setWordWrap(True)
        self.loading_grayout_label.setAlignment(QtCore.Qt.AlignCenter | QtCore.Qt.AlignVCenter)
        self.loading_grayout_label.setVisible(False)
        self.loading_grayout_label.setStyleSheet("""
            QLabel { 
                color: white;
                background-color: rgba(0,0,0,223);
                font-size: 10pt;
                } 
            """)

        self.dragged_grayout_label = QtWidgets.QLabel("Drop to create single view(s)...") # Needed to give users feedback when dragging in images
        self.dragged_grayout_label.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents)
        self.dragged_grayout_label.setWordWrap(True)
        self.dragged_grayout_label.setAlignment(QtCore.Qt.AlignCenter | QtCore.Qt.AlignVCenter)
        self.dragged_grayout_label.setVisible(False)
        self.dragged_grayout_label.setStyleSheet("""
            QLabel { 
                color: white;
                background-color: rgba(63,63,63,223);
                border: 0.13em dashed gray;
                border-radius: 0.25em;
                margin-left: 0.25em;
                margin-top: 0.25em;
                margin-right: 0.25em;
                margin-bottom: 0.25em;
                font-size: 10pt;
                } 
            """)    


        layout_mdiarea = QtWidgets.QGridLayout()
        layout_mdiarea.setContentsMargins(0, 0, 0, 0)
        layout_mdiarea.setSpacing(0)
        layout_mdiarea.addWidget(self._mdiArea, 0, 0)
        layout_mdiarea.addWidget(self.label_mdiarea, 0, 0, QtCore.Qt.AlignCenter)
        layout_mdiarea.addWidget(self.dragged_grayout_label, 0, 0)
        layout_mdiarea.addWidget(self.loading_grayout_label, 0, 0)
        self.image_workspace = QtWidgets.QWidget()
        self.image_workspace.setLayout(layout_mdiarea)

        sidebar_header = QtWidgets.QFrame()
        sidebar_header.setStyleSheet("QFrame { background: palette(base); border: 1px solid palette(mid); border-radius: 0.8em; }")
        sidebar_header_layout = QtWidgets.QVBoxLayout()
        sidebar_header_layout.setContentsMargins(14, 14, 14, 14)
        sidebar_header_layout.setSpacing(10)
        sidebar_title = QtWidgets.QLabel("MosaicView")
        sidebar_title.setStyleSheet("QLabel { font-size: 14pt; font-weight: bold; }")
        sidebar_header_layout.addWidget(sidebar_title)
        sidebar_header.setLayout(sidebar_header_layout)

        sidebar_section_tools = QtWidgets.QFrame()
        sidebar_section_tools.setStyleSheet("QFrame { background: palette(base); border: 1px solid palette(mid); border-radius: 0.7em; }")
        sidebar_section_tools_layout = QtWidgets.QVBoxLayout()
        sidebar_section_tools_layout.setContentsMargins(14, 14, 14, 14)
        sidebar_section_tools_layout.setSpacing(10)
        sidebar_section_tools_title = QtWidgets.QLabel("Viewer Controls")
        sidebar_section_tools_title.setStyleSheet("QLabel { font-size: 11pt; font-weight: bold; }")
        sidebar_session_label = QtWidgets.QLabel("Session")
        sidebar_session_label.setStyleSheet("QLabel { color: palette(mid); font-size: 8pt; font-weight: bold; }")
        sidebar_canvas_label = QtWidgets.QLabel("Canvas")
        sidebar_canvas_label.setStyleSheet("QLabel { color: palette(mid); font-size: 8pt; font-weight: bold; }")
        sidebar_section_tools_layout.addWidget(sidebar_section_tools_title)
        sidebar_section_tools_layout.addWidget(sidebar_session_label)
        sidebar_section_tools_layout.addWidget(self.interface_mdiarea_bottomright_horizontal)
        sidebar_section_tools_layout.addWidget(sidebar_canvas_label)
        sidebar_section_tools_layout.addWidget(self.interface_mdiarea_bottomright_vertical)
        sidebar_section_tools.setLayout(sidebar_section_tools_layout)

        self.zoom_panel = QtWidgets.QFrame()
        self.zoom_panel.setStyleSheet("QFrame { background: palette(base); border: 1px solid palette(mid); border-radius: 0.7em; }")
        zoom_panel_layout = QtWidgets.QVBoxLayout()
        zoom_panel_layout.setContentsMargins(14, 14, 14, 14)
        zoom_panel_layout.setSpacing(10)
        zoom_panel_title = QtWidgets.QLabel("Zoom")
        zoom_panel_title.setStyleSheet("QLabel { font-size: 11pt; font-weight: bold; }")
        self.zoom_value_label = QtWidgets.QLabel("N/A")
        self.zoom_value_label.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
        self.zoom_value_label.setStyleSheet("QLabel { font-size: 16pt; font-weight: bold; }")
        self.actual_size_pushbutton = QtWidgets.QPushButton("1:1")
        self.actual_size_pushbutton.setToolTip("Set active view zoom to 100%")
        self.actual_size_pushbutton.setSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
        self.actual_size_pushbutton.setEnabled(False)
        self.actual_size_pushbutton.clicked.connect(self.set_active_view_actual_size)
        zoom_panel_layout.addWidget(zoom_panel_title)
        zoom_panel_layout.addWidget(self.zoom_value_label)
        zoom_panel_layout.addWidget(self.actual_size_pushbutton, 0, QtCore.Qt.AlignLeft)
        self.zoom_panel.setLayout(zoom_panel_layout)

        self.sidebar_content = QtWidgets.QWidget()
        self.sidebar_content.setMinimumWidth(0)
        self.sidebar_content.setSizePolicy(QtWidgets.QSizePolicy.Ignored, QtWidgets.QSizePolicy.Preferred)
        sidebar_layout = QtWidgets.QVBoxLayout()
        sidebar_layout.setContentsMargins(16, 16, 20, 16)
        sidebar_layout.setSpacing(16)
        sidebar_layout.addWidget(sidebar_header)
        sidebar_layout.addWidget(sidebar_section_tools)
        sidebar_layout.addWidget(self.zoom_panel)
        sidebar_layout.addStretch(1)
        self.sidebar_content.setLayout(sidebar_layout)

        self.sidebar_scroll = QtWidgets.QScrollArea()
        self.sidebar_scroll.setWidgetResizable(True)
        self.sidebar_scroll.setFrameShape(QtWidgets.QFrame.NoFrame)
        self.sidebar_scroll.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.sidebar_scroll.setViewportMargins(0, 0, 2, 0)
        self.sidebar_scroll.setWidget(self.sidebar_content)

        self.sidebar_panel = QtWidgets.QFrame()
        self.sidebar_panel.setObjectName("sidebarPanel")
        self.sidebar_panel.setMinimumWidth(260)
        self.sidebar_panel.setStyleSheet("QFrame#sidebarPanel { background: palette(window); border-right: 1px solid palette(mid); }")
        sidebar_panel_layout = QtWidgets.QVBoxLayout()
        sidebar_panel_layout.setContentsMargins(0, 0, 0, 0)
        sidebar_panel_layout.addWidget(self.sidebar_scroll)
        self.sidebar_panel.setLayout(sidebar_panel_layout)

        self.file_browser_panel = FileBrowserPanel()
        self.file_browser_panel.file_activated.connect(self.open_file_from_browser)

        self.browser_sidebar_panel = QtWidgets.QFrame()
        self.browser_sidebar_panel.setObjectName("browserSidebarPanel")
        self.browser_sidebar_panel.setMinimumWidth(360)
        self.browser_sidebar_panel.setStyleSheet("QFrame#browserSidebarPanel { background: palette(window); border-left: 1px solid palette(mid); }")
        browser_sidebar_layout = QtWidgets.QVBoxLayout()
        browser_sidebar_layout.setContentsMargins(16, 16, 16, 16)
        browser_sidebar_layout.setSpacing(16)
        browser_sidebar_layout.addWidget(self.interface_mdiarea_topleft)
        browser_sidebar_layout.addWidget(self.file_browser_panel, 1)
        self.browser_sidebar_panel.setLayout(browser_sidebar_layout)

        self.workspace_splitter = QtWidgets.QSplitter(QtCore.Qt.Horizontal)
        self.workspace_splitter.setChildrenCollapsible(False)
        self.workspace_splitter.setHandleWidth(5)
        self.workspace_splitter.setStyleSheet("""
            QSplitter::handle {
                background: palette(mid);
            }
            QSplitter::handle:hover {
                background: palette(highlight);
            }
        """)
        self.workspace_splitter.addWidget(self.sidebar_panel)
        self.workspace_splitter.addWidget(self.image_workspace)
        self.workspace_splitter.addWidget(self.browser_sidebar_panel)
        self.workspace_splitter.setStretchFactor(0, 0)
        self.workspace_splitter.setStretchFactor(1, 1)
        self.workspace_splitter.setStretchFactor(2, 0)
        self.workspace_splitter.setSizes([260, 800, 390])

        workspace_layout = QtWidgets.QHBoxLayout()
        workspace_layout.setContentsMargins(0, 0, 0, 0)
        workspace_layout.setSpacing(0)
        workspace_layout.addWidget(self.workspace_splitter)

        self.mdiarea_plus_buttons = QtWidgets.QWidget()
        self.mdiarea_plus_buttons.setLayout(workspace_layout)

        self.setCentralWidget(self.mdiarea_plus_buttons)

        self.subwindow_was_just_closed = False

        self._windowMapper = QtCore.QSignalMapper(self)

        self._actionMapper = QtCore.QSignalMapper(self)
        self._actionMapper.mapped[str].connect(self.mappedImageViewerAction)
        self._recentFileMapper = QtCore.QSignalMapper(self)
        self._recentFileMapper.mapped[str].connect(self.openRecentFile)

        self.createActions()
        self.addAction(self._activateSubWindowSystemMenuAct)

        self.createMenus()
        self.updateMenus()
        self.createStatusBar()

        self.readSettings()
        self.updateStatusBar()

        self.setUnifiedTitleAndToolBarOnMac(True)
        
        self.showNormal()
        self.menuBar().hide()

        self.setStyleSheet("QWidget{font-size: 9pt}")


    # Screenshot window

    def copy_view(self):
        """Screenshot MultiViewMainWindow and copy to clipboard as image."""
        
        self.display_loading_grayout(True, "Screenshot copied to clipboard.")

        interface_was_already_set_hidden = not self.is_interface_showing # Needed to hide the interface temporarily while grabbing a screenshot (makes sure the screenshot only shows the views)
        if not interface_was_already_set_hidden:
            self.show_interface_off()

        pixmap = self._mdiArea.grab()
        clipboard = QtWidgets.QApplication.clipboard()
        clipboard.setPixmap(pixmap)

        if not interface_was_already_set_hidden:
            self.show_interface_on()

        self.display_loading_grayout(False, pseudo_load_time=1)


    def save_view(self):
        """Screenshot MultiViewMainWindow and open Save dialog to save screenshot as image.""" 

        self.display_loading_grayout(True, "Saving viewer screenshot...")

        folderpath = None

        if self.activeMdiChild:
            folderpath = self.activeMdiChild.currentFile
            folderpath = os.path.dirname(folderpath)
            folderpath = folderpath + "\\"
        else:
            self.display_loading_grayout(False, pseudo_load_time=0)
            return

        interface_was_already_set_hidden = not self.is_interface_showing # Needed to hide the interface temporarily while grabbing a screenshot (makes sure the screenshot only shows the views)
        if not interface_was_already_set_hidden:
            self.show_interface_off()

        pixmap = self._mdiArea.grab()

        date_and_time = datetime.now().strftime('%Y-%m-%d %H%M%S') # Sets the default filename with date and time 
        filename = "Viewer screenshot " + date_and_time + ".png"
        name_filters = "PNG (*.png);; JPEG (*.jpeg);; TIFF (*.tiff);; JPG (*.jpg);; TIF (*.tif)" # Allows users to select filetype of screenshot

        self.display_loading_grayout(True, "Selecting folder and name for the viewer screenshot...", pseudo_load_time=0)
        
        filepath, _ = QtWidgets.QFileDialog.getSaveFileName(self, "Save a screenshot of the viewer", folderpath+filename, name_filters)
        _, fileextension = os.path.splitext(filepath)
        fileextension = fileextension.replace('.','')
        if filepath:
            pixmap.save(filepath, fileextension)
        
        if not interface_was_already_set_hidden:
            self.show_interface_on()

        self.display_loading_grayout(False)

    
    # Interface and appearance

    def display_loading_grayout(self, boolean, text="Loading...", pseudo_load_time=0.2):
        """Show/hide grayout screen for loading sequences.

        Args:
            boolean (bool): True to show grayout; False to hide.
            text (str): The text to show on the grayout.
            pseudo_load_time (float): The delay (in seconds) to hide the grayout to give users a feeling of action.
        """ 
        if not boolean:
            text = "Loading..."
        self.loading_grayout_label.setText(text)
        self.loading_grayout_label.setVisible(boolean)
        if boolean:
            self.loading_grayout_label.repaint()
        if not boolean:
            time.sleep(pseudo_load_time)

    def display_dragged_grayout(self, boolean):
        """Show/hide grayout screen for drag-and-drop sequences.

        Args:
            boolean (bool): True to show grayout; False to hide.
        """ 
        self.dragged_grayout_label.setVisible(boolean)
        if boolean:
            self.dragged_grayout_label.repaint()

    def on_last_remaining_subwindow_was_closed(self):
        """Show instructions label of MDIArea."""
        self.label_mdiarea.setVisible(True)
        self.update_zoom_panel()

    def on_first_subwindow_was_opened(self):
        """Hide instructions label of MDIArea."""
        self.label_mdiarea.setVisible(False)

    def update_zoom_panel(self, window=None):
        """Refresh the sidebar zoom value for the active view."""
        image_viewer = self.activeMdiChild
        if image_viewer is None:
            self.zoom_value_label.setText("N/A")
            self.actual_size_pushbutton.setEnabled(False)
            return

        self.zoom_value_label.setText("%0.f%%" % (image_viewer.zoomFactor * 100,))
        self.actual_size_pushbutton.setEnabled(True)

    def set_active_view_actual_size(self):
        """Set the active view zoom to one image pixel per screen pixel."""
        if not self.activeMdiChild:
            return

        self.activeMdiChild.actualSize()
        self.updateStatusBar()
        self.update_zoom_panel()

    def show_interface(self, boolean):
        """Show or hide the application sidebars.

        Args:
            boolean (bool): True to show interface; False to hide.
        """ 
        if boolean:
            self.show_interface_on()
        elif not boolean:
            self.show_interface_off()

    def show_interface_on(self):
        """Show the application sidebars.""" 
        if self.is_interface_showing:
            return
        
        self.is_interface_showing = True
        self.is_quiet_mode = False

        self.update_window_highlight(self._mdiArea.activeSubWindow())
        self.update_window_labels(self._mdiArea.activeSubWindow())
        self.set_window_close_pushbuttons_always_visible(self._mdiArea.activeSubWindow(), True)
        self.set_window_mouse_rect_visible(self._mdiArea.activeSubWindow(), True)
        self.sidebar_panel.setVisible(True)
        self.browser_sidebar_panel.setVisible(True)

        self.interface_toggle_pushbutton.setToolTip("Hide interface (studio mode)")

        if self.interface_toggle_pushbutton:
            self.interface_toggle_pushbutton.setChecked(True)

    def show_interface_off(self):
        """Hide the application sidebars.""" 
        if not self.is_interface_showing:
            return

        self.is_interface_showing = False
        self.is_quiet_mode = True

        self.update_window_highlight(self._mdiArea.activeSubWindow())
        self.update_window_labels(self._mdiArea.activeSubWindow())
        self.set_window_close_pushbuttons_always_visible(self._mdiArea.activeSubWindow(), False)
        self.set_window_mouse_rect_visible(self._mdiArea.activeSubWindow(), False)
        self.sidebar_panel.setVisible(False)
        self.browser_sidebar_panel.setVisible(False)

        self.interface_toggle_pushbutton.setToolTip("Show interface (H)")

        if self.interface_toggle_pushbutton:
            self.interface_toggle_pushbutton.setChecked(False)
            self.interface_toggle_pushbutton.setAttribute(QtCore.Qt.WA_UnderMouse, False)

    def toggle_interface(self):
        """Toggle the visibility of the application sidebars.""" 
        if self.is_interface_showing: # If interface is showing, then toggle it off; if not, then toggle it on
            self.show_interface_off()
        else:
            self.show_interface_on()

    def eventFilter(self, source, event):
        """Handle app-wide shortcuts that must work while image views own focus."""
        if self._handle_subwindow_reorder_drag(event):
            return True

        if event.type() == QtCore.QEvent.KeyPress and event.key() == QtCore.Qt.Key_H:
            if event.modifiers() in (QtCore.Qt.NoModifier, QtCore.Qt.ShiftModifier):
                focus_widget = QtWidgets.QApplication.focusWidget()
                text_input_types = (
                    QtWidgets.QLineEdit,
                    QtWidgets.QTextEdit,
                    QtWidgets.QPlainTextEdit,
                    QtWidgets.QSpinBox,
                    QtWidgets.QDoubleSpinBox,
                    QtWidgets.QComboBox,
                )
                if not isinstance(focus_widget, text_input_types):
                    self.toggle_interface()
                    event.accept()
                    return True

        return super().eventFilter(source, event)

    def _handle_subwindow_reorder_drag(self, event):
        """Swap tiled view order with Shift+drag between subwindows."""
        event_type = event.type()
        if event_type == QtCore.QEvent.MouseButtonPress:
            if event.button() != QtCore.Qt.LeftButton:
                return False
            if not event.modifiers() & QtCore.Qt.ShiftModifier:
                return False

            source_window = self._mdi_subwindow_at_global_pos(event.globalPos())
            if source_window is None:
                return False

            self._reorder_drag_source_window = source_window
            self._reorder_drag_start_global_pos = event.globalPos()
            self._reorder_drag_active = False
            self._mdiArea.setActiveSubWindow(source_window)
            self._mdiArea.viewport().setCursor(QtCore.Qt.ClosedHandCursor)
            event.accept()
            return True

        if self._reorder_drag_source_window is None:
            return False

        if event_type == QtCore.QEvent.MouseMove:
            if not event.buttons() & QtCore.Qt.LeftButton:
                self._clear_subwindow_reorder_drag()
                return False

            drag_distance = (event.globalPos() - self._reorder_drag_start_global_pos).manhattanLength()
            if drag_distance >= QtWidgets.QApplication.startDragDistance():
                self._reorder_drag_active = True
            event.accept()
            return True

        if event_type == QtCore.QEvent.MouseButtonRelease:
            if event.button() != QtCore.Qt.LeftButton:
                return False

            source_window = self._reorder_drag_source_window
            target_window = self._mdi_subwindow_at_global_pos(event.globalPos())
            should_swap = self._reorder_drag_active and target_window is not None and target_window != source_window
            self._clear_subwindow_reorder_drag()

            if should_swap and self._mdiArea.swap_subwindow_order(source_window, target_window):
                self.refreshPan()
                self.update_window_highlight(source_window)
                self.update_window_labels(source_window)
            event.accept()
            return True

        return False

    def _clear_subwindow_reorder_drag(self):
        """Reset temporary state for subwindow order dragging."""
        self._reorder_drag_source_window = None
        self._reorder_drag_start_global_pos = None
        self._reorder_drag_active = False
        self._mdiArea.viewport().unsetCursor()

    def _mdi_subwindow_at_global_pos(self, global_pos):
        """Return the MDI subwindow under a global cursor position."""
        mdi_pos = self._mdiArea.mapFromGlobal(global_pos)
        for window in reversed(self._mdiArea.ordered_subwindows()):
            if window.geometry().contains(mdi_pos):
                return window
        return None

    def set_stopsync_pushbutton(self, boolean):
        """Set state of synchronous zoom/pan and appearance of corresponding interface button.

        Args:
            boolean (bool): True to enable synchronized zoom/pan; False to disable.
        """ 
        self._synchZoomAct.setChecked(not boolean)
        self._synchPanAct.setChecked(not boolean)
        
        if self._synchZoomAct.isChecked():
            if self.activeMdiChild:
                self.activeMdiChild.fitToWindow()

        if boolean:
            self.stopsync_toggle_pushbutton.setToolTip("Synchronize zoom and pan (currently unsynced)")
        else:
            self.stopsync_toggle_pushbutton.setToolTip("Unsynchronize zoom and pan (currently synced)")

    def toggle_fullscreen(self):
        """Toggle fullscreen state of app."""
        if self.is_fullscreen:
            self.set_fullscreen_off()
        else:
            self.set_fullscreen_on()
    
    def set_fullscreen_on(self):
        """Enable fullscreen of MultiViewMainWindow.
        
        Moves MDIArea to secondary window and makes it fullscreen.
        Shows interim widget in main window.  
        """
        if self.is_fullscreen:
            return

        position_of_window = self.pos()

        centralwidget_to_be_made_fullscreen = self.mdiarea_plus_buttons
        widget_to_replace_central = self.centralwidget_during_fullscreen

        centralwidget_to_be_made_fullscreen.setParent(None)

        # move() is needed when using multiple monitors because when the widget loses its parent, its position moves to the primary screen origin (0,0) instead of retaining the app's screen
        # The solution is to move the widget to the position of the app window and then make the widget fullscreen
        # A timer is needed for showFullScreen() to apply on the app's screen (otherwise the command is made before the widget's move is established)
        centralwidget_to_be_made_fullscreen.move(position_of_window)
        QtCore.QTimer.singleShot(50, centralwidget_to_be_made_fullscreen.showFullScreen)

        self.showMinimized()

        self.setCentralWidget(widget_to_replace_central)
        widget_to_replace_central.show()
        
        self._mdiArea.tile_what_was_done_last_time()
        self._mdiArea.activateWindow()

        self.is_fullscreen = True
        if self.fullscreen_pushbutton:
            self.fullscreen_pushbutton.setChecked(True)

        if self.activeMdiChild:
            self.synchPan(self.activeMdiChild)

    def set_fullscreen_off(self):
        """Disable fullscreen of MultiViewMainWindow.
        
        Removes interim widget in main window. 
        Returns MDIArea to normal (non-fullscreen) view on main window. 
        """
        if not self.is_fullscreen:
            return
        
        self.showNormal()

        fullscreenwidget_to_be_made_central = self.mdiarea_plus_buttons
        centralwidget_to_be_hidden = self.centralwidget_during_fullscreen

        centralwidget_to_be_hidden.setParent(None)
        centralwidget_to_be_hidden.hide()

        self.setCentralWidget(fullscreenwidget_to_be_made_central)

        self._mdiArea.tile_what_was_done_last_time()
        self._mdiArea.activateWindow()

        self.is_fullscreen = False
        if self.fullscreen_pushbutton:
            self.fullscreen_pushbutton.setChecked(False)
            self.fullscreen_pushbutton.setAttribute(QtCore.Qt.WA_UnderMouse, False)

        self.refreshPanDelayed(100)

    def set_fullscreen(self, boolean):
        """Enable/disable fullscreen of MultiViewMainWindow.
        
        Args:
            boolean (bool): True to enable fullscreen; False to disable.
        """
        if boolean:
            self.set_fullscreen_on()
        elif not boolean:
            self.set_fullscreen_off()
    
    def update_window_highlight(self, window):
        """Update highlight of subwindows in MDIArea.

        Input window should be the subwindow which is active.
        All other subwindow(s) will be shown no highlight.
        
        Args:
            window (QMdiSubWindow): The active subwindow to show highlight and indicate as active.
        """
        if window is None:
            return
        changed_window = window
        if self.is_quiet_mode:
            changed_window.widget().frame_hud.setStyleSheet("QFrame {border: 0px solid transparent}")
        else:
            changed_window.widget().frame_hud.setStyleSheet("QFrame {border: 0.2em blue; border-left-style: outset; border-top-style: inset; border-right-style: inset; border-bottom-style: inset}")

        windows = self._mdiArea.subWindowList()
        for window in windows:
            if window != changed_window:
                window.widget().frame_hud.setStyleSheet("QFrame {border: 0px solid transparent}")

    def update_window_labels(self, window):
        """Update labels of subwindows in MDIArea.

        All subwindows keep image filename labels visible when labels have text.
        Interface visibility only affects sidebars and controls, not image labels.
        
        Args:
            window (QMdiSubWindow): Unused signal argument from active subwindow changes.
        """
        label_visible = True

        windows = self._mdiArea.subWindowList()
        for window in windows:
            window.widget().label_main_topleft.set_visible_based_on_text(label_visible)
            window.widget().label_topright.set_visible_based_on_text(label_visible)
            window.widget().label_bottomright.set_visible_based_on_text(label_visible)
            window.widget().label_bottomleft.set_visible_based_on_text(label_visible)

    def set_window_close_pushbuttons_always_visible(self, window, boolean):
        """Enable/disable the always-on visiblilty of the close X on each subwindow.
        
        Args:
            window (QMdiSubWindow): The active subwindow.
            boolean (bool): True to show the close X always; False to hide unless mouse hovers over.
        """
        if window is None:
            return
        changed_window = window
        always_visible = boolean
        changed_window.widget().set_close_pushbutton_always_visible(always_visible)
        windows = self._mdiArea.subWindowList()
        for window in windows:
            if window != changed_window:
                window.widget().set_close_pushbutton_always_visible(always_visible)

    def set_window_mouse_rect_visible(self, window, boolean):
        """Enable/disable the visiblilty of the red 1x1 outline at the pointer
        
        Outline shows the relative size of a pixel in the active subwindow.
        
        Args:
            window (QMdiSubWindow): The active subwindow.
            boolean (bool): True to show 1x1 outline; False to hide.
        """
        if window is None:
            return
        changed_window = window
        visible = boolean
        changed_window.widget().set_mouse_rect_visible(visible)
        windows = self._mdiArea.subWindowList()
        for window in windows:
            if window != changed_window:
                window.widget().set_mouse_rect_visible(visible)

    def auto_tile_subwindows_on_close(self):
        """Tile the subwindows of MDIArea using previously used tile method."""
        if self.subwindow_was_just_closed:
            self.subwindow_was_just_closed = False
            QtCore.QTimer.singleShot(50, self._mdiArea.tile_what_was_done_last_time)
            self.refreshPanDelayed(50)

    def set_single_window_transform_mode_smooth(self, window, boolean):
        """Set the transform mode of a given subwindow.
        
        Args:
            window (QMdiSubWindow): The subwindow.
            boolean (bool): True to smooth (interpolate); False to fast (not interpolate).
        """
        if window is None:
            return
        changed_window = window
        changed_window.widget().set_transform_mode_smooth(boolean)
        

    def set_all_window_transform_mode_smooth(self, boolean):
        """Set the transform mode of all subwindows. 
        
        Args:
            boolean (bool): True to smooth (interpolate); False to fast (not interpolate).
        """
        if self._mdiArea.activeSubWindow() is None:
            return
        windows = self._mdiArea.subWindowList()
        for window in windows:
            window.widget().set_transform_mode_smooth(boolean)

    def set_all_background_color(self, color):
        """Set the background color of all subwindows. 
        
        Args:
            color (list): Descriptor string and RGB int values. Example: ["White", 255, 255, 255].
        """
        if self._mdiArea.activeSubWindow() is None:
            return
        windows = self._mdiArea.subWindowList()
        for window in windows:
            window.widget().set_scene_background_color(color)
        self.scene_background_color = color

    def set_all_sync_zoom_by(self, by: str):
        """[str] Set the method by which to sync zoom all windows."""
        if self._mdiArea.activeSubWindow() is None:
            return
        windows = self._mdiArea.subWindowList()
        for window in windows:
            window.widget().update_sync_zoom_by(by)
        self.sync_zoom_by = by
        self.refreshZoom()

    def info_button_clicked(self):
        """Trigger when info button is clicked."""
        self.show_about()
        return
    
    def show_about(self):
        """Show about box."""
        sp = "<br>"
        title = "MosaicView"
        text = "MosaicView"
        text = text + sp + "Lars Maxfield"
        text = text + sp + "Version: " + VERSION
        text = text + sp + "License: <a href='https://www.gnu.org/licenses/gpl-3.0.en.html'>GNU GPL v3</a> or later"
        text = text + sp + "Source: <a href='https://github.com/halley/MosaicView'>github.com/halley/MosaicView</a>"
        text = text + sp + "Tutorial: <a href='https://halley.github.io/MosaicView'>halley.github.io/MosaicView</a>"
        box = QtWidgets.QMessageBox.about(self, title, text)

    # View loading methods

    def loadFile(self, filename_main_topleft, filename_topright=None, filename_bottomleft=None, filename_bottomright=None, show_differences=False):
        """Load an individual image or sliding overlay into new subwindow.

        Args:
            filename_main_topleft (str): The image filepath of the main image to be viewed; the basis of the sliding overlay (main; topleft)
            filename_topright (str): The image filepath for top-right of the sliding overlay (set None to exclude)
            filename_bottomleft (str): The image filepath for bottom-left of the sliding overlay (set None to exclude)
            filename_bottomright (str): The image filepath for bottom-right of the sliding overlay (set None to exclude)
            show_differences (bool): True to render non-base overlay images as differences against the base image.
        """
        
        self.display_loading_grayout(True, "Loading viewer with main image '" + filename_main_topleft.split("/")[-1] + "'...")

        activeMdiChild = self.activeMdiChild
        QtWidgets.QApplication.setOverrideCursor(QtCore.Qt.WaitCursor)

        transform_mode_smooth = self.is_global_transform_mode_smooth
        loaded_view = load_view_pixmaps(
            filename_main_topleft,
            filename_topright,
            filename_bottomleft,
            filename_bottomright,
            show_differences=show_differences,
        )
        
        QtWidgets.QApplication.restoreOverrideCursor()
        
        if (not loaded_view.main or
            loaded_view.main.width() == 0 or loaded_view.main.height() == 0):
            self.display_loading_grayout(True, "Waiting on dialog box...")
            QtWidgets.QMessageBox.warning(self, APPNAME,
                                      "Cannot read file %s." % (filename_main_topleft,))
            self.updateRecentFileSettings(filename_main_topleft, delete=True)
            self.updateRecentFileActions()
            self.display_loading_grayout(False)
            return

        child = self.createMdiChild(
            loaded_view.main,
            filename_main_topleft,
            loaded_view.topright,
            loaded_view.bottomleft,
            loaded_view.bottomright,
            transform_mode_smooth,
        )
        child.set_image_paths(filename_main_topleft, filename_topright, filename_bottomleft, filename_bottomright)

        # Show filenames
        child.refresh_main_label()
        child.label_topright.setText(filename_topright)
        child.label_bottomright.setText(filename_bottomright)
        child.label_bottomleft.setText(filename_bottomleft)
        
        child.show()

        if activeMdiChild:
            if self._synchPanAct.isChecked():
                self.synchPan(activeMdiChild)
            if self._synchZoomAct.isChecked():
                self.synchZoom(activeMdiChild)
                
        self._mdiArea.tile_what_was_done_last_time()

        child.set_close_pushbutton_always_visible(self.is_interface_showing)
        if self.scene_background_color is not None:
            child.set_scene_background_color(self.scene_background_color)

        self.updateRecentFileSettings(filename_main_topleft)
        self.updateRecentFileActions()
        
        self._last_accessed_fullpath = filename_main_topleft
        self.sync_file_browser_to_path(filename_main_topleft)

        self.display_loading_grayout(False)
        
        sync_by = self.sync_zoom_by
        child.update_sync_zoom_by(sync_by)

        child.fitToWindow()
        self.update_zoom_panel()

        self.statusBar().showMessage("File loaded", 2000)

    def load_from_dragged_and_dropped_file(self, filename_main_topleft):
        """Load an individual image (convenience function — e.g., from a single emitted single filename)."""
        self.loadFile(filename_main_topleft)

    def sync_file_browser_to_path(self, filepath):
        """Keep the file browser aligned with the most recently opened image."""
        if filepath:
            self.file_browser_panel.focus_path(filepath)

    def is_supported_browser_file(self, filepath):
        """Return whether the file browser selection looks like an image file."""
        if not filepath or not os.path.isfile(filepath):
            return False

        detected_format = QtGui.QImageReader.imageFormat(filepath)
        if detected_format:
            return True

        _, extension = os.path.splitext(filepath)
        return extension.lower() in {".svg", ".svgz"}

    def open_file_from_browser(self, filepath):
        """Open an image selected from the in-app file browser."""
        if not self.is_supported_browser_file(filepath):
            self.statusBar().showMessage("Select an image file to open it in the viewer.", 3000)
            return

        self.loadFile(filepath)
    
    def createMdiChild(self, pixmap, filename_main_topleft, pixmap_topright, pixmap_bottomleft, pixmap_bottomright, transform_mode_smooth):
        """Create new viewing widget for an individual image or sliding overlay to be placed in a new subwindow.

        Args:
            pixmap (QPixmap): The main image to be viewed; the basis of the sliding overlay (main; topleft)
            filename_main_topleft (str): The image filepath of the main image.
            pixmap_topright (QPixmap): The top-right image of the sliding overlay (set None to exclude).
            pixmap_bottomleft (QPixmap): The bottom-left image of the sliding overlay (set None to exclude).
            pixmap_bottomright (QPixmap): The bottom-right image of the sliding overlay (set None to exclude).

        Returns:
            child (SplitViewMdiChild): The viewing widget instance.
        """
        
        child = SplitViewMdiChild(pixmap,
                         filename_main_topleft,
                         "Window %d" % (len(self._mdiArea.subWindowList())+1),
                         pixmap_topright, pixmap_bottomleft, pixmap_bottomright, 
                         transform_mode_smooth)

        child.enableScrollBars(self._showScrollbarsAct.isChecked())

        child.sync_this_zoom = True
        child.sync_this_pan = True
        
        self._mdiArea.addSubWindow(child, QtCore.Qt.FramelessWindowHint) # LVM: No frame, starts fitted

        child.scrollChanged.connect(self.panChanged)
        child.transformChanged.connect(self.zoomChanged)
        
        child.positionChanged.connect(self.on_positionChanged)
        child.tracker.mouse_leaved.connect(self.on_mouse_leaved)
        
        child.scrollChanged.connect(self.on_scrollChanged)

        child.became_closed.connect(self.on_subwindow_closed)
        child.was_clicked_close_pushbutton.connect(lambda child=child: self.close_mdi_child(child))
        child.signal_display_loading_grayout.connect(self.display_loading_grayout)
        child.was_set_global_transform_mode.connect(self.set_all_window_transform_mode_smooth)
        child.was_set_scene_background_color.connect(self.set_all_background_color)
        child.was_set_sync_zoom_by.connect(self.set_all_sync_zoom_by)

        return child

    def close_mdi_child(self, child):
        """Close the specific MDI child whose close button was clicked."""
        if child is None:
            return

        for window in self._mdiArea.subWindowList():
            if window.widget() is child:
                self._mdiArea.setActiveSubWindow(window)
                window.close()
                return

        child.close()


    # View and split methods

    @QtCore.pyqtSlot()
    def on_create_splitview(self):
        """Load a sliding overlay using the filepaths of the current images in the sliding overlay creator."""
        # Get filenames
        file_path_main_topleft = self._splitview_creator.drag_drop_area.app_main_topleft.file_path
        file_path_topright = self._splitview_creator.drag_drop_area.app_topright.file_path
        file_path_bottomleft = self._splitview_creator.drag_drop_area.app_bottomleft.file_path
        file_path_bottomright = self._splitview_creator.drag_drop_area.app_bottomright.file_path

        # loadFile with those filenames
        self.loadFile(
            file_path_main_topleft,
            file_path_topright,
            file_path_bottomleft,
            file_path_bottomright,
            show_differences=self._splitview_creator.show_differences_in_overlay,
        )

    def fit_to_window(self):
        """Fit the view of the active subwindow (if it exists)."""
        if self.activeMdiChild:
            self.activeMdiChild.fitToWindow()

    @QtCore.pyqtSlot()
    def on_scrollChanged(self):
        """Refresh position of split of all subwindows based on their respective last position."""
        windows = self._mdiArea.subWindowList()
        for window in windows:
            window.widget().refresh_split_based_on_last_updated_point_of_split_on_scene_main()

    def on_subwindow_closed(self):
        """Record that a subwindow was closed upon the closing of a subwindow."""
        self.subwindow_was_just_closed = True
    
    @QtCore.pyqtSlot()
    def on_mouse_leaved(self):
        """Update displayed coordinates of mouse as N/A upon the mouse leaving the subwindow area."""
        self._label_mouse.setText("View pixel coordinates: ( N/A , N/A )")
        self._label_mouse.adjustSize()
        
    @QtCore.pyqtSlot(QtCore.QPoint)
    def on_positionChanged(self, pos):
        """Update displayed coordinates of mouse on the active subwindow using global coordinates."""
    
        point_of_mouse_on_viewport = QtCore.QPoint(int(pos.x()), int(pos.y()))
        pos_qcursor_global = QtGui.QCursor.pos()
        
        if self.activeMdiChild:
        
            # Use mouse position to grab scene coordinates (activeMdiChild?)
            active_view = self.activeMdiChild._view_main_topleft
            point_of_mouse_on_scene = active_view.mapToScene(point_of_mouse_on_viewport.x(), point_of_mouse_on_viewport.y())

            self._label_mouse.setText("View pixel coordinates: ( x = %d , y = %d )" % (point_of_mouse_on_scene.x(), point_of_mouse_on_scene.y()))
            
            pos_qcursor_view = active_view.mapFromGlobal(pos_qcursor_global)
            pos_qcursor_scene = active_view.mapToScene(pos_qcursor_view)
            # print("Cursor coords scene: ( %d , %d )" % (pos_qcursor_scene.x(), pos_qcursor_scene.y()))
            
        else:
            
            self._label_mouse.setText("View pixel coordinates: ( N/A , N/A )")
            
        self._label_mouse.adjustSize()

    
    # [Legacy methods from derived MDI Image Viewer]

    def createMappedAction(self, icon, text, parent, shortcut, methodName):
        """Create |QAction| that is mapped via methodName to call.

        :param icon: icon associated with |QAction|
        :type icon: |QIcon| or None
        :param str text: the |QAction| descriptive text
        :param QObject parent: the parent |QObject|
        :param QKeySequence shortcut: the shortcut |QKeySequence|
        :param str methodName: name of method to call when |QAction| is
                               triggered
        :rtype: |QAction|"""

        if icon is not None:
            action = QtWidgets.QAction(icon, text, parent,
                                   shortcut=shortcut,
                                   triggered=self._actionMapper.map)
        else:
            action = QtWidgets.QAction(text, parent,
                                   shortcut=shortcut,
                                   triggered=self._actionMapper.map)
        self._actionMapper.setMapping(action, methodName)
        return action

    def createActions(self):
        """Create actions used in menus."""
        #File menu actions
        self._openAct = QtWidgets.QAction(
            "&Open...", self,
            shortcut=QtGui.QKeySequence.Open,
            statusTip="Open an existing file",
            triggered=self.open)

        self._switchLayoutDirectionAct = QtWidgets.QAction(
            "Switch &layout direction", self,
            triggered=self.switchLayoutDirection)

        #create dummy recent file actions
        for i in range(MultiViewMainWindow.MaxRecentFiles):
            self._recentFileActions.append(
                QtWidgets.QAction(self, visible=False,
                              triggered=self._recentFileMapper.map))

        self._exitAct = QtWidgets.QAction(
            "E&xit", self,
            shortcut=QtGui.QKeySequence.Quit,
            statusTip="Exit the application",
            triggered=QtWidgets.QApplication.closeAllWindows)

        #View menu actions
        self._showScrollbarsAct = QtWidgets.QAction(
            "&Scrollbars", self,
            checkable=True,
            statusTip="Toggle display of subwindow scrollbars",
            triggered=self.toggleScrollbars)

        self._showStatusbarAct = QtWidgets.QAction(
            "S&tatusbar", self,
            checkable=True,
            statusTip="Toggle display of statusbar",
            triggered=self.toggleStatusbar)

        self._synchZoomAct = QtWidgets.QAction(
            "Synch &Zoom", self,
            checkable=True,
            statusTip="Synch zooming of subwindows",
            triggered=self.toggleSynchZoom)

        self._synchPanAct = QtWidgets.QAction(
            "Synch &Pan", self,
            checkable=True,
            statusTip="Synch panning of subwindows",
            triggered=self.toggleSynchPan)

        #Scroll menu actions
        self._scrollActions = [
            self.createMappedAction(
                None,
                "&Top", self,
                QtGui.QKeySequence.MoveToStartOfDocument,
                "scrollToTop"),

            self.createMappedAction(
                None,
                "&Bottom", self,
                QtGui.QKeySequence.MoveToEndOfDocument,
                "scrollToBottom"),

            self.createMappedAction(
                None,
                "&Left Edge", self,
                QtGui.QKeySequence.MoveToStartOfLine,
                "scrollToBegin"),

            self.createMappedAction(
                None,
                "&Right Edge", self,
                QtGui.QKeySequence.MoveToEndOfLine,
                "scrollToEnd"),

            self.createMappedAction(
                None,
                "&Center", self,
                "5",
                "centerView"),
            ]

        #zoom menu actions
        separatorAct = QtWidgets.QAction(self)
        separatorAct.setSeparator(True)

        self._zoomActions = [
            self.createMappedAction(
                None,
                "Zoo&m In (25%)", self,
                QtGui.QKeySequence.ZoomIn,
                "zoomIn"),

            self.createMappedAction(
                None,
                "Zoom &Out (25%)", self,
                QtGui.QKeySequence.ZoomOut,
                "zoomOut"),

            #self.createMappedAction(
                #None,
                #"&Zoom To...", self,
                #"Z",
                #"zoomTo"),

            separatorAct,

            self.createMappedAction(
                None,
                "Actual &Size", self,
                "/",
                "actualSize"),

            self.createMappedAction(
                None,
                "Fit &Image", self,
                "*",
                "fitToWindow"),

            self.createMappedAction(
                None,
                "Fit &Width", self,
                "Alt+Right",
                "fitWidth"),

            self.createMappedAction(
                None,
                "Fit &Height", self,
                "Alt+Down",
                "fitHeight"),
           ]

        #Window menu actions
        self._activateSubWindowSystemMenuAct = QtWidgets.QAction(
            "Activate &System Menu", self,
            shortcut="Ctrl+ ",
            statusTip="Activate subwindow System Menu",
            triggered=self.activateSubwindowSystemMenu)

        self._closeAct = QtWidgets.QAction(
            "Cl&ose", self,
            shortcut=QtGui.QKeySequence.Close,
            shortcutContext=QtCore.Qt.WidgetShortcut,
            #shortcut="Ctrl+Alt+F4",
            statusTip="Close the active window",
            triggered=self._mdiArea.closeActiveSubWindow)

        self._closeAllAct = QtWidgets.QAction(
            "Close &All", self,
            statusTip="Close all the windows",
            triggered=self._mdiArea.closeAllSubWindows)

        self._tileAct = QtWidgets.QAction(
            "&Tile", self,
            statusTip="Tile the windows",
            triggered=self._mdiArea.tileSubWindows)

        self._tileAct.triggered.connect(self.tile_and_fit_mdiArea)

        self._cascadeAct = QtWidgets.QAction(
            "&Cascade", self,
            statusTip="Cascade the windows",
            triggered=self._mdiArea.cascadeSubWindows)

        self._nextAct = QtWidgets.QAction(
            "Ne&xt", self,
            shortcut=QtGui.QKeySequence.NextChild,
            statusTip="Move the focus to the next window",
            triggered=self._mdiArea.activateNextSubWindow)

        self._previousAct = QtWidgets.QAction(
            "Pre&vious", self,
            shortcut=QtGui.QKeySequence.PreviousChild,
            statusTip="Move the focus to the previous window",
            triggered=self._mdiArea.activatePreviousSubWindow)

        self._separatorAct = QtWidgets.QAction(self)
        self._separatorAct.setSeparator(True)

        self._aboutAct = QtWidgets.QAction(
            "&About", self,
            statusTip="Show the application's About box",
            triggered=self.about)

        self._aboutQtAct = QtWidgets.QAction(
            "About &Qt", self,
            statusTip="Show the Qt library's About box",
            triggered=QtWidgets.QApplication.aboutQt)

    def createMenus(self):
        """Create menus."""
        self._fileMenu = self.menuBar().addMenu("&File")
        self._fileMenu.addAction(self._openAct)
        self._fileMenu.addAction(self._switchLayoutDirectionAct)

        self._fileSeparatorAct = self._fileMenu.addSeparator()
        for action in self._recentFileActions:
            self._fileMenu.addAction(action)
        self.updateRecentFileActions()
        self._fileMenu.addSeparator()
        self._fileMenu.addAction(self._exitAct)

        self._viewMenu = self.menuBar().addMenu("&View")
        self._viewMenu.addAction(self._showScrollbarsAct)
        self._viewMenu.addAction(self._showStatusbarAct)
        self._viewMenu.addSeparator()
        self._viewMenu.addAction(self._synchZoomAct)
        self._viewMenu.addAction(self._synchPanAct)

        self._scrollMenu = self.menuBar().addMenu("&Scroll")
        [self._scrollMenu.addAction(action) for action in self._scrollActions]

        self._zoomMenu = self.menuBar().addMenu("&Zoom")
        [self._zoomMenu.addAction(action) for action in self._zoomActions]

        self._windowMenu = self.menuBar().addMenu("&Window")
        self.updateWindowMenu()
        self._windowMenu.aboutToShow.connect(self.updateWindowMenu)

        self.menuBar().addSeparator()

        self._helpMenu = self.menuBar().addMenu("&Help")
        self._helpMenu.addAction(self._aboutAct)
        self._helpMenu.addAction(self._aboutQtAct)

    def updateMenus(self):
        """Update menus."""
        hasMdiChild = (self.activeMdiChild is not None)

        self._scrollMenu.setEnabled(hasMdiChild)
        self._zoomMenu.setEnabled(hasMdiChild)

        self._closeAct.setEnabled(hasMdiChild)
        self._closeAllAct.setEnabled(hasMdiChild)

        self._tileAct.setEnabled(hasMdiChild)
        self._cascadeAct.setEnabled(hasMdiChild)
        self._nextAct.setEnabled(hasMdiChild)
        self._previousAct.setEnabled(hasMdiChild)
        self._separatorAct.setVisible(hasMdiChild)

    def updateRecentFileActions(self):
        """Update recent file menu items."""
        settings = QtCore.QSettings()
        files = settings.value(SETTING_RECENTFILELIST)
        numRecentFiles = min(len(files) if files else 0,
                             MultiViewMainWindow.MaxRecentFiles)

        for i in range(numRecentFiles):
            text = "&%d %s" % (i + 1, strippedName(files[i]))
            self._recentFileActions[i].setText(text)
            self._recentFileActions[i].setData(files[i])
            self._recentFileActions[i].setVisible(True)
            self._recentFileMapper.setMapping(self._recentFileActions[i],
                                              files[i])

        for j in range(numRecentFiles, MultiViewMainWindow.MaxRecentFiles):
            self._recentFileActions[j].setVisible(False)

        self._fileSeparatorAct.setVisible((numRecentFiles > 0))

    def updateWindowMenu(self):
        """Update the Window menu."""
        self._windowMenu.clear()
        self._windowMenu.addAction(self._closeAct)
        self._windowMenu.addAction(self._closeAllAct)
        self._windowMenu.addSeparator()
        self._windowMenu.addAction(self._tileAct)
        self._windowMenu.addAction(self._cascadeAct)
        self._windowMenu.addSeparator()
        self._windowMenu.addAction(self._nextAct)
        self._windowMenu.addAction(self._previousAct)
        self._windowMenu.addAction(self._separatorAct)

        windows = self._mdiArea.subWindowList()
        self._separatorAct.setVisible(len(windows) != 0)

        for i, window in enumerate(windows):
            child = window.widget()

            text = "%d %s" % (i + 1, child.userFriendlyCurrentFile)
            if i < 9:
                text = '&' + text

            action = self._windowMenu.addAction(text)
            action.setCheckable(True)
            action.setChecked(child == self.activeMdiChild)
            action.triggered.connect(self._windowMapper.map)
            self._windowMapper.setMapping(action, window)

    def createStatusBarLabel(self, stretch=0):
        """Create status bar label.

        :param int stretch: stretch factor
        :rtype: |QLabel|"""
        label = QtWidgets.QLabel()
        label.setFrameStyle(QtWidgets.QFrame.Panel | QtWidgets.QFrame.Sunken)
        label.setLineWidth(2)
        self.statusBar().addWidget(label, stretch)
        return label

    def createStatusBar(self):
        """Create status bar."""
        statusBar = self.statusBar()

        self._sbLabelName = self.createStatusBarLabel(1)
        self._sbLabelSize = self.createStatusBarLabel()
        self._sbLabelDimensions = self.createStatusBarLabel()
        self._sbLabelDate = self.createStatusBarLabel()
        self._sbLabelZoom = self.createStatusBarLabel()

        statusBar.showMessage("Ready")

    @property
    def activeMdiChild(self):
        """Get active MDI child (:class:`SplitViewMdiChild` or *None*)."""
        activeSubWindow = self._mdiArea.activeSubWindow()
        if activeSubWindow:
            return activeSubWindow.widget()
        return None


    def closeEvent(self, event):
        """Overrides close event to save application settings.

        :param QEvent event: instance of |QEvent|"""

        if self.is_fullscreen: # Needed to properly close the image viewer if the main window is closed while the viewer is fullscreen
            self.is_fullscreen = False
            self.setCentralWidget(self.mdiarea_plus_buttons)

        self._mdiArea.closeAllSubWindows()
        if self.activeMdiChild:
            event.ignore()
        else:
            self.writeSettings()
            event.accept()
            
    
    def tile_and_fit_mdiArea(self):
        self._mdiArea.tileSubWindows()

    
    # Synchronized pan and zoom methods
    
    @QtCore.pyqtSlot(str)
    def mappedImageViewerAction(self, methodName):
        """Perform action mapped to :class:`aux_splitview.SplitView`
        methodName.

        :param str methodName: method to call"""
        activeViewer = self.activeMdiChild
        if hasattr(activeViewer, str(methodName)):
            getattr(activeViewer, str(methodName))()

    @QtCore.pyqtSlot()
    def toggleSynchPan(self):
        """Toggle synchronized subwindow panning."""
        if self._synchPanAct.isChecked():
            self.synchPan(self.activeMdiChild)

    @QtCore.pyqtSlot()
    def panChanged(self):
        """Synchronize subwindow pans."""
        mdiChild = self.sender()
        while mdiChild is not None and type(mdiChild) != SplitViewMdiChild:
            mdiChild = mdiChild.parent()
        if mdiChild and self._synchPanAct.isChecked():
            self.synchPan(mdiChild)

    @QtCore.pyqtSlot()
    def toggleSynchZoom(self):
        """Toggle synchronized subwindow zooming."""
        if self._synchZoomAct.isChecked():
            self.synchZoom(self.activeMdiChild)

    @QtCore.pyqtSlot()
    def zoomChanged(self):
        """Synchronize subwindow zooms."""
        mdiChild = self.sender()
        if self._synchZoomAct.isChecked():
            self.synchZoom(mdiChild)
        self.updateStatusBar()
        self.update_zoom_panel()

    def synchPan(self, fromViewer):
        """Synch panning of all subwindowws to the same as *fromViewer*.

        :param fromViewer: :class:`SplitViewMdiChild` that initiated synching"""

        assert isinstance(fromViewer, SplitViewMdiChild)
        if not fromViewer:
            return
        if self._handlingScrollChangedSignal:
            return
        if fromViewer.parent() != self._mdiArea.activeSubWindow(): # Prevent circular scroll state change signals from propagating
            if fromViewer.parent() != self:
                return
        self._handlingScrollChangedSignal = True

        newState = fromViewer.scrollState
        changedWindow = fromViewer.parent()
        windows = self._mdiArea.subWindowList()
        for window in windows:
            if window != changedWindow:
                if window.widget().sync_this_pan:
                    window.widget().scrollState = newState
                    window.widget().resize_scene()

        self._handlingScrollChangedSignal = False

    def synchZoom(self, fromViewer):
        """Synch zoom of all subwindowws to the same as *fromViewer*.

        :param fromViewer: :class:`SplitViewMdiChild` that initiated synching"""
        if not fromViewer:
            return
        newZoomFactor = fromViewer.zoomFactor

        sync_by = self.sync_zoom_by

        sender_dimension = determineSyncSenderDimension(fromViewer.imageWidth,
                                                        fromViewer.imageHeight,
                                                        sync_by)

        changedWindow = fromViewer.parent()
        windows = self._mdiArea.subWindowList()
        for window in windows:
            if window != changedWindow:
                receiver = window.widget()
                if receiver.sync_this_zoom:
                    adjustment_factor = determineSyncAdjustmentFactor(sync_by,
                                                                      sender_dimension,
                                                                      receiver.imageWidth,
                                                                      receiver.imageHeight)

                    receiver.zoomFactor = newZoomFactor*adjustment_factor
                    receiver.resize_scene()
        self.refreshPan()

    def refreshPan(self):
        if self.activeMdiChild:
            self.synchPan(self.activeMdiChild)

    def refreshPanDelayed(self, ms=0):
        QtCore.QTimer.singleShot(ms, self.refreshPan)

    def refreshZoom(self):
        if self.activeMdiChild:
            self.synchZoom(self.activeMdiChild)


    # Methods from PyQt MDI Image Viewer left unaltered

    @QtCore.pyqtSlot()
    def activateSubwindowSystemMenu(self):
        """Activate current subwindow's System Menu."""
        activeSubWindow = self._mdiArea.activeSubWindow()
        if activeSubWindow:
            activeSubWindow.showSystemMenu()

    @QtCore.pyqtSlot(str)
    def openRecentFile(self, filename_main_topleft):
        """Open a recent file.

        :param str filename_main_topleft: filename_main_topleft to view"""
        self.loadFile(filename_main_topleft, None, None, None)

    @QtCore.pyqtSlot()
    def open(self):
        """Handle the open action."""
        fileDialog = QtWidgets.QFileDialog(self)
        settings = QtCore.QSettings()
        fileDialog.setNameFilters([
            "Common image files (*.jpeg *.jpg  *.png *.tiff *.tif *.bmp *.gif *.webp *.svg)",
            "JPEG image files (*.jpeg *.jpg)", 
            "PNG image files (*.png)", 
            "TIFF image files (*.tiff *.tif)",
            "BMP (*.bmp)",
            "All files (*)",])
        if not settings.contains(SETTING_FILEOPEN + "/state"):
            fileDialog.setDirectory(".")
        else:
            self.restoreDialogState(fileDialog, SETTING_FILEOPEN)
        fileDialog.setFileMode(QtWidgets.QFileDialog.ExistingFile)
        if not fileDialog.exec_():
            return
        self.saveDialogState(fileDialog, SETTING_FILEOPEN)

        filename_main_topleft = fileDialog.selectedFiles()[0]
        self.loadFile(filename_main_topleft, None, None, None)

    def open_multiple(self):
        """Handle the open multiple action."""
        last_accessed_fullpath = self._last_accessed_fullpath
        filters = "\
            Common image files (*.jpeg *.jpg  *.png *.tiff *.tif *.bmp *.gif *.webp *.svg);;\
            JPEG image files (*.jpeg *.jpg);;\
            PNG image files (*.png);;\
            TIFF image files (*.tiff *.tif);;\
            BMP (*.bmp);;\
            All files (*)"
        fullpaths, _ = QtWidgets.QFileDialog.getOpenFileNames(self, "Select image(s) to open", last_accessed_fullpath, filters)

        for fullpath in fullpaths:
            self.loadFile(fullpath, None, None, None)



    @QtCore.pyqtSlot()
    def toggleScrollbars(self):
        """Toggle subwindow scrollbar visibility."""
        checked = self._showScrollbarsAct.isChecked()

        windows = self._mdiArea.subWindowList()
        for window in windows:
            child = window.widget()
            child.enableScrollBars(checked)

    @QtCore.pyqtSlot()
    def toggleStatusbar(self):
        """Toggle status bar visibility."""
        self.statusBar().setVisible(self._showStatusbarAct.isChecked())


    @QtCore.pyqtSlot()
    def about(self):
        """Display About dialog box."""
        QtWidgets.QMessageBox.about(self, "About MDI",
                "<b>MDI Image Viewer</b> demonstrates how to"
                "synchronize the panning and zooming of multiple image"
                "viewer windows using Qt.")
    @QtCore.pyqtSlot(QtWidgets.QMdiSubWindow)
    def subWindowActivated(self, window):
        """Handle |QMdiSubWindow| activated signal.

        :param |QMdiSubWindow| window: |QMdiSubWindow| that was just
                                       activated"""
        self.updateStatusBar()

    @QtCore.pyqtSlot(QtWidgets.QMdiSubWindow)
    def setActiveSubWindow(self, window):
        """Set active |QMdiSubWindow|.

        :param |QMdiSubWindow| window: |QMdiSubWindow| to activate """
        if window:
            self._mdiArea.setActiveSubWindow(window)


    def updateStatusBar(self):
        """Update status bar."""
        self.statusBar().setVisible(self._showStatusbarAct.isChecked())
        imageViewer = self.activeMdiChild
        if not imageViewer:
            self._sbLabelName.setText("")
            self._sbLabelSize.setText("")
            self._sbLabelDimensions.setText("")
            self._sbLabelDate.setText("")
            self._sbLabelZoom.setText("")

            self._sbLabelSize.hide()
            self._sbLabelDimensions.hide()
            self._sbLabelDate.hide()
            self._sbLabelZoom.hide()
            return

        filename_main_topleft = imageViewer.currentFile
        self._sbLabelName.setText(" %s " % filename_main_topleft)

        fi = QtCore.QFileInfo(filename_main_topleft)
        size = fi.size()
        fmt = " %.1f %s "
        if size > 1024*1024*1024:
            unit = "MB"
            size /= 1024*1024*1024
        elif size > 1024*1024:
            unit = "MB"
            size /= 1024*1024
        elif size > 1024:
            unit = "KB"
            size /= 1024
        else:
            unit = "Bytes"
            fmt = " %d %s "
        self._sbLabelSize.setText(fmt % (size, unit))

        pixmap = imageViewer.pixmap_main_topleft
        self._sbLabelDimensions.setText(" %dx%dx%d " %
                                        (pixmap.width(),
                                         pixmap.height(),
                                         pixmap.depth()))

        self._sbLabelDate.setText(
            " %s " %
            fi.lastModified().toString(QtCore.Qt.SystemLocaleShortDate))
        self._sbLabelZoom.setText(" %0.f%% " % (imageViewer.zoomFactor*100,))

        self._sbLabelSize.show()
        self._sbLabelDimensions.show()
        self._sbLabelDate.show()
        self._sbLabelZoom.show()
        
    def switchLayoutDirection(self):
        """Switch MDI subwindow layout direction."""
        if self.layoutDirection() == QtCore.Qt.LeftToRight:
            QtWidgets.QApplication.setLayoutDirection(QtCore.Qt.RightToLeft)
        else:
            QtWidgets.QApplication.setLayoutDirection(QtCore.Qt.LeftToRight)

    def saveDialogState(self, dialog, groupName):
        """Save dialog state, position & size.

        :param |QDialog| dialog: dialog to save state of
        :param str groupName: |QSettings| group name"""
        assert isinstance(dialog, QtWidgets.QDialog)

        settings = QtCore.QSettings()
        settings.beginGroup(groupName)

        settings.setValue('state', dialog.saveState())
        settings.setValue('geometry', dialog.saveGeometry())
        settings.setValue('filter', dialog.selectedNameFilter())

        settings.endGroup()

    def restoreDialogState(self, dialog, groupName):
        """Restore dialog state, position & size.

        :param str groupName: |QSettings| group name"""
        assert isinstance(dialog, QtWidgets.QDialog)

        settings = QtCore.QSettings()
        settings.beginGroup(groupName)

        dialog.restoreState(settings.value('state'))
        dialog.restoreGeometry(settings.value('geometry'))
        dialog.selectNameFilter(settings.value('filter', ""))

        settings.endGroup()

    def writeSettings(self):
        """Write application settings."""
        settings = QtCore.QSettings()
        settings.setValue('pos', self.pos())
        settings.setValue('size', self.size())
        settings.setValue('windowgeometry', self.saveGeometry())
        settings.setValue('windowstate', self.saveState())

        settings.setValue(SETTING_SCROLLBARS,
                          self._showScrollbarsAct.isChecked())
        settings.setValue(SETTING_STATUSBAR,
                          self._showStatusbarAct.isChecked())
        settings.setValue(SETTING_SYNCHZOOM,
                          self._synchZoomAct.isChecked())
        settings.setValue(SETTING_SYNCHPAN,
                          self._synchPanAct.isChecked())

    def readSettings(self):
        """Read application settings."""
        
        scrollbars_always_checked_off_at_startup = True
        statusbar_always_checked_off_at_startup = True
        sync_always_checked_on_at_startup = True

        settings = QtCore.QSettings()

        pos = settings.value('pos', QtCore.QPoint(100, 100))
        size = settings.value('size', QtCore.QSize(1100, 600))
        self.move(pos)
        self.resize(size)

        if settings.contains('windowgeometry'):
            self.restoreGeometry(settings.value('windowgeometry'))
        if settings.contains('windowstate'):
            self.restoreState(settings.value('windowstate'))

        
        if scrollbars_always_checked_off_at_startup:
            self._showScrollbarsAct.setChecked(False)
        else:
            self._showScrollbarsAct.setChecked(
                toBool(settings.value(SETTING_SCROLLBARS, False)))

        if statusbar_always_checked_off_at_startup:
            self._showStatusbarAct.setChecked(False)
        else:
            self._showStatusbarAct.setChecked(
                toBool(settings.value(SETTING_STATUSBAR, False)))

        if sync_always_checked_on_at_startup:
            self._synchZoomAct.setChecked(True)
            self._synchPanAct.setChecked(True)
        else:
            self._synchZoomAct.setChecked(
                toBool(settings.value(SETTING_SYNCHZOOM, False)))
            self._synchPanAct.setChecked(
                toBool(settings.value(SETTING_SYNCHPAN, False)))

    def updateRecentFileSettings(self, filename_main_topleft, delete=False):
        """Update recent file list setting.

        :param str filename_main_topleft: filename_main_topleft to add or remove from recent file
                             list
        :param bool delete: if True then filename_main_topleft removed, otherwise added"""
        settings = QtCore.QSettings()
        
        try:
            files = list(settings.value(SETTING_RECENTFILELIST, []))
        except TypeError:
            files = []

        try:
            files.remove(filename_main_topleft)
        except ValueError:
            pass

        if not delete:
            files.insert(0, filename_main_topleft)
        del files[MultiViewMainWindow.MaxRecentFiles:]

        settings.setValue(SETTING_RECENTFILELIST, files)


if __name__ == '__main__':
    main()
