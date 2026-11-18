"""Vector icons for the Results Review toolbars.

Every glyph is drawn with QPainter on a 24x24 design grid instead of being
cropped from a screenshot, so the buttons stay crisp at any full screen scale.
"""

from __future__ import annotations

import math

from ...qt_compat import (
    QColor,
    QIcon,
    QPainter,
    QPainterPath,
    QPen,
    QPixmap,
    QPointF,
    QRectF,
    Qt,
)

DESIGN = 24.0

DARK = "#24313f"
BLUE = "#2d6fb5"
LIGHT_BLUE = "#d8e8f6"
GREEN = "#2f9d3a"
LIGHT_GREEN = "#dff0dd"
RED = "#c62b2b"
LIGHT_RED = "#f8dede"
AMBER = "#d79b18"
LIGHT_AMBER = "#f7e6bd"
GREY = "#6b7076"
LIGHT_GREY = "#eceae4"
PAPER = "#fbfaf6"
STEEL = "#8fa3b4"


def _pen(color, width=1.5):
    return QPen(QColor(color), width, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)


def _line(painter, x1, y1, x2, y2):
    """QPainter only accepts ints or QPointF; keep float math Python-side."""
    painter.drawLine(QPointF(float(x1), float(y1)), QPointF(float(x2), float(y2)))


def _arc(painter, rect, start, span):
    path = QPainterPath()
    path.arcMoveTo(rect, start)
    path.arcTo(rect, start, span)
    painter.drawPath(path)


def _arrow(painter, points, color):
    painter.setPen(Qt.NoPen)
    painter.setBrush(QColor(color))
    path = QPainterPath()
    path.moveTo(*points[0])
    for point in points[1:]:
        path.lineTo(*point)
    path.closeSubpath()
    painter.drawPath(path)


