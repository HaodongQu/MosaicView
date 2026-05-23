"""Services for loading images into viewer-ready pixmaps."""

from __future__ import annotations

from dataclasses import dataclass

from PyQt5 import QtGui

try:
    from ..aux_exif import get_exif_rotation_angle
except ImportError:
    from aux_exif import get_exif_rotation_angle


@dataclass(frozen=True)
class LoadedViewPixmaps:
    """Prepared pixmaps for one comparison view."""

    main: QtGui.QPixmap
    topright: QtGui.QPixmap | None
    bottomleft: QtGui.QPixmap | None
    bottomright: QtGui.QPixmap | None


def load_pixmap(filepath):
    """Load a pixmap and apply EXIF-based rotation when needed."""
    if not filepath:
        return None

    pixmap = QtGui.QPixmap(filepath)
    if not pixmap or pixmap.width() == 0 or pixmap.height() == 0:
        return pixmap

    angle = get_exif_rotation_angle(filepath)
    if angle:
        pixmap = pixmap.transformed(QtGui.QTransform().rotate(angle))
    return pixmap


def load_view_pixmaps(filename_main_topleft, filename_topright=None, filename_bottomleft=None, filename_bottomright=None):
    """Load all pixmaps required for one viewer window."""
    return LoadedViewPixmaps(
        main=load_pixmap(filename_main_topleft),
        topright=load_pixmap(filename_topright),
        bottomleft=load_pixmap(filename_bottomleft),
        bottomright=load_pixmap(filename_bottomright),
    )
