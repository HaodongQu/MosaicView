"""Parse block-level CSV data for image overlays."""

from dataclasses import dataclass
import csv
import os


class BlockOverlayError(ValueError):
    """Raised when a block overlay CSV cannot be parsed or validated."""


@dataclass(frozen=True)
class BlockValue:
    """A scalar value attached to a rectangular image region."""

    x: int
    y: int
    width: int
    height: int
    value: float


@dataclass(frozen=True)
class BlockOverlayData:
    """Parsed block overlay metadata and values."""

    source_path: str
    name: str
    image_width: int
    image_height: int
    value_min: float
    value_max: float
    color_map: str
    blocks: tuple


def _number(value, line_number, field_name, number_type=float):
    try:
        return number_type(value)
    except (TypeError, ValueError) as error:
        raise BlockOverlayError(
            f"Line {line_number}: invalid {field_name} value {value!r}."
        ) from error


def load_block_overlay(path):
    """Read a MosaicView block-data CSV file."""
    if not path or not os.path.isfile(path):
        raise BlockOverlayError("CSV file does not exist.")

    image_width = image_height = None
    name = "Value"
    value_min, value_max = 0.0, 1.0
    color_map = "jet"
    blocks = []

    try:
        stream = open(path, "r", encoding="utf-8-sig", newline="")
    except OSError as error:
        raise BlockOverlayError(f"Could not open CSV: {error}") from error

    with stream:
        reader = csv.reader(stream, delimiter=";")
        for line_number, row in enumerate(reader, 1):
            if not row or not any(field.strip() for field in row):
                continue
            row = [field.strip() for field in row]

            if row[0] == "%":
                key = row[1] if len(row) > 1 else ""
                if key == "seq-specs":
                    if len(row) < 6:
                        raise BlockOverlayError(f"Line {line_number}: incomplete seq-specs metadata.")
                    image_width = _number(row[4], line_number, "image width", int)
                    image_height = _number(row[5], line_number, "image height", int)
                elif key == "type" and len(row) > 3:
                    name = row[3] or name
                elif key == "defaultRange":
                    if len(row) < 5:
                        raise BlockOverlayError(f"Line {line_number}: incomplete defaultRange metadata.")
                    value_min = _number(row[2], line_number, "minimum")
                    value_max = _number(row[3], line_number, "maximum")
                    color_map = row[4] or color_map
                continue

            if len(row) < 7:
                raise BlockOverlayError(f"Line {line_number}: expected at least 7 fields.")

            x = _number(row[1], line_number, "x", int)
            y = _number(row[2], line_number, "y", int)
            width = _number(row[3], line_number, "width", int)
            height = _number(row[4], line_number, "height", int)
            value = _number(row[6], line_number, "block value")
            if x < 0 or y < 0 or width <= 0 or height <= 0:
                raise BlockOverlayError(f"Line {line_number}: invalid block rectangle.")
            blocks.append(BlockValue(x, y, width, height, value))

    if image_width is None or image_height is None:
        raise BlockOverlayError("CSV is missing seq-specs image dimensions.")
    if image_width <= 0 or image_height <= 0:
        raise BlockOverlayError("CSV image dimensions must be positive.")
    if value_max <= value_min:
        raise BlockOverlayError("CSV value range maximum must be greater than minimum.")
    if not blocks:
        raise BlockOverlayError("CSV contains no block data.")

    for block in blocks:
        if block.x + block.width > image_width or block.y + block.height > image_height:
            raise BlockOverlayError(
                f"Block at ({block.x}, {block.y}) extends beyond the declared image dimensions."
            )

    return BlockOverlayData(
        source_path=os.path.abspath(path),
        name=name,
        image_width=image_width,
        image_height=image_height,
        value_min=value_min,
        value_max=value_max,
        color_map=color_map,
        blocks=tuple(blocks),
    )
