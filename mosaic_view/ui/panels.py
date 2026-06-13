#!/usr/bin/env python3

"""User interface widgets and their supporting subwidgets for MosaicView.

Not intended as a script.

Interface widgets are:
    SplitViewCreator, for users to add images in a 2x2 drag-and-drop zone from which to create a sliding overlay.
"""
# SPDX-License-Identifier: GPL-3.0-or-later



import os
import time

from PyQt5 import QtWidgets, QtCore

try:
    from ..aux_dragdrop import FourDragDropImageLabel
except ImportError:
    from aux_dragdrop import FourDragDropImageLabel



class FourDragDropImageLabelForSplitView(FourDragDropImageLabel):
    """Extends a 2x2 drag-and-drop zone for SplitViewCreator.
    
    Requires a base image (main; top-left) to be given before other images of SplitView may be added.

    Instantiate without input:
        self.drag_drop_area = FourDragDropImageLabelForSplitView()
    """

    main_became_occupied = QtCore.pyqtSignal(bool)

    def __init__(self):
        super().__init__()
        self.set_addable_all_except_main(False)
        self.app_main_topleft.became_occupied.connect(self.on_main_topleft_occupied)
        self.app_main_topleft.became_occupied.connect(self.main_became_occupied)

        for image_slot in (
            self.app_main_topleft,
            self.app_topright,
            self.app_bottomleft,
            self.app_bottomright,
        ):
            image_slot.set_open_button_visible(False)


    # Set style and function of drag-and-drop zones

    def set_addable_all_except_main(self, boolean):
        """Set all overlay images to be (or not to be) addable via drag-and-drop.

        Convenience for the SplitViewCreator.

        Args:
            boolean (bool): True to make the overlay images addable; False to make un-addable.
        """
        self.app_topright.set_addable(boolean)
        self.app_bottomright.set_addable(boolean)
        self.app_bottomleft.set_addable(boolean)

    def on_main_topleft_occupied(self, boolean):
        """Set when base image becomes occupied or unoccupied to set whether overlay images can be added.
        
        Args:
            boolean (bool): True to indicate base image is occupied (and thus overlay images may be added); 
             False to indicate main image is unoccupied (and thus overlay images may not be added)."""
        self.set_addable_all_except_main(boolean)

    def clear_images(self):
        """Clear all image slots in the sliding overlay creator."""
        for image_slot in (
            self.app_main_topleft,
            self.app_topright,
            self.app_bottomleft,
            self.app_bottomright,
        ):
            image_slot.clear_image()

