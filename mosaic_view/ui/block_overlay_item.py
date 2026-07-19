"""Vector graphics item for block-level image data."""

from PyQt5 import QtCore, QtGui, QtWidgets


def jet_color(value, minimum, maximum):
    """Return a QColor from a compact jet-style scalar mapping."""
    normalized = max(0.0, min(1.0, (value - minimum) / (maximum - minimum)))
    red = max(0.0, min(1.0, 1.5 - abs(4.0 * normalized - 3.0)))
    green = max(0.0, min(1.0, 1.5 - abs(4.0 * normalized - 2.0)))
    blue = max(0.0, min(1.0, 1.5 - abs(4.0 * normalized - 1.0)))
    return QtGui.QColor(round(red * 255), round(green * 255), round(blue * 255))


class BlockOverlayRenderData:
    """Share prepared geometry, colors, and a spatial index across scene items."""

    bucket_size = 128

    def __init__(self, data):
        self.rects = tuple(
            QtCore.QRectF(block.x, block.y, block.width, block.height) for block in data.blocks
        )
        self.colors = tuple(
            jet_color(block.value, data.value_min, data.value_max) for block in data.blocks
        )
        self.labels = tuple(
            str(int(block.value)) if block.value.is_integer() else f"{block.value:g}"
            for block in data.blocks
        )
        buckets = {}
        for index, rect in enumerate(self.rects):
            left = int(rect.left()) // self.bucket_size
            right = max(int(rect.right() - 0.001), int(rect.left())) // self.bucket_size
            top = int(rect.top()) // self.bucket_size
            bottom = max(int(rect.bottom() - 0.001), int(rect.top())) // self.bucket_size
            for bucket_x in range(left, right + 1):
                for bucket_y in range(top, bottom + 1):
                    buckets.setdefault((bucket_x, bucket_y), []).append(index)
        self.buckets = {key: tuple(indices) for key, indices in buckets.items()}

    def visible_indices(self, exposed):
        """Return candidate block indexes intersecting an exposed scene rectangle."""
        left = max(0, int(exposed.left()) // self.bucket_size)
        right = max(left, int(exposed.right()) // self.bucket_size)
        top = max(0, int(exposed.top()) // self.bucket_size)
        bottom = max(top, int(exposed.bottom()) // self.bucket_size)
        indexes = set()
        for bucket_x in range(left, right + 1):
            for bucket_y in range(top, bottom + 1):
                indexes.update(self.buckets.get((bucket_x, bucket_y), ()))
        return sorted(indexes)


class BlockOverlayItem(QtWidgets.QGraphicsItem):
    """Draw all CSV blocks as one lightweight vector scene item."""

    def __init__(self, data, render_data=None):
        super().__init__()
        self.data = data
        self.render_data = render_data or BlockOverlayRenderData(data)
        self.draw_borders = True
        self.show_values = False
        self.label_color = "white"
        self.fill_opacity = 0.45
        self._bounds = QtCore.QRectF(0, 0, data.image_width, data.image_height)
        self.setZValue(10.0)

    def boundingRect(self):
        return self._bounds

    def set_draw_borders(self, enabled):
        """Show or hide block outlines."""
        enabled = bool(enabled)
        if self.draw_borders != enabled:
            self.draw_borders = enabled
            self.update()

    def set_fill_opacity(self, opacity):
        """Set fill opacity without changing the independently drawn borders."""
        opacity = max(0.0, min(1.0, float(opacity)))
        if self.fill_opacity != opacity:
            self.fill_opacity = opacity
            self.update()

    def set_show_values(self, enabled):
        """Show or hide each block's scalar value."""
        enabled = bool(enabled)
        if self.show_values != enabled:
            self.show_values = enabled
            self.update()

    def set_label_color(self, color):
        """Set block value labels to black or white."""
        color = str(color).lower()
        if color not in {"black", "white"}:
            raise ValueError("Label color must be black or white.")
        if self.label_color != color:
            self.label_color = color
            self.update()

    def paint(self, painter, option, widget=None):
        exposed = option.exposedRect
        visible_indexes = self.render_data.visible_indices(exposed)
        painter_opacity = painter.opacity()
        painter.setOpacity(painter_opacity * self.fill_opacity)
        painter.setPen(QtCore.Qt.NoPen)
        for index in visible_indexes:
            rect = self.render_data.rects[index]
            if exposed.intersects(rect):
                painter.fillRect(rect, self.render_data.colors[index])

        painter.setOpacity(painter_opacity)

        if self.draw_borders:
            pen = QtGui.QPen(QtGui.QColor(0, 0, 0, 180))
            pen.setCosmetic(True)
            pen.setWidth(1)
            painter.setPen(pen)
            painter.setBrush(QtCore.Qt.NoBrush)
            for index in visible_indexes:
                rect = self.render_data.rects[index]
                if exposed.intersects(rect):
                    painter.drawRect(rect)

        if self.show_values:
            painter.setPen(QtGui.QColor(self.label_color))
            font = painter.font()
            for index in visible_indexes:
                rect = self.render_data.rects[index]
                if not exposed.intersects(rect):
                    continue
                font.setPixelSize(max(3, round(min(rect.width(), rect.height()) * 0.38)))
                painter.setFont(font)
                painter.drawText(rect, QtCore.Qt.AlignCenter, self.render_data.labels[index])
