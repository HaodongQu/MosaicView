#!/usr/bin/env python3

"""QMdiArea with drag-and-drop functions and vertical/horizontal window tiling.

Not intended as a script.

Creates the multi document interface (MDI) widget for the MosaicView.
"""
# SPDX-License-Identifier: GPL-3.0-or-later



import math

from PyQt5 import QtWidgets, QtCore



class QMdiAreaWithCustomSignals(QtWidgets.QMdiArea):
    """Extend QMdiArea with drag-and-drop functions and vertical/horizontal window tiling.

    Instantiate without input.
    
    Features:
        Signals for drag-and-drop and subwindow events.
        Methods for arranging the subwindows vertically and horizontally, and to track the history of the arrangement.
    """

    file_path_dragged_and_dropped = QtCore.pyqtSignal(str)
    file_path_dragged = QtCore.pyqtSignal(bool)
    first_subwindow_was_opened = QtCore.pyqtSignal()
    last_remaining_subwindow_was_closed = QtCore.pyqtSignal()

    def __init__(self):
        super().__init__()
        
        self.setAcceptDrops(True)
        self.subWindowActivated.connect(self.subwindow_was_activated)
        self.last_tile_method = None
        self.are_there_any_subwindows_open = False
        self.most_recently_activated_subwindow = None
        self._subwindow_order = []

        self.tile_subwindows_horizontally()

    def addSubWindow(self, widget, windowFlags=QtCore.Qt.WindowFlags()):
        """Add a subwindow and track its tile order."""
        window = super().addSubWindow(widget, windowFlags)
        self._register_subwindow(window)
        return window

    def _register_subwindow(self, window):
        """Track a subwindow in the explicit tile order."""
        if window not in self._subwindow_order:
            self._subwindow_order.append(window)
            window.destroyed.connect(self._sync_subwindow_order_later)

    def _sync_subwindow_order_later(self, *_args):
        """Clean closed subwindows from the explicit tile order after Qt updates."""
        QtCore.QTimer.singleShot(0, self._sync_subwindow_order)

    def _sync_subwindow_order(self):
        """Keep the explicit tile order aligned with the live MDI subwindows."""
        live_windows = self.subWindowList()
        self._subwindow_order = [window for window in self._subwindow_order if window in live_windows]
        return live_windows

    def ordered_subwindows(self):
        """Return live subwindows in the user-controlled tile order."""
        live_windows = self._sync_subwindow_order()
        for window in live_windows:
            self._register_subwindow(window)
        return list(self._subwindow_order)

    def swap_subwindow_order(self, source_window, target_window):
        """Swap two subwindows in the user-controlled tile order."""
        windows = self.ordered_subwindows()
        if source_window not in windows or target_window not in windows or source_window == target_window:
            return False

        source_index = self._subwindow_order.index(source_window)
        target_index = self._subwindow_order.index(target_window)
        self._subwindow_order[source_index], self._subwindow_order[target_index] = (
            self._subwindow_order[target_index],
            self._subwindow_order[source_index],
        )
        self.tile_what_was_done_last_time()
        self.setActiveSubWindow(source_window)
        return True

    def tile_subwindows_vertically(self, button_input=None):
        """Arrange subwindows vertically as a single column.

        Arranges subwindows top to bottom in order of when they were added (oldest to newest).
        
        Args:
            button_input: Optional placeholder for signal compatibility.
        """
        windows = self.ordered_subwindows()
        if not windows:
            self.last_tile_method = "vertically"
            return

        position = QtCore.QPoint()
        for window in windows:
            rect = QtCore.QRect(0, 0, self.width(), self.height() // len(windows))
            window.setGeometry(rect)
            window.move(position)
            position.setY(position.y() + window.height())
        self.last_tile_method = "vertically"

    def tile_subwindows_horizontally(self, button_input=None):
        """Arrange subwindows horizontally as a single row.

        Arranges subwindows left to right in order of when they were added (oldest to newest).
        
        Args:
            button_input: Optional placeholder for signal compatibility.
        """
        windows = self.ordered_subwindows()
        if not windows:
            self.last_tile_method = "horizontally"
            return

        position = QtCore.QPoint()
        for window in windows:
            rect = QtCore.QRect(0, 0, self.width() // len(windows), self.height())
            window.setGeometry(rect)
            window.move(position)
            position.setX(position.x() + window.width())
        self.last_tile_method = "horizontally"
    
    def tileSubWindows(self, button_input=None):
        """Arrange subwindows as tiles (override).
        
        Args:
            button_input: Optional placeholder for signal compatibility.
        """
        windows = self.ordered_subwindows()
        if not windows:
            self.last_tile_method = "grid"
            return

        columns = math.ceil(math.sqrt(len(windows)))
        rows = math.ceil(len(windows) / columns)
        tile_width = self.width() // columns
        tile_height = self.height() // rows

        for index, window in enumerate(windows):
            row = index // columns
            column = index % columns
            rect = QtCore.QRect(column * tile_width, row * tile_height, tile_width, tile_height)
            if column == columns - 1:
                rect.setWidth(self.width() - rect.x())
            if row == rows - 1:
                rect.setHeight(self.height() - rect.y())
            window.setGeometry(rect)

        self.last_tile_method = "grid"

    def tile_what_was_done_last_time(self):
        """Arrange subwindows based on previous arrangement.
        
        Needed to arrange windows in the last arranged method during events like resizing.
        """
        if self.last_tile_method == "horizontally":
            self.tile_subwindows_horizontally()
        elif self.last_tile_method == "vertically":
            self.tile_subwindows_vertically()
        else:
            self.tileSubWindows()

    def dragEnterEvent(self, event):
        """event: Signal that one or more files have been dragged into the area."""
        self.file_path_dragged.emit(True)
        event.accept()

    def dragMoveEvent(self, event):
        """event: Signal that one or more files are being dragged in the area."""
        event.accept()

    def dragLeaveEvent(self, event):
        """event: Signal that one or more files have been dragged out of the area."""
        self.file_path_dragged.emit(False)
        event.accept()

    def dropEvent(self, event):
        """event: Signal that one or more files have been dropped into the area."""
        event.setDropAction(QtCore.Qt.CopyAction)

        self.file_path_dragged.emit(False)

        urls = event.mimeData().urls()

        if urls:
            for url in urls:
                file_path = url.toLocalFile()
                self.file_path_dragged_and_dropped.emit(file_path)
            event.accept()
        else:
            event.ignore()

    def subwindow_was_activated(self, window): 
        """Signal if first subwindow has been activated or if last remaining subwindow has been closed.

        Triggered when subwindow activated signal of area is emitted.
        Fixes issues with improper subwindow activation behavior.

        Args:
            window (QMdiSubWindow)
        """
        
        if not window: #  When the last remaining subwindow is closed, subWindowActivated throws Null window
            self.are_there_any_subwindows_open = False
            self.last_remaining_subwindow_was_closed.emit()
        elif not self.are_there_any_subwindows_open: # If there is indeed a window but the boolean still shows there are none open, then change the boolean
            self.are_there_any_subwindows_open = True
            self.first_subwindow_was_opened.emit()
            self.most_recently_activated_subwindow = window
        return

    def resizeEvent(self, event):
        """Override resizeEvent() to maintain horizontal and vertical arrangement of subwindows during resizing.
        
        Fixes shuffling of subwindows when area is resized in vertical and horizontal arrangements.
        """
        super().resizeEvent(event)

        if self.last_tile_method == "horizontally":
            self.tile_subwindows_horizontally()
        elif self.last_tile_method == "vertically":
            self.tile_subwindows_vertically()
        else:
            return