class SplitViewCreator(QtWidgets.QFrame):
    """Interface for users to add images from which to create a SplitView.
    
    Users can add local image files via drag-and-drop and "Select image..." dialogs.

    Instantiate without input. See MosaicView for implementation.
    """
    
    clicked_create_splitview_pushbutton = QtCore.pyqtSignal()

    def __init__(self):
        super().__init__()  
        self.setObjectName("splitViewCreatorPanel")
        
        main_layout = QtWidgets.QGridLayout()
        
        self.drag_drop_area = FourDragDropImageLabelForSplitView()
        self.drag_drop_area.will_start_loading.connect(self.display_loading_grayout)
        self.drag_drop_area.has_stopped_loading.connect(self.display_loading_grayout)
        
        self.buttons_layout = QtWidgets.QBoxLayout(QtWidgets.QBoxLayout.LeftToRight)
        self.create_splitview_pushbutton = QtWidgets.QPushButton("Create Overlay")
        self.create_splitview_pushbutton.setToolTip("Create a sliding overlay window with these images")
        self.create_splitview_pushbutton.setStyleSheet("""
            QPushButton {
                font-size: 10pt;
                font-weight: bold;
                padding: 0.5em 0.8em;
            }
        """)
        self.create_splitview_pushbutton.clicked.connect(self.clicked_create_splitview_pushbutton)

        self.create_splitview_pushbutton.setEnabled(False)
        self.drag_drop_area.main_became_occupied.connect(self.create_splitview_pushbutton.setEnabled)

        self.clear_pushbutton = QtWidgets.QPushButton("Clear")
        self.clear_pushbutton.setToolTip("Clear all images from the sliding overlay creator")
        self.clear_pushbutton.setEnabled(False)
        self.clear_pushbutton.clicked.connect(self.drag_drop_area.clear_images)

        for image_slot in (
            self.drag_drop_area.app_main_topleft,
            self.drag_drop_area.app_topright,
            self.drag_drop_area.app_bottomleft,
            self.drag_drop_area.app_bottomright,
        ):
            image_slot.became_occupied.connect(self.update_clear_pushbutton)
        
        self.buttons_layout.addWidget(self.create_splitview_pushbutton)
        self.buttons_layout.addWidget(self.clear_pushbutton)

        self.loading_grayout_label = QtWidgets.QLabel("Loading...")
        self.loading_grayout_label.setAlignment(QtCore.Qt.AlignCenter | QtCore.Qt.AlignVCenter)
        self.loading_grayout_label.setVisible(False)
        self.loading_grayout_label.setStyleSheet("""
            QLabel { 
                color: white;
                font-size: 7.5pt;
                background-color: rgba(0,0,0,223);
                } 
            """)

        self.title_label = QtWidgets.QLabel("Sliding Overlay Creator")
        self.title_label.setAlignment(QtCore.Qt.AlignLeft)
        self.title_label.setStyleSheet("""
            QLabel { 
                font-size: 11pt;
                font-weight: bold;
                } 
            """)

        self.drag_drop_frame = QtWidgets.QFrame()
        self.drag_drop_frame.setObjectName("splitViewCreatorDropFrame")
        self.drag_drop_frame.setStyleSheet("""
            QFrame#splitViewCreatorDropFrame {
                background: rgba(255, 255, 255, 0.03);
                border: 1px solid palette(mid);
                border-radius: 0.55em;
            }
        """)
        drag_drop_frame_layout = QtWidgets.QVBoxLayout()
        drag_drop_frame_layout.setContentsMargins(8, 8, 8, 8)
        drag_drop_frame_layout.addWidget(self.drag_drop_area)
        self.drag_drop_frame.setLayout(drag_drop_frame_layout)

        self.show_differences_checkbox = QtWidgets.QCheckBox("Show Differences")
        self.show_differences_checkbox.setToolTip("Create the overlay with difference images against the base image")
        
        main_layout.addWidget(self.title_label,0,0)
        main_layout.addWidget(self.drag_drop_frame, 1, 0)
        main_layout.addWidget(self.show_differences_checkbox, 2, 0)
        main_layout.addLayout(self.buttons_layout, 3, 0)
        main_layout.addWidget(self.loading_grayout_label, 0, 0, 4, 1)
        main_layout.setAlignment(QtCore.Qt.AlignTop)
        main_layout.setContentsMargins(14, 14, 14, 14)
        main_layout.setVerticalSpacing(10)
        
        # self.setMinimumWidth(250)
        # self.setMinimumHeight(325)
        
        self.setLayout(main_layout)
        self.setContentsMargins(2,2,2,2) # As docked on left side
        
        self.setStyleSheet("""
            QFrame#splitViewCreatorPanel {
                background: palette(base);
                border: 1px solid palette(mid);
                border-radius: 0.7em;
            }
        """)

    @property
    def show_differences_in_overlay(self):
        """Whether new overlays should render non-base images as differences to the base image."""
        return self.show_differences_checkbox.isChecked()

    def update_clear_pushbutton(self, _occupied=None):
        """Enable clearing whenever the creator contains at least one image."""
        image_slots = (
            self.drag_drop_area.app_main_topleft,
            self.drag_drop_area.app_topright,
            self.drag_drop_area.app_bottomleft,
            self.drag_drop_area.app_bottomright,
        )
        self.clear_pushbutton.setEnabled(
            any(image_slot.image_label_child.IS_OCCUPIED for image_slot in image_slots)
        )

    def setMouseTracking(self, flag):
        """PyQt flag: Override mouse tracking to set mouse tracking for all children widgets."""
        def recursive_set(parent):
            for child in parent.findChildren(QtCore.QObject): # Needed to track the split in sliding overlays while hovering over interfaces and other widgets; prevents sudden stops and jumps of the split
                try:
                    child.setMouseTracking(flag)
                except:
                    pass
                recursive_set(child)
        QtWidgets.QWidget.setMouseTracking(self, flag)
        recursive_set(self)

    def display_loading_grayout(self, boolean, text="Loading...", pseudo_load_time=0.2): 
        """Show/hide grayout screen for loading sequences.

        Args:
            boolean (bool): True to show grayout; False to hide.
            text (str): The text to show on the grayout.
            pseudo_load_time (float): The delay (in seconds) to hide the grayout to give users a feeling of action.
        """ 
        # Needed to give feedback to user that images are loading
        if not boolean:
            text = "Loading..."
        self.loading_grayout_label.setText(text)
        self.loading_grayout_label.setVisible(boolean)
        if boolean:
            self.loading_grayout_label.repaint()
        if not boolean:
            time.sleep(pseudo_load_time)