def _send_arrow(painter, color=BLUE):
    """Small arrow in the upper right corner that marks a transfer action."""
    painter.setPen(QPen(QColor(color), 1.8, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
    painter.setBrush(Qt.NoBrush)
    _line(painter, 13.5, 10.0, 20.0, 3.5)
    _arrow(painter, [(15.0, 3.5), (20.5, 3.0), (20.0, 8.5)], color)


def _lens(painter, cx=10.0, cy=10.0, radius=6.4, color=GREY):
    painter.setPen(QPen(QColor(color), 2.0, Qt.SolidLine, Qt.RoundCap))
    painter.setBrush(Qt.NoBrush)
    painter.drawEllipse(QRectF(cx - radius, cy - radius, radius * 2, radius * 2))
    painter.setPen(QPen(QColor(color), 2.4, Qt.SolidLine, Qt.RoundCap))
    _line(painter, cx + radius * 0.72, cy + radius * 0.72, cx + radius * 1.62, cy + radius * 1.62)


def _document(painter, fill=PAPER, border=GREY):
    painter.setPen(_pen(border, 1.4))
    painter.setBrush(QColor(fill))
    path = QPainterPath()
    path.moveTo(6.0, 3.0)
    path.lineTo(14.5, 3.0)
    path.lineTo(18.5, 7.0)
    path.lineTo(18.5, 20.5)
    path.lineTo(6.0, 20.5)
    path.closeSubpath()
    painter.drawPath(path)
    painter.setPen(_pen(border, 1.1))
    _line(painter, 9.0, 8.0, 15.5, 8.0)
    _line(painter, 9.0, 11.0, 15.5, 11.0)
    _line(painter, 9.0, 14.0, 13.0, 14.0)


def _check(painter, color=GREEN, width=2.2):
    painter.setPen(QPen(QColor(color), width, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
    painter.setBrush(Qt.NoBrush)
    _line(painter, 11.0, 15.5, 13.6, 18.3)
    _line(painter, 13.6, 18.3, 19.5, 10.8)


def _gear(painter, cx=12.0, cy=12.0, color=STEEL, teeth=8, outer=9.2, inner=4.0):
    painter.save()
    painter.translate(cx, cy)
    painter.setPen(Qt.NoPen)
    painter.setBrush(QColor(color))
    for index in range(teeth):
        painter.save()
        painter.rotate(index * (360.0 / teeth))
        painter.drawRoundedRect(QRectF(-1.7, -outer - 1.3, 3.4, 4.6), 1.1, 1.1)
        painter.restore()
    painter.drawEllipse(QRectF(-outer + 1.6, -outer + 1.6, (outer - 1.6) * 2, (outer - 1.6) * 2))
    painter.setBrush(QColor(PAPER))
    painter.drawEllipse(QRectF(-inner, -inner, inner * 2, inner * 2))
    painter.restore()


def _funnel(painter):
    painter.setPen(_pen(GREY, 1.4))
    painter.setBrush(QColor(LIGHT_GREY))
    path = QPainterPath()
    path.moveTo(3.5, 4.0)
    path.lineTo(17.5, 4.0)
    path.lineTo(12.5, 11.0)
    path.lineTo(12.5, 18.0)
    path.lineTo(8.5, 20.0)
    path.lineTo(8.5, 11.0)
    path.closeSubpath()
    painter.drawPath(path)


def _plus(painter, center=(17.0, 16.0), size=4.2, color=GREEN):
    painter.setPen(QPen(QColor(color), 2.2, Qt.SolidLine, Qt.RoundCap))
    cx, cy = center
    _line(painter, cx - size, cy, cx + size, cy)
    _line(painter, cx, cy - size, cx, cy + size)


def _minus(painter, center=(17.0, 16.0), size=4.2, color=RED):
    painter.setPen(QPen(QColor(color), 2.2, Qt.SolidLine, Qt.RoundCap))
    cx, cy = center
    _line(painter, cx - size, cy, cx + size, cy)


def _wafer(painter, cx=11.0, cy=11.0, radius=6.4, color=STEEL):
    painter.setPen(_pen(DARK, 1.5))
    painter.setBrush(QColor("#c9d3da"))
    painter.drawEllipse(QRectF(cx - radius, cy - radius, radius * 2, radius * 2))
    painter.setPen(QPen(QColor(color), 1.0))
    painter.setBrush(Qt.NoBrush)
    painter.drawEllipse(QRectF(cx - radius * 0.6, cy - radius * 0.6, radius * 1.2, radius * 1.2))
    _line(painter, cx, cy - radius, cx, cy + radius)


def _picture(painter, rect=(4.0, 6.0, 14.0, 11.0)):
    x, y, w, h = rect
    painter.setPen(_pen(GREY, 1.3))
    painter.setBrush(QColor(LIGHT_BLUE))
    painter.drawRoundedRect(QRectF(x, y, w, h), 1.4, 1.4)
    painter.setPen(QPen(QColor(AMBER), 2.0))
    painter.setBrush(QColor(AMBER))
    painter.drawEllipse(QRectF(x + w - 4.6, y + 1.6, 2.8, 2.8))
    painter.setPen(_pen(GREEN, 1.4))
    painter.setBrush(QColor(LIGHT_GREEN))
    path = QPainterPath()
    path.moveTo(x + 1.2, y + h - 1.4)
    path.lineTo(x + w * 0.36, y + h * 0.36)
    path.lineTo(x + w * 0.58, y + h * 0.68)
    path.lineTo(x + w * 0.72, y + h * 0.52)
    path.lineTo(x + w - 1.2, y + h - 1.4)
    path.closeSubpath()
    painter.drawPath(path)


def _cursor(painter):
    painter.setPen(_pen(DARK, 1.4))
    painter.setBrush(QColor(PAPER))
    path = QPainterPath()
    path.moveTo(7.0, 3.5)
    path.lineTo(7.0, 18.0)
    path.lineTo(11.0, 14.0)
    path.lineTo(13.6, 20.2)
    path.lineTo(16.2, 19.0)
    path.lineTo(13.7, 13.0)
    path.lineTo(19.0, 12.6)
    path.closeSubpath()
    painter.drawPath(path)


def _draw_glyph(painter, key: str):
    painter.setRenderHint(QPainter.Antialiasing, True)

    if key in {"optics_engaged", "optics_disengaged"}:
        engaged = key == "optics_engaged"
        color = GREEN if engaged else GREY
        painter.setPen(QPen(QColor(color), 1.8))
        painter.setBrush(QColor(LIGHT_GREEN if engaged else "#eeeeea"))
        painter.drawEllipse(QRectF(3.0, 5.0, 14.0, 14.0))
        painter.setPen(QPen(QColor(color), 1.3))
        painter.setBrush(Qt.NoBrush)
        painter.drawEllipse(QRectF(7.0, 9.0, 6.0, 6.0))
        if engaged:
            painter.setPen(QPen(QColor(GREEN), 2.2, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
            _line(painter, 14.0, 17.0, 16.4, 19.4)
            _line(painter, 16.4, 19.4, 21.0, 13.6)
        else:
            painter.setPen(QPen(QColor(RED), 2.0, Qt.SolidLine, Qt.RoundCap))
            _line(painter, 5.0, 19.0, 19.0, 5.0)
        return

    if key == "optics_apply":
        _document(painter)
        _check(painter, GREEN, 2.3)
        return

    if key == "optics_pixel":
        painter.setPen(QPen(QColor(STEEL), 1.3))
        painter.setBrush(QColor(LIGHT_BLUE))
        for row in range(2):
            for column in range(2):
                painter.drawRect(QRectF(3.0 + column * 4.6, 4.0 + row * 4.6, 3.8, 3.8))
        _lens(painter, 13.0, 13.0, 5.4, DARK)
        return

    if key == "optics_imaging":
        painter.setPen(_pen(DARK, 1.5))
        painter.setBrush(QColor(PAPER))
        painter.drawEllipse(QRectF(4.0, 4.0, 16.0, 16.0))
        path = QPainterPath()
        path.moveTo(12.0, 4.0)
        path.arcTo(QRectF(4.0, 4.0, 16.0, 16.0), 90.0, 180.0)
        path.closeSubpath()
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor("#3d4a55"))
        painter.drawPath(path)
        return

    if key == "optics_aperture":
        painter.setPen(_pen(DARK, 1.4))
        painter.setBrush(QColor(LIGHT_GREY))
        painter.drawEllipse(QRectF(3.5, 3.5, 17.0, 17.0))
        painter.setPen(QPen(QColor(GREY), 1.3))
        for index in range(6):
            angle = math.radians(index * 60.0)
            x = 12.0 + math.cos(angle) * 7.0
            y = 12.0 + math.sin(angle) * 7.0
            _line(painter, x, y, 12.0 + math.cos(angle + 0.9) * 3.4, 12.0 + math.sin(angle + 0.9) * 3.4)
        return

    if key == "optics_focus":
        painter.setPen(QPen(QColor(DARK), 1.5))
        painter.setBrush(QColor(PAPER))
        painter.drawEllipse(QRectF(6.0, 6.0, 12.0, 12.0))
        painter.setPen(QPen(QColor(BLUE), 1.6, Qt.SolidLine, Qt.RoundCap))
        _line(painter, 12.0, 1.5, 12.0, 5.5)
        _line(painter, 12.0, 18.5, 12.0, 22.5)
        _line(painter, 1.5, 12.0, 5.5, 12.0)
        _line(painter, 18.5, 12.0, 22.5, 12.0)
        _arrow(painter, [(9.8, 4.0), (12.0, 1.4), (14.2, 4.0)], BLUE)
        _arrow(painter, [(9.8, 20.0), (12.0, 22.6), (14.2, 20.0)], BLUE)
        return

    if key in {"optics_light", "optics_light_auto"}:
        automatic = key == "optics_light_auto"
        painter.setPen(_pen(AMBER, 1.5))
        painter.setBrush(QColor(LIGHT_AMBER))
        painter.drawEllipse(QRectF(7.0, 3.0, 11.0, 11.0))
        painter.setPen(_pen(AMBER, 1.8))
        _line(painter, 9.6, 15.2, 15.4, 15.2)
        _line(painter, 10.4, 18.0, 14.6, 18.0)
        painter.setPen(QPen(QColor(AMBER), 1.2))
        for angle in (200, 240, 280, 320, 20):
            radians = math.radians(angle - 90)
            _line(painter, 
                12.5 + math.cos(radians) * 8.2,
                8.5 + math.sin(radians) * 8.2,
                12.5 + math.cos(radians) * 10.6,
                8.5 + math.sin(radians) * 10.6,
            )
        if automatic:
            painter.setPen(_pen(BLUE, 1.4))
            painter.setBrush(QColor("#ffffff"))
            painter.drawEllipse(QRectF(14.0, 13.5, 8.0, 8.0))
            painter.setPen(QColor(BLUE))
            font = painter.font()
            font.setFamily("Arial")
            font.setPixelSize(6)
            font.setBold(True)
            painter.setFont(font)
            painter.drawText(QRectF(14.0, 13.0, 8.0, 8.5), Qt.AlignCenter, "A")
        return

    if key == "optics_advanced":
        _gear(painter, 12.0, 12.0, STEEL)
        painter.setPen(_pen(BLUE, 1.3))
        painter.setBrush(QColor("#ffffff"))
        painter.drawEllipse(QRectF(9.6, 9.6, 4.8, 4.8))
        return

    if key == "optics_ruler":
        painter.save()
        painter.translate(12.0, 12.0)
        painter.rotate(-38.0)
        painter.setPen(_pen(AMBER, 1.5))
        painter.setBrush(QColor(LIGHT_AMBER))
        painter.drawRoundedRect(QRectF(-9.5, -4.5, 19.0, 9.0), 1.2, 1.2)
        painter.setPen(QPen(QColor(DARK), 1.1))
        for index in range(5):
            x = -7.5 + index * 3.5
            length = 3.4 if index % 2 == 0 else 2.0
            _line(painter, x, -4.5, x, -4.5 + length)
        painter.restore()
        return

    if key in {"map_select", "review_select"}:
        if key == "map_select":
            painter.setPen(_pen(STEEL, 1.1))
            painter.setBrush(QColor("#eef2f4"))
            painter.drawEllipse(QRectF(9.5, 9.5, 12.0, 12.0))
        _cursor(painter)
        return

    if key == "review_clear":
        painter.setPen(QPen(QColor(RED), 1.4, Qt.DashLine))
        painter.setBrush(Qt.NoBrush)
        painter.drawRect(QRectF(4.0, 4.0, 16.0, 16.0))
        painter.setPen(QPen(QColor(RED), 2.4, Qt.SolidLine, Qt.RoundCap))
        _line(painter, 7.5, 7.5, 16.5, 16.5)
        _line(painter, 16.5, 7.5, 7.5, 16.5)
        return

    if key == "review_mark":
        painter.setPen(_pen(DARK, 1.6))
        painter.setBrush(QColor(PAPER))
        painter.drawEllipse(QRectF(3.5, 3.5, 17.0, 17.0))
        painter.setPen(QPen(QColor(GREEN), 2.4, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        painter.setBrush(Qt.NoBrush)
        _line(painter, 7.5, 12.2, 10.8, 15.6)
        _line(painter, 10.8, 15.6, 16.8, 8.0)
        return

    if key == "review_analysis":
        for index, height in enumerate((7.0, 11.0, 15.0)):
            painter.setPen(_pen(BLUE, 1.3))
            painter.setBrush(QColor(LIGHT_BLUE))
            painter.drawRect(QRectF(4.0 + index * 4.6, 19.0 - height, 3.6, height))
        _lens(painter, 13.5, 13.0, 5.2, DARK)
        return

    if key == "review_super":
        for index, color in enumerate((LIGHT_BLUE, LIGHT_GREEN, LIGHT_AMBER)):
            painter.setPen(_pen(DARK, 1.2))
            painter.setBrush(QColor(color))
            painter.drawRoundedRect(QRectF(3.6 + index * 1.4, 4.4 + index * 4.6, 15.4, 5.4), 1.2, 1.2)
        return

    if key.startswith("review_filter"):
        _funnel(painter)
        if key == "review_filter_in":
            painter.setPen(_pen(GREEN, 1.8))
            painter.setBrush(QColor(LIGHT_GREEN))
            painter.drawEllipse(QRectF(13.0, 13.0, 9.5, 9.5))
            _plus(painter, (17.75, 17.75), 2.9, GREEN)
        elif key == "review_filter_out":
            painter.setPen(_pen(RED, 1.8))
            painter.setBrush(QColor(LIGHT_RED))
            painter.drawEllipse(QRectF(13.0, 13.0, 9.5, 9.5))
            _minus(painter, (17.75, 17.75), 2.9, RED)
        elif key == "review_filter_reset":
            painter.setPen(_pen(BLUE, 1.5))
            painter.setBrush(QColor("#ffffff"))
            painter.drawEllipse(QRectF(13.0, 13.0, 9.5, 9.5))
            painter.setPen(QPen(QColor(BLUE), 1.8, Qt.SolidLine, Qt.RoundCap))
            painter.setBrush(Qt.NoBrush)
            _arc(painter, QRectF(15.2, 15.2, 5.1, 5.1), 60.0, 250.0)
            _arrow(painter, [(19.9, 15.4), (20.6, 18.3), (17.7, 18.0)], BLUE)
        else:
            painter.setPen(_pen(STEEL, 1.4))
            painter.setBrush(QColor("#ffffff"))
            painter.drawEllipse(QRectF(13.0, 13.0, 9.5, 9.5))
            painter.save()
            painter.translate(17.75, 17.75)
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor(STEEL))
            for index in range(6):
                painter.save()
                painter.rotate(index * 60.0)
                painter.drawRoundedRect(QRectF(-1.0, -4.6, 2.0, 2.8), 0.6, 0.6)
                painter.restore()
            painter.drawEllipse(QRectF(-2.5, -2.5, 5.0, 5.0))
            painter.setBrush(QColor("#ffffff"))
            painter.drawEllipse(QRectF(-1.0, -1.0, 2.0, 2.0))
            painter.restore()
        return

    if key == "review_images":
        _picture(painter)
        return

    if key == "review_send_images":
        _picture(painter, (3.0, 7.5, 13.0, 10.5))
        _send_arrow(painter)
        return

    if key == "review_send_wafer":
        _wafer(painter, 10.0, 12.5, 6.6)
        _send_arrow(painter)
        return

    if key == "review_send_lot":
        for index, shade in enumerate(("#b9c6d0", "#9fb1bd", "#c9d3da")):
            painter.setPen(_pen(DARK, 1.2))
            painter.setBrush(QColor(shade))
            painter.drawRoundedRect(QRectF(3.4, 4.6 + index * 4.4, 13.0, 3.6), 1.2, 1.2)
        _send_arrow(painter)
        return

    if key == "review_camera":
        painter.setPen(_pen(DARK, 1.4))
        painter.setBrush(QColor("#d9d9d4"))
        painter.drawRoundedRect(QRectF(2.6, 7.0, 18.8, 12.6), 2.0, 2.0)
        painter.drawRoundedRect(QRectF(8.4, 4.2, 7.2, 3.4), 1.0, 1.0)
        painter.setPen(_pen(DARK, 1.5))
        painter.setBrush(QColor("#5c7382"))
        painter.drawEllipse(QRectF(7.8, 9.2, 8.4, 8.4))
        painter.setPen(QPen(QColor("#eaf2f7"), 1.2))
        painter.setBrush(Qt.NoBrush)
        painter.drawEllipse(QRectF(10.2, 11.6, 3.6, 3.6))
        painter.setPen(_pen(AMBER, 1.6))
        _line(painter, 18.0, 9.2, 20.2, 9.2)
        return

    if key == "map_pan":
        painter.setPen(_pen(DARK, 1.4))
        painter.setBrush(QColor("#e9d9b8"))
        path = QPainterPath()
        path.moveTo(5.0, 12.5)
        path.lineTo(5.0, 9.5)
        path.lineTo(9.0, 9.5)
        path.lineTo(9.0, 6.0)
        path.lineTo(11.4, 6.0)
        path.lineTo(11.4, 9.5)
        path.lineTo(13.2, 9.5)
        path.lineTo(13.2, 7.0)
        path.lineTo(15.4, 7.0)
        path.lineTo(15.4, 10.0)
        path.lineTo(17.0, 10.0)
        path.lineTo(17.0, 12.5)
        path.lineTo(18.6, 12.5)
        path.lineTo(18.6, 15.5)
        path.lineTo(16.4, 19.6)
        path.lineTo(8.6, 19.6)
        path.lineTo(5.0, 14.6)
        path.closeSubpath()
        painter.drawPath(path)
        return

    if key == "map_zoom_region":
        painter.setPen(QPen(QColor(BLUE), 1.3, Qt.DashLine))
        painter.setBrush(Qt.NoBrush)
        painter.drawRect(QRectF(2.6, 2.6, 11.0, 11.0))
        _lens(painter, 13.5, 13.5, 5.6, DARK)
        return

    if key == "map_fit":
        painter.setPen(_pen(GREY, 1.4))
        painter.setBrush(Qt.NoBrush)
        painter.drawRect(QRectF(7.0, 7.0, 10.0, 10.0))
        painter.setPen(QPen(QColor(BLUE), 1.6, Qt.SolidLine, Qt.RoundCap))
        _line(painter, 11.0, 11.0, 4.0, 4.0)
        _line(painter, 13.0, 11.0, 20.0, 4.0)
        _line(painter, 11.0, 13.0, 4.0, 20.0)
        _line(painter, 13.0, 13.0, 20.0, 20.0)
        _arrow(painter, [(4.0, 7.0), (4.0, 3.6), (7.4, 4.0)], BLUE)
        _arrow(painter, [(17.0, 4.0), (20.4, 3.6), (20.0, 7.0)], BLUE)
        _arrow(painter, [(4.0, 17.0), (3.6, 20.4), (7.0, 20.0)], BLUE)
        _arrow(painter, [(20.0, 17.0), (20.4, 20.4), (17.0, 20.0)], BLUE)
        return

    if key == "map_stack":
        painter.setPen(_pen(DARK, 1.3))
        for index, shade in enumerate(("#c9d3da", "#b3c2cc", "#dde5eb")):
            painter.setBrush(QColor(shade))
            painter.drawEllipse(QRectF(3.6, 5.0 + index * 4.6, 16.8, 6.4))
        return

    if key == "map_legend":
        palette = ("#d64d4d", "#e0a52a", "#3c9a4a", "#3f6cb5")
        for index, color in enumerate(palette):
            painter.setPen(_pen(DARK, 1.1))
            painter.setBrush(QColor(color))
            painter.drawRoundedRect(QRectF(4.0, 3.6 + index * 4.7, 6.4, 3.8), 0.8, 0.8)
            painter.setPen(QPen(QColor(GREY), 1.2))
            _line(painter, 12.0, 5.5 + index * 4.7, 20.0, 5.5 + index * 4.7)
        return

    if key == "map_count":
        painter.setPen(_pen(DARK, 1.4))
        painter.setBrush(QColor(PAPER))
        painter.drawRoundedRect(QRectF(2.6, 4.6, 18.8, 14.8), 2.0, 2.0)
        font = painter.font()
        font.setFamily("Arial")
        font.setPixelSize(10)
        font.setBold(True)
        painter.setFont(font)
        painter.setPen(QColor(BLUE))
        painter.drawText(QRectF(3.0, 4.0, 18.0, 15.0), Qt.AlignCenter, "123")
        return

    if key == "map_rules":
        for index, color in enumerate((BLUE, GREEN, AMBER)):
            y = 5.5 + index * 6.5
            painter.setPen(_pen(GREY, 1.4))
            _line(painter, 3.0, y, 21.0, y)
            painter.setPen(_pen(DARK, 1.2))
            painter.setBrush(QColor(color))
            painter.drawEllipse(QRectF(4.5 + index * 5.0, y - 2.6, 5.2, 5.2))
        return

    if key == "map_care":
        painter.setPen(QPen(QColor(BLUE), 1.3, Qt.DashLine))
        painter.setBrush(QColor("#e8f1fb"))
        painter.drawEllipse(QRectF(3.4, 3.4, 17.2, 17.2))
        painter.setPen(QPen(QColor(BLUE), 1.0))
        path = QPainterPath()
        path.moveTo(6.0, 16.0)
        path.lineTo(16.0, 6.0)
        painter.setClipPath(path)
        for offset in range(-20, 30, 4):
            _line(painter, 0.0, 4.0 + offset, 24.0, -6.0 + offset)
        painter.setClipping(False)
        return

    if key == "map_partial":
        painter.setPen(_pen(GREY, 1.3))
        painter.setBrush(QColor("#f1efe8"))
        painter.drawEllipse(QRectF(3.4, 3.4, 17.2, 17.2))
        painter.setPen(QPen(QColor(RED), 1.8))
        painter.setBrush(Qt.NoBrush)
        _arc(painter, QRectF(6.4, 6.4, 11.2, 11.2), 40.0, 220.0)
        painter.setPen(QPen(QColor(GREY), 1.2, Qt.DashLine))
        _line(painter, 12.0, 12.0, 20.6, 12.0)
        return

    if key in {"map_pd_sd", "map_sd_pd"}:
        first, second = ("#4a5a68", PAPER) if key == "map_pd_sd" else (PAPER, "#4a5a68")
        painter.setPen(_pen(DARK, 1.3))
        painter.setBrush(QColor(first))
        painter.drawEllipse(QRectF(2.6, 8.6, 8.4, 8.4))
        painter.setBrush(QColor(second))
        painter.drawEllipse(QRectF(13.0, 8.6, 8.4, 8.4))
        painter.setPen(QPen(QColor(BLUE), 1.8, Qt.SolidLine, Qt.RoundCap))
        _line(painter, 6.8, 5.6, 17.2, 5.6)
        _arrow(painter, [(15.0, 2.8), (17.6, 5.6), (15.0, 8.4)], BLUE)
        return

    if key == "map_help":
        painter.setPen(_pen(BLUE, 1.5))
        painter.setBrush(QColor("#e4effa"))
        painter.drawEllipse(QRectF(3.0, 3.0, 18.0, 18.0))
        font = painter.font()
        font.setFamily("Arial")
        font.setPixelSize(12)
        font.setBold(True)
        painter.setFont(font)
        painter.setPen(QColor(BLUE))
        painter.drawText(QRectF(3.0, 2.4, 18.0, 18.0), Qt.AlignCenter, "?")
        return

    if key in {"grid_save", "grid_default", "grid_delete"}:
        if key == "grid_delete":
            painter.setPen(_pen(DARK, 1.4))
            painter.setBrush(QColor("#d9d9d4"))
            painter.drawRoundedRect(QRectF(6.0, 7.0, 12.0, 14.0), 1.4, 1.4)
            painter.drawRoundedRect(QRectF(4.2, 4.4, 15.6, 3.0), 1.0, 1.0)
            _line(painter, 9.6, 3.0, 14.4, 3.0)
            painter.setPen(QPen(QColor(RED), 1.6))
            _line(painter, 9.4, 10.0, 9.4, 18.0)
            _line(painter, 12.0, 10.0, 12.0, 18.0)
            _line(painter, 14.6, 10.0, 14.6, 18.0)
            return
        painter.setPen(_pen(DARK, 1.4))
        painter.setBrush(QColor(key == "grid_default" and "#eef1f4" or "#e6e8ea"))
        painter.drawRoundedRect(QRectF(3.6, 3.6, 16.8, 16.8), 1.6, 1.6)
        painter.setPen(_pen(GREY, 1.2))
        painter.setBrush(QColor(PAPER))
        painter.drawRect(QRectF(7.0, 3.8, 10.0, 6.0))
        painter.setBrush(QColor(LIGHT_BLUE))
        painter.drawRect(QRectF(6.4, 12.0, 11.2, 7.4))
        if key == "grid_default":
            painter.setPen(_pen(AMBER, 1.2))
            painter.setBrush(QColor(AMBER))
            path = QPainterPath()
            for index in range(10):
                angle = math.radians(-90 + index * 36)
                radius = 4.6 if index % 2 == 0 else 2.0
                x = 16.8 + math.cos(angle) * radius
                y = 16.4 + math.sin(angle) * radius
                if index == 0:
                    path.moveTo(x, y)
                else:
                    path.lineTo(x, y)
            path.closeSubpath()
            painter.drawPath(path)
        return

    # Generic fallback keeps an unknown name from producing an empty button.
    _document(painter)


def pixmap(name: str, height: int = 22, *, ratio: float = 1.0) -> QPixmap:
    """Return a crisp pixmap for an asset-style name such as ``review_mark.png``."""
    key = str(name or "").rsplit(".", 1)[0]
    height = max(8, int(height))
    width = height
    if ratio <= 1.0:
        # Exact logical size keeps QIcon.availableSizes() equal to the button
        # size the call sites derive from it.
        pixmap = QPixmap(width, height)
        pixmap.fill(Qt.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing, True)
        scale = height / DESIGN
        painter.scale(scale, scale)
        _draw_glyph(painter, key)
        painter.end()
        return pixmap
    pixmap = QPixmap(int(round(width * ratio)), int(round(height * ratio)))
    pixmap.setDevicePixelRatio(ratio)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing, True)
    scale = (height * ratio) / DESIGN
    painter.scale(scale, scale)
    _draw_glyph(painter, key)
    painter.end()
    return pixmap


def icon(name: str, height: int = 22) -> QIcon:
    """Build one icon with several raster sizes so big buttons stay sharp."""
    result = QIcon()
    for size in (height, int(round(height * 1.5)), height * 2):
        result.addPixmap(pixmap(name, size))
    return result

