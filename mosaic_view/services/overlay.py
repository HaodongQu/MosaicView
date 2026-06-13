"""Services for overlay layout selection and image slot mapping."""

try:
    from ..domain.models import ImageSlot
except ImportError:
    from domain.models import ImageSlot


def determine_overlay_layout_mode(pixmap_topright_exists, pixmap_bottomleft_exists, pixmap_bottomright_exists):
    """Determine how overlay images should be arranged."""
    overlay_image_count = sum([pixmap_topright_exists, pixmap_bottomright_exists, pixmap_bottomleft_exists])
    if overlay_image_count <= 1:
        if pixmap_bottomleft_exists and not pixmap_topright_exists and not pixmap_bottomright_exists:
            return "top-bottom"
        return "left-right"
    return "quad"


def build_image_slots_for_view(child):
    """Return logical image slots for the current child view."""
    image_slots = [ImageSlot("Base image", child.filename_main_topleft)]

    if child.overlay_layout_mode == "left-right":
        overlay_path = child.filename_topright or child.filename_bottomright
        if overlay_path:
            image_slots.append(ImageSlot("Right image", overlay_path))
    elif child.overlay_layout_mode == "top-bottom":
        overlay_path = child.filename_bottomleft or child.filename_bottomright
        if overlay_path:
            image_slots.append(ImageSlot("Bottom image", overlay_path))
    else:
        if child.filename_topright:
            image_slots.append(ImageSlot("Right image", child.filename_topright))
        if child.filename_bottomleft:
            image_slots.append(ImageSlot("Bottom image", child.filename_bottomleft))
        if child.filename_bottomright:
            image_slots.append(ImageSlot("Extra image", child.filename_bottomright))

    return image_slots