class ImageStatsPanel(QtWidgets.QFrame):
    """Sidebar panel for live view stats and metadata of all images in the active view."""

    def __init__(self):
        super().__init__()
        self.setObjectName("imageStatsPanel")

        self.title_label = QtWidgets.QLabel("Image Stats")
        self.title_label.setStyleSheet("QLabel { font-size: 11pt; font-weight: bold; }")

        self.view_title_label = QtWidgets.QLabel("View Summary")
        self.view_title_label.setStyleSheet("QLabel { font-size: 9pt; font-weight: bold; }")

        self.value_zoom = self.create_metric_card("Zoom")
        self.value_mouse = self.create_metric_card("Mouse Pixel")

        self.view_frame = QtWidgets.QFrame()
        self.view_frame.setStyleSheet("QFrame { background: rgba(255, 255, 255, 0.03); border-radius: 0.55em; }")
        view_layout = QtWidgets.QVBoxLayout()
        view_layout.setContentsMargins(10, 10, 10, 10)
        view_layout.setSpacing(10)
        view_layout.addWidget(self.view_title_label)
        view_metrics_layout = QtWidgets.QGridLayout()
        view_metrics_layout.setContentsMargins(0, 0, 0, 0)
        view_metrics_layout.setHorizontalSpacing(8)
        view_metrics_layout.setVerticalSpacing(8)
        view_metrics_layout.addWidget(self.value_zoom, 0, 0)
        view_metrics_layout.addWidget(self.value_mouse, 0, 1)
        view_layout.addLayout(view_metrics_layout)
        self.view_frame.setLayout(view_layout)

        self.images_title_label = QtWidgets.QLabel("Images")
        self.images_title_label.setStyleSheet("QLabel { font-size: 9pt; font-weight: bold; }")

        self.images_tab_widget = QtWidgets.QTabWidget()
        self.images_tab_widget.setDocumentMode(True)
        self.images_tab_widget.setMovable(False)
        self.images_tab_widget.setElideMode(QtCore.Qt.ElideRight)
        self.images_tab_widget.setUsesScrollButtons(True)
        self.images_tab_widget.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid palette(mid);
                border-radius: 0.55em;
                background: rgba(255, 255, 255, 0.03);
                top: -1px;
            }
            QTabBar::tab {
                padding: 0.45em 0.8em;
                margin-right: 0.2em;
            }
        """)

        layout = QtWidgets.QVBoxLayout()
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)
        layout.addWidget(self.title_label)
        layout.addWidget(self.view_frame)
        layout.addWidget(self.images_title_label)
        layout.addWidget(self.images_tab_widget)
        layout.addStretch(1)

        self.setLayout(layout)
        self.setStyleSheet("""
            QFrame#imageStatsPanel {
                background: palette(base);
                border: 1px solid palette(mid);
                border-radius: 0.7em;
            }
        """)

        self.reset()

    def create_value_label(self):
        """Create a word-wrapped value label."""
        label = QtWidgets.QLabel("N/A")
        label.setWordWrap(True)
        label.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)
        return label

    def create_metric_card(self, label_text):
        """Create a compact summary tile for one live view metric."""
        frame = QtWidgets.QFrame()
        frame.setStyleSheet("QFrame { background: rgba(255, 255, 255, 0.04); border-radius: 0.45em; }")

        label = QtWidgets.QLabel(label_text)
        label.setStyleSheet("QLabel { color: palette(mid); font-size: 8pt; font-weight: bold; }")

        value = self.create_value_label()
        value.setStyleSheet("QLabel { font-size: 9.5pt; font-weight: bold; }")

        layout = QtWidgets.QVBoxLayout()
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(4)
        layout.addWidget(label)
        layout.addWidget(value)
        frame.setLayout(layout)
        frame.value_label = value
        return frame

    def reset(self):
        """Reset all displayed values."""
        self.set_zoom()
        self.set_mouse_position()
        self.set_images([])

    def set_zoom(self, zoom_text="N/A"):
        """Update zoom value."""
        self.value_zoom.value_label.setText(zoom_text)

    def set_mouse_position(self, mouse_text="( N/A , N/A )"):
        """Update mouse pixel coordinate display."""
        self.value_mouse.value_label.setText(mouse_text)

    def clear_images(self):
        """Remove all image tabs from the panel."""
        while self.images_tab_widget.count():
            widget = self.images_tab_widget.widget(0)
            self.images_tab_widget.removeTab(0)
            if widget is not None:
                widget.deleteLater()

    def create_image_tab(self, image_info):
        """Create a metadata tab for one image slot."""
        page = QtWidgets.QWidget()

        title_label = QtWidgets.QLabel(image_info.get("title", "Image"))
        title_label.setStyleSheet("QLabel { font-size: 9.5pt; font-weight: bold; }")

        form_layout = QtWidgets.QFormLayout()
        form_layout.setContentsMargins(0, 0, 0, 0)
        form_layout.setSpacing(8)

        value_filename = self.create_value_label()
        value_resolution = self.create_value_label()
        value_depth_channels = self.create_value_label()
        value_file_size = self.create_value_label()

        value_filename.setText(image_info.get("filename", "N/A"))
        value_resolution.setText(image_info.get("resolution", "N/A"))
        value_depth_channels.setText(image_info.get("depth_channels", "N/A"))
        value_file_size.setText(image_info.get("file_size", "N/A"))

        form_layout.addRow("Filename", value_filename)
        form_layout.addRow("Resolution", value_resolution)
        form_layout.addRow("Bit depth / channels", value_depth_channels)
        form_layout.addRow("File size", value_file_size)

        layout = QtWidgets.QVBoxLayout()
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)
        layout.addWidget(title_label)
        layout.addLayout(form_layout)
        layout.addStretch(1)
        page.setLayout(layout)

        return page

    def tab_label_for_image(self, image_info):
        """Return a short tab label for one image entry."""
        title = image_info.get("title", "Image")
        replacements = {
            "Base image": "Base",
            "Right image": "Right",
            "Bottom image": "Bottom",
            "Extra image": "Extra",
        }
        return replacements.get(title, title)

    def set_images(self, image_entries):
        """Replace the image metadata tabs with the images from the active view."""
        self.clear_images()

        if not image_entries:
            empty_page = QtWidgets.QWidget()
            empty_label = self.create_value_label()
            empty_label.setText("No active image")
            empty_label.setAlignment(QtCore.Qt.AlignCenter)
            layout = QtWidgets.QVBoxLayout()
            layout.setContentsMargins(12, 12, 12, 12)
            layout.addWidget(empty_label, alignment=QtCore.Qt.AlignCenter)
            empty_page.setLayout(layout)
            self.images_tab_widget.addTab(empty_page, "Empty")
            return

        for image_info in image_entries:
            self.images_tab_widget.addTab(
                self.create_image_tab(image_info),
                self.tab_label_for_image(image_info),
            )


class FileBrowserPanel(QtWidgets.QFrame):
    """Compact in-app file browser for navigating folders and opening images."""

    file_activated = QtCore.pyqtSignal(str)

    def __init__(self, root_path=None):
        super().__init__()
        self.setObjectName("fileBrowserPanel")

        self._root_path = ""

        self.title_label = QtWidgets.QLabel("File Browser")
        self.title_label.setStyleSheet("QLabel { font-size: 10pt; font-weight: bold; }")

        self.subtitle_label = QtWidgets.QLabel("Double-click a folder to enter it. Double-click an image to open it. Drag one or more images into the sliding overlay creator.")
        self.subtitle_label.setWordWrap(True)
        self.subtitle_label.setStyleSheet("QLabel { color: palette(mid); font-size: 8.5pt; }")

        self.path_label = QtWidgets.QLabel()
        self.path_label.setWordWrap(True)
        self.path_label.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)
        self.path_label.setStyleSheet("QLabel { color: palette(text); background: rgba(255, 255, 255, 0.03); border-radius: 0.35em; padding: 0.45em 0.6em; }")

        self.up_button = QtWidgets.QPushButton("Up")
        self.up_button.clicked.connect(self.go_to_parent_directory)

        self.home_button = QtWidgets.QPushButton("Home")
        self.home_button.clicked.connect(self.go_to_home_directory)

        self.choose_folder_button = QtWidgets.QPushButton("Choose Folder...")
        self.choose_folder_button.clicked.connect(self.choose_directory)

        button_layout = QtWidgets.QHBoxLayout()
        button_layout.setContentsMargins(0, 0, 0, 0)
        button_layout.setSpacing(8)
        button_layout.addWidget(self.up_button)
        button_layout.addWidget(self.home_button)
        button_layout.addWidget(self.choose_folder_button, 1)

        self.file_model = QtWidgets.QFileSystemModel(self)
        self.file_model.setFilter(QtCore.QDir.AllDirs | QtCore.QDir.Files | QtCore.QDir.NoDotAndDotDot)

        self.tree_view = QtWidgets.QTreeView()
        self.tree_view.setModel(self.file_model)
        self.tree_view.setHeaderHidden(True)
        self.tree_view.setRootIsDecorated(False)
        self.tree_view.setItemsExpandable(False)
        self.tree_view.setAllColumnsShowFocus(True)
        self.tree_view.setAlternatingRowColors(True)
        self.tree_view.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.tree_view.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        self.tree_view.setDragEnabled(True)
        self.tree_view.setDragDropMode(QtWidgets.QAbstractItemView.DragOnly)
        self.tree_view.setDefaultDropAction(QtCore.Qt.CopyAction)
        self.tree_view.setSortingEnabled(True)
        self.tree_view.sortByColumn(0, QtCore.Qt.AscendingOrder)
        self.tree_view.activated.connect(self.on_item_activated)
        for column in range(1, self.file_model.columnCount()):
            self.tree_view.hideColumn(column)

        layout = QtWidgets.QVBoxLayout()
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)
        layout.addWidget(self.title_label)
        layout.addWidget(self.subtitle_label)
        layout.addWidget(self.path_label)
        layout.addLayout(button_layout)
        layout.addWidget(self.tree_view, 1)
        self.setLayout(layout)
        self.setStyleSheet("QFrame#fileBrowserPanel { background: palette(window); border-radius: 0.5em; }")

        self.set_root_path(root_path or QtCore.QDir.currentPath())

    @property
    def root_path(self):
        """Current root directory shown by the browser."""
        return self._root_path

    def set_root_path(self, path):
        """Set the directory displayed by the browser."""
        if not path:
            path = QtCore.QDir.currentPath()

        normalized_path = os.path.abspath(path)
        if os.path.isfile(normalized_path):
            normalized_path = os.path.dirname(normalized_path)
        if not os.path.isdir(normalized_path):
            normalized_path = QtCore.QDir.currentPath()

        self._root_path = normalized_path
        self.path_label.setText(normalized_path)
        root_index = self.file_model.setRootPath(normalized_path)
        self.tree_view.setRootIndex(root_index)

    def focus_path(self, path):
        """Show the directory of a file and select it when possible."""
        if not path:
            return

        self.set_root_path(path)
        if os.path.isdir(path):
            return

        index = self.file_model.index(os.path.abspath(path))
        if index.isValid():
            self.tree_view.setCurrentIndex(index)
            self.tree_view.scrollTo(index, QtWidgets.QAbstractItemView.PositionAtCenter)

    def choose_directory(self):
        """Open a folder picker and switch the browser root."""
        folder = QtWidgets.QFileDialog.getExistingDirectory(self, "Select folder", self.root_path)
        if folder:
            self.set_root_path(folder)

    def go_to_parent_directory(self):
        """Navigate to the current root's parent directory."""
        parent_directory = QtCore.QFileInfo(self.root_path).dir().absolutePath()
        if parent_directory and parent_directory != self.root_path:
            self.set_root_path(parent_directory)

    def go_to_home_directory(self):
        """Navigate to the user's home directory."""
        self.set_root_path(QtCore.QDir.homePath())

    def on_item_activated(self, index):
        """Enter folders or emit the chosen file path."""
        if not index.isValid():
            return

        path = self.file_model.filePath(index)
        if self.file_model.isDir(index):
            self.set_root_path(path)
            return

        self.file_activated.emit(path)
