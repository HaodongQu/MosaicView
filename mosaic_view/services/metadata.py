"""Services for extracting metadata shown in the Image Stats sidebar."""

import os

from PyQt5 import QtGui

try:
    from ..domain.models import ImageMetadata, ImageSlot, ImageStatsEntry
except ImportError:
    from domain.models import ImageMetadata, ImageSlot, ImageStatsEntry


def format_file_size(num_bytes):
    """Return a human-readable file size string."""
    if num_bytes is None:
        return "N/A"
    units = ["B", "KB", "MB", "GB", "TB"]
    size = float(num_bytes)
    unit_index = 0
    while size >= 1024 and unit_index < len(units) - 1:
        size /= 1024.0
        unit_index += 1
    if unit_index == 0:
        return f"{int(size)} {units[unit_index]}"
    return f"{size:.1f} {units[unit_index]}"


def get_image_depth_and_channels(image):
    """Return total bit depth and approximate channel count for a loaded QImage."""
    if image is None or image.isNull():
        return "N/A"

    depth = image.depth()
    if image.isGrayscale():
        channels = 1
    elif image.hasAlphaChannel():
        channels = 4
    else:
        channels = 3

    return f"{depth}-bit / {channels} channel{'s' if channels != 1 else ''}"


def get_image_metadata(filepath):
    """Return metadata for a single image filepath."""
    if not filepath or not os.path.exists(filepath):
        return ImageMetadata(
            filename="N/A",
            resolution="N/A",
            depth_channels="N/A",
            file_size="N/A",
        )

    image = QtGui.QImage(filepath)
    resolution = "N/A"
    depth_channels = "N/A"
    if not image.isNull():
        resolution = f"{image.width()} x {image.height()}"
        depth_channels = get_image_depth_and_channels(image)

    return ImageMetadata(
        filename=os.path.basename(filepath),
        resolution=resolution,
        depth_channels=depth_channels,
        file_size=format_file_size(os.path.getsize(filepath)),
    )


def build_stats_entries(image_slots):
    """Convert logical image slots into sidebar entries."""
    entries = []
    for slot in image_slots:
        metadata = get_image_metadata(slot.filepath)
        entries.append(
            ImageStatsEntry(
                title=slot.title,
                filename=metadata.filename,
                resolution=metadata.resolution,
                depth_channels=metadata.depth_channels,
                file_size=metadata.file_size,
            )
        )
    return entries
