#!/usr/bin/env python3

"""User interface widgets and their supporting subwidgets for Butterfly Viewer.

Not intended as a script.

Interface widgets are:
    SplitViewCreator, for users to add images in a 2x2 drag-and-drop zone from which to create a sliding overlay.
"""
# SPDX-License-Identifier: GPL-3.0-or-later



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



class SplitViewCreator(QtWidgets.QFrame):
    """Interface for users to add images from which to create a SplitView.
    
    Users can add local image files via drag-and-drop and "Select image..." dialogs.

    Instantiate without input. See Butterfly Viewer for implementation.
    """
    
    clicked_create_splitview_pushbutton = QtCore.pyqtSignal()

    def __init__(self):
        super().__init__()  
        
        main_layout = QtWidgets.QGridLayout()
        
        self.drag_drop_area = FourDragDropImageLabelForSplitView()
        self.drag_drop_area.will_start_loading.connect(self.display_loading_grayout)
        self.drag_drop_area.has_stopped_loading.connect(self.display_loading_grayout)
        
        self.buttons_layout = QtWidgets.QBoxLayout(QtWidgets.QBoxLayout.LeftToRight)
        self.create_splitview_pushbutton = QtWidgets.QPushButton("Create")
        self.create_splitview_pushbutton.setToolTip("Create a sliding overlay window with these images")
        self.create_splitview_pushbutton.setStyleSheet("QPushButton { font-size: 10pt; }")
        self.create_splitview_pushbutton.clicked.connect(self.clicked_create_splitview_pushbutton)

        self.create_splitview_pushbutton.setEnabled(False)
        self.drag_drop_area.main_became_occupied.connect(self.create_splitview_pushbutton.setEnabled)
        
        self.buttons_layout.addWidget(self.create_splitview_pushbutton)

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

        self.title_label = QtWidgets.QLabel("Sliding overlay creator")
        self.title_label.setAlignment(QtCore.Qt.AlignLeft)
        self.title_label.setStyleSheet("""
            QLabel { 
                font-size: 10pt;
                } 
            """)

        self.mode_help_label = QtWidgets.QLabel(
            "Base + right image = left-right\n"
            "Base + bottom image = top-bottom\n"
            "3 to 4 images = quad"
        )
        self.mode_help_label.setAlignment(QtCore.Qt.AlignLeft)
        self.mode_help_label.setStyleSheet("""
            QLabel {
                color: palette(mid);
                font-size: 8.5pt;
            }
        """)
        
        main_layout.addWidget(self.title_label,0,0)
        main_layout.addWidget(self.mode_help_label, 1, 0)
        main_layout.addWidget(self.drag_drop_area, 2, 0)
        main_layout.addLayout(self.buttons_layout, 3, 0)
        main_layout.addWidget(self.loading_grayout_label, 0, 0, 4, 1)
        main_layout.setAlignment(QtCore.Qt.AlignTop)
        main_layout.setContentsMargins(4,4,4,4)
        
        # self.setMinimumWidth(250)
        # self.setMinimumHeight(325)
        
        self.setLayout(main_layout)
        self.setContentsMargins(2,2,2,2) # As docked on left side
        
        self.setStyleSheet("QFrame {background: palette(window); border-radius: 0.5em;}")

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

        self.title_label = QtWidgets.QLabel("Image Stats")
        self.title_label.setStyleSheet("QLabel { font-size: 10pt; font-weight: bold; }")

        self.view_title_label = QtWidgets.QLabel("View")
        self.view_title_label.setStyleSheet("QLabel { font-size: 9pt; font-weight: bold; }")

        self.view_form_layout = QtWidgets.QFormLayout()
        self.view_form_layout.setContentsMargins(0, 0, 0, 0)
        self.view_form_layout.setSpacing(8)

        self.value_zoom = self.create_value_label()
        self.value_mouse = self.create_value_label()

        self.view_form_layout.addRow("Zoom", self.value_zoom)
        self.view_form_layout.addRow("Mouse pixel", self.value_mouse)

        self.view_frame = QtWidgets.QFrame()
        self.view_frame.setStyleSheet("QFrame { background: rgba(255, 255, 255, 0.03); border-radius: 0.45em; }")
        view_layout = QtWidgets.QVBoxLayout()
        view_layout.setContentsMargins(10, 10, 10, 10)
        view_layout.setSpacing(8)
        view_layout.addWidget(self.view_title_label)
        view_layout.addLayout(self.view_form_layout)
        self.view_frame.setLayout(view_layout)

        self.images_title_label = QtWidgets.QLabel("Images")
        self.images_title_label.setStyleSheet("QLabel { font-size: 9pt; font-weight: bold; }")

        self.images_container = QtWidgets.QWidget()
        self.images_layout = QtWidgets.QVBoxLayout()
        self.images_layout.setContentsMargins(0, 0, 0, 0)
        self.images_layout.setSpacing(10)
        self.images_container.setLayout(self.images_layout)

        layout = QtWidgets.QVBoxLayout()
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)
        layout.addWidget(self.title_label)
        layout.addWidget(self.view_frame)
        layout.addWidget(self.images_title_label)
        layout.addWidget(self.images_container)
        layout.addStretch(1)

        self.setLayout(layout)
        self.setStyleSheet("QFrame {background: palette(window); border-radius: 0.5em;}")

        self.reset()

    def create_value_label(self):
        """Create a word-wrapped value label."""
        label = QtWidgets.QLabel("N/A")
        label.setWordWrap(True)
        label.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)
        return label

    def reset(self):
        """Reset all displayed values."""
        self.set_zoom()
        self.set_mouse_position()
        self.set_images([])

    def set_zoom(self, zoom_text="N/A"):
        """Update zoom value."""
        self.value_zoom.setText(zoom_text)

    def set_mouse_position(self, mouse_text="( N/A , N/A )"):
        """Update mouse pixel coordinate display."""
        self.value_mouse.setText(mouse_text)

    def clear_images(self):
        """Remove all image cards from the panel."""
        while self.images_layout.count():
            item = self.images_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

    def create_image_card(self, image_info):
        """Create a metadata card for one image slot."""
        frame = QtWidgets.QFrame()
        frame.setStyleSheet("QFrame { background: rgba(255, 255, 255, 0.03); border-radius: 0.45em; }")

        title_label = QtWidgets.QLabel(image_info.get("title", "Image"))
        title_label.setStyleSheet("QLabel { font-size: 9pt; font-weight: bold; }")

        form_layout = QtWidgets.QFormLayout()
        form_layout.setContentsMargins(0, 0, 0, 0)
        form_layout.setSpacing(6)

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

        frame_layout = QtWidgets.QVBoxLayout()
        frame_layout.setContentsMargins(10, 10, 10, 10)
        frame_layout.setSpacing(8)
        frame_layout.addWidget(title_label)
        frame_layout.addLayout(form_layout)
        frame.setLayout(frame_layout)

        return frame

    def set_images(self, image_entries):
        """Replace the image metadata list with the images from the active view."""
        self.clear_images()

        if not image_entries:
            empty_label = self.create_value_label()
            empty_label.setText("No active image")
            self.images_layout.addWidget(empty_label)
            return

        for image_info in image_entries:
            self.images_layout.addWidget(self.create_image_card(image_info))
