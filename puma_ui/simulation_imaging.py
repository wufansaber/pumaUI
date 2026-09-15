from __future__ import annotations

from .qt_compat import QColor, QPainter, QPen, Qt


def paint_simulated_die(
    painter: QPainter,
    rect,
    *,
    channel: int = 1,
    filtered: bool = False,
    brightfield: bool = False,
    grayscale: bool = False,
) -> None:
    """Paint a deterministic semiconductor inspection image into a Qt rectangle."""
    painter.save()
    painter.setClipRect(rect)
    left, top = rect.left(), rect.top()
    width, height = max(1, rect.width()), max(1, rect.height())
    palettes = (
        (24, 47, 52, 91, 142, 146),
        (25, 34, 67, 74, 104, 171),
        (31, 42, 63, 92, 118, 154),
    )
    dark_r, dark_g, dark_b, light_r, light_g, light_b = palettes[(int(channel) - 1) % 3]
    if brightfield:
        dark_r += 35
        dark_g += 35
        dark_b += 31
        light_r += 45
        light_g += 45
        light_b += 40
    if grayscale:
        dark_value = int(dark_r * 0.22 + dark_g * 0.68 + dark_b * 0.10)
        light_value = int(light_r * 0.22 + light_g * 0.68 + light_b * 0.10)
        dark_r = dark_g = dark_b = dark_value
        light_r = light_g = light_b = light_value
    painter.fillRect(rect, QColor(dark_r, dark_g, dark_b))

    band_step = max(3, height // 120)
    for row in range(0, height, band_step):
        variation = (row * 17 + channel * 23) % 18
        painter.setPen(QPen(QColor(
            min(255, dark_r + variation),
            min(255, dark_g + variation),
            min(255, dark_b + variation),
        ), 1))
        painter.drawLine(left, top + row, left + width, top + row)

    gap = max(8, width // 40)
    memory_left = left + width // 24
    memory_top = top + height // 18
    memory_width = width * 11 // 24
    memory_height = height * 11 // 18
    painter.fillRect(memory_left, memory_top, memory_width, memory_height, QColor(
        max(0, dark_r - 4), min(255, dark_g + 8), min(255, dark_b + 10)
    ))
    line_step = max(4, height // (38 if filtered else 70))
    painter.setPen(QPen(QColor(light_r, light_g, light_b), 1))
    for y in range(memory_top + gap // 2, memory_top + memory_height, line_step):
        painter.drawLine(memory_left + 3, y, memory_left + memory_width - 3, y)
    column_step = max(6, width // 45)
    painter.setPen(QPen(QColor(light_r // 2, light_g // 2, light_b // 2), 1))
    for x in range(memory_left + gap, memory_left + memory_width, column_step):
        painter.drawLine(x, memory_top + 2, x, memory_top + memory_height - 2)

    logic_left = left + width * 13 // 24
    logic_top = top + height // 18
    logic_width = width * 10 // 24
    logic_height = height * 11 // 18
    painter.fillRect(logic_left, logic_top, logic_width, logic_height, QColor(
        max(0, dark_r - 7), max(0, dark_g - 2), min(255, dark_b + 5)
    ))
    route_step = max(13, height // 24)
    for index, y in enumerate(range(logic_top + gap, logic_top + logic_height, route_step)):
        start = logic_left + gap + (index * 29 % max(gap, logic_width // 4))
        end = logic_left + logic_width - gap - (index * 17 % max(gap, logic_width // 5))
        route = QColor(light_r + min(50, index % 3 * 18), light_g, light_b)
        painter.setPen(QPen(route, 2 if filtered else 3))
        painter.drawLine(start, y, end, y)
        if index % 2 == 0:
            via_x = start + max(4, (end - start) // 3)
            painter.drawLine(via_x, y, via_x, min(logic_top + logic_height, y + route_step))
            painter.setBrush(QColor(205, 216, 210))
            painter.drawRect(via_x - 2, y - 2, 5, 5)

    lower_top = top + height * 13 // 18
    lower_height = height * 4 // 18
    painter.fillRect(memory_left, lower_top, memory_width, lower_height, QColor(
        min(255, dark_r + 8), min(255, dark_g + 10), min(255, dark_b + 10)
    ))
    contact = max(3, min(width, height) // 75)
    contact_step = max(9, min(width, height) // 27)
    painter.setPen(QPen(QColor(light_r, light_g, light_b), 1))
    painter.setBrush(QColor(190, 204, 199))
    for y in range(lower_top + contact_step, lower_top + lower_height, contact_step):
        for x in range(memory_left + contact_step, memory_left + memory_width, contact_step):
            painter.drawRect(x, y, contact, contact)

    painter.setBrush(Qt.NoBrush)
    analog_left = logic_left + gap
    analog_top = lower_top + gap // 2
    analog_width = max(12, logic_width - gap * 2)
    analog_height = max(12, lower_height - gap)
    for inset in range(0, max(1, min(analog_width, analog_height) // 3), max(5, gap // 2)):
        painter.setPen(QPen(QColor(light_r, light_g, light_b), 2))
        painter.drawRect(
            analog_left + inset,
            analog_top + inset,
            max(1, analog_width - inset * 2),
            max(1, analog_height - inset * 2),
        )

    if not filtered:
        painter.setPen(QPen(QColor(183, 224, 226, 115), 1))
        interference_step = max(4, height // 85)
        for offset in range(-height, width, interference_step):
            painter.drawLine(left + offset, top, left + offset + height, top + height)
    else:
        painter.setPen(QPen(QColor(238, 245, 231), 2))
        for x_fraction, y_fraction in ((0.20, 0.27), (0.43, 0.58), (0.72, 0.34), (0.84, 0.71)):
            x = left + int(width * x_fraction)
            y = top + int(height * y_fraction)
            painter.drawLine(x - 5, y, x + 5, y)
            painter.drawLine(x, y - 5, x, y + 5)
    painter.restore()
