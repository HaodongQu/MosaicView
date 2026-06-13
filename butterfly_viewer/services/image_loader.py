"""Services for loading images into viewer-ready pixmaps."""

from __future__ import annotations

from dataclasses import dataclass

from PyQt5 import QtCore, QtGui

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


def normalize_pixmap_for_difference(pixmap, target_size):
    """Scale a pixmap into a common canvas so image differences share one frame."""
    if pixmap is None or pixmap.isNull():
        return None

    canvas = QtGui.QImage(target_size, QtGui.QImage.Format_ARGB32)
    canvas.fill(QtGui.QColor(0, 0, 0, 255))

    scaled_pixmap = pixmap.scaled(
        target_size,
        QtCore.Qt.KeepAspectRatio,
        QtCore.Qt.SmoothTransformation,
    )
    painter = QtGui.QPainter(canvas)
    x = int((target_size.width() - scaled_pixmap.width()) / 2)
    y = int((target_size.height() - scaled_pixmap.height()) / 2)
    painter.drawPixmap(x, y, scaled_pixmap)
    painter.end()
    return canvas


def build_difference_pixmap(base_pixmap, compare_pixmap):
    """Return an absolute RGB difference image between the base and comparison pixmaps."""
    if base_pixmap is None or compare_pixmap is None:
        return compare_pixmap
    if base_pixmap.isNull() or compare_pixmap.isNull():
        return compare_pixmap

    target_size = base_pixmap.size()
    base_image = normalize_pixmap_for_difference(base_pixmap, target_size)
    compare_image = normalize_pixmap_for_difference(compare_pixmap, target_size)
    difference_image = QtGui.QImage(target_size, QtGui.QImage.Format_ARGB32)

    for y in range(target_size.height()):
        for x in range(target_size.width()):
            base_color = base_image.pixelColor(x, y)
            compare_color = compare_image.pixelColor(x, y)
            red = min(255, abs(compare_color.red() - base_color.red()) * 2)
            green = min(255, abs(compare_color.green() - base_color.green()) * 2)
            blue = min(255, abs(compare_color.blue() - base_color.blue()) * 2)
            difference_image.setPixelColor(x, y, QtGui.QColor(red, green, blue, 255))

    return QtGui.QPixmap.fromImage(difference_image)


def load_view_pixmaps(filename_main_topleft, filename_topright=None, filename_bottomleft=None, filename_bottomright=None, show_differences=False):
    """Load all pixmaps required for one viewer window."""
    main_pixmap = load_pixmap(filename_main_topleft)
    topright_pixmap = load_pixmap(filename_topright)
    bottomleft_pixmap = load_pixmap(filename_bottomleft)
    bottomright_pixmap = load_pixmap(filename_bottomright)

    if show_differences and main_pixmap and not main_pixmap.isNull():
        if topright_pixmap is not None:
            topright_pixmap = build_difference_pixmap(main_pixmap, topright_pixmap)
        if bottomleft_pixmap is not None:
            bottomleft_pixmap = build_difference_pixmap(main_pixmap, bottomleft_pixmap)
        if bottomright_pixmap is not None:
            bottomright_pixmap = build_difference_pixmap(main_pixmap, bottomright_pixmap)

    return LoadedViewPixmaps(
        main=main_pixmap,
        topright=topright_pixmap,
        bottomleft=bottomleft_pixmap,
        bottomright=bottomright_pixmap,
    )
