from __future__ import annotations

from typing import Optional

from ...qt_compat import (
    QColor,
    QFrame,
    QHBoxLayout,
    QIcon,
    QLabel,
    QPainter,
    QPen,
    QPixmap,
    QPushButton,
    QSize,
    Qt,
    QVBoxLayout,
    QWidget,
)


def _pixmap_icon(kind: str, size: int = 28) -> QIcon:
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)

    if kind in {"cassette", "cassette-disabled"}:
        active = kind == "cassette"
        body = QColor("#ff6f21" if active else "#9b9b9b")
        dark = QColor("#1d1d1d" if active else "#6d6d6d")
        painter.setPen(QPen(QColor("#333333"), 1))
        painter.setBrush(body)
        painter.drawRect(5, 5, 16, 18)
        painter.setBrush(QColor("#222222" if active else "#777777"))
        painter.drawEllipse(8, 8, 10, 10)
        painter.setPen(QPen(dark, 2))
        painter.drawLine(8, 22, 21, 14)
        painter.drawLine(21, 14, 21, 22)
        painter.setBrush(QColor("#333333" if active else "#777777"))
        painter.drawRect(2, 10, 5, 10)
    elif kind == "wafer":
        painter.setBrush(QColor("#595959"))
        painter.setPen(QPen(QColor("#f4f4f4"), 1))
        painter.drawEllipse(5, 5, 18, 18)
    elif kind == "load-align":
        painter.setBrush(QColor("#575757"))
        painter.setPen(QPen(QColor("#f4f4f4"), 1))
        painter.drawEllipse(5, 5, 18, 18)
        painter.setPen(QPen(QColor("#4d5fd4"), 3))
        painter.drawLine(10, 14, 20, 14)
    elif kind == "align":
        painter.setPen(QPen(QColor("#777777"), 3))
        painter.drawLine(8, 9, 20, 9)
        painter.drawLine(8, 18, 20, 18)
    elif kind == "recovery":
        painter.setBrush(QColor("#ed1c24"))
        painter.setPen(QPen(QColor("#ffffff"), 1))
        painter.drawEllipse(4, 4, 20, 20)
        painter.setPen(QPen(QColor("#ffffff"), 4))
        painter.drawLine(14, 8, 14, 20)
        painter.drawLine(8, 14, 20, 14)

    painter.end()
    return QIcon(pixmap)


class EmptyWaferDisk(QWidget):
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setFixedSize(86, 86)

    def paintEvent(self, event):  # noqa: N802 - Qt override
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setBrush(QColor("#c4c0b0"))
        pen = QPen(QColor("#5f5b53"), 1)
        pen.setStyle(Qt.DashLine)
        painter.setPen(pen)
        painter.drawEllipse(8, 8, 68, 68)


class OrientationDisk(QWidget):
    def __init__(self, notch: str, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.notch = notch
        self.setFixedSize(26, 24)

    def paintEvent(self, event):  # noqa: N802 - Qt override
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setBrush(QColor("#242424"))
        painter.setPen(QPen(QColor("#111111"), 1))
        painter.drawEllipse(3, 2, 20, 20)
        painter.setBrush(QColor("#c4c0b0"))
        painter.setPen(Qt.NoPen)
        if self.notch == "up":
            painter.drawEllipse(9, 0, 8, 8)
        elif self.notch == "right":
            painter.drawEllipse(17, 8, 8, 8)
        elif self.notch == "down":
            painter.drawEllipse(9, 16, 8, 8)
        else:
            painter.drawEllipse(1, 8, 8, 8)


class RadioDot(QWidget):
    def __init__(self, selected: bool = False, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.selected = selected
        self.setFixedSize(13, 13)

    def paintEvent(self, event):  # noqa: N802 - Qt override
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setBrush(QColor("#ffffff"))
        painter.setPen(QPen(QColor("#2b61b8"), 1))
        painter.drawEllipse(2, 2, 9, 9)
        if self.selected:
            painter.setBrush(QColor("#1ea542"))
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(5, 5, 4, 4)


class CassetteBody(QFrame):
    def __init__(self, port_number: int, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.port_number = port_number
        self.selected_slot = 25 if port_number == 1 else None
        self.aligned = port_number == 1
        self.setMinimumSize(150, 390)

    def paintEvent(self, event):  # noqa: N802 - Qt override
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        rect = self.rect().adjusted(9, 8, -9, -10)
        painter.setBrush(QColor("#a8a8a4"))
        painter.setPen(QPen(QColor("#777777"), 5))
        painter.drawRect(rect.adjusted(0, 10, 0, 0))
        painter.setPen(QPen(QColor("#f7f7f7"), 2))
        painter.drawLine(rect.left() + 5, rect.top() + 10, rect.right() - 5, rect.top() + 10)

        slot_top = rect.top() + 15
        slot_height = max(12, int((rect.height() - 34) / 25))
        for row, slot in enumerate(range(25, 0, -1)):
            y = slot_top + row * slot_height
            if y + slot_height > rect.bottom() - 11:
                break
            label_rect = rect.adjusted(4, 0, -rect.width() + 27, 0)
            label_rect.setTop(y - 1)
            label_rect.setBottom(y + slot_height)
            painter.setPen(QColor("#f5f5f5") if slot == self.selected_slot else QColor("#444444"))
            painter.drawText(label_rect, Qt.AlignRight | Qt.AlignVCenter, str(slot))

            painter.setBrush(QColor("#1ed02e") if slot == self.selected_slot else QColor("#f3f3f3"))
            painter.setPen(QPen(QColor("#004d00") if slot == self.selected_slot else QColor("#808080"), 1))
            painter.drawEllipse(rect.left() + 29, y + 2, 10, 10)

            slot_rect = rect.adjusted(43, 0, -5, 0)
            slot_rect.setTop(y + 1)
            slot_rect.setBottom(y + slot_height - 1)
            if slot == self.selected_slot:
                painter.setBrush(QColor("#c9f3a8"))
                painter.setPen(QPen(QColor("#1420c8"), 2))
                painter.drawRoundedRect(slot_rect, 3, 3)
                painter.setPen(QPen(QColor("#1e6410"), 1))
                painter.drawText(slot_rect, Qt.AlignCenter, "Aligned")
            else:
                gradient_color = QColor("#ffffff") if slot % 2 else QColor("#e8e8e8")
                painter.setBrush(gradient_color)
                painter.setPen(QPen(QColor("#a8a8a8"), 1))
                painter.drawRoundedRect(slot_rect, 4, 4)

        painter.setPen(QPen(QColor("#777777"), 2))
        painter.drawLine(rect.left(), rect.bottom() - 7, rect.right(), rect.bottom() - 7)
        painter.setBrush(QColor("#008a1d"))
        painter.setPen(QPen(QColor("#006812"), 1))
        painter.drawEllipse(rect.center().x() - 12, rect.bottom() - 9, 8, 8)
        painter.drawEllipse(rect.center().x() + 4, rect.bottom() - 9, 8, 8)


class ShowWaferPanel(QFrame):
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setMinimumWidth(720)
        self.setObjectName("showWaferPanel")
        self.port_widgets = {}
        self.setStyleSheet(
            """
            QFrame#showWaferPanel {
                background: #c4c0b0;
                border-left: 1px solid #807c73;
            }
            QLabel {
                font-size: 10px;
                color: #111111;
            }
            QLabel[section="true"] {
                color: #1b58d4;
                font-weight: 600;
            }
            QPushButton {
                background: #eceae0;
                border-top: 1px solid #ffffff;
                border-left: 1px solid #ffffff;
                border-right: 1px solid #77736b;
                border-bottom: 1px solid #77736b;
                min-height: 25px;
                padding: 2px 5px;
            }
            QPushButton:disabled {
                color: #888888;
                background: #d8d5cc;
            }
            """
        )
        self._build_ui()

    def _build_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 8)
        layout.setSpacing(10)
        layout.addWidget(self._wafer_operations())
        for port_number in [1, 2, 3]:
            port = self._load_port(port_number)
            self.port_widgets[port_number] = port
            layout.addWidget(port, 1)

    def _wafer_operations(self) -> QWidget:
        panel = QFrame()
        panel.setFixedWidth(168)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        top = QHBoxLayout()
        top.setSpacing(7)
        top.addWidget(EmptyWaferDisk(), alignment=Qt.AlignLeft | Qt.AlignTop)
        self.wafer_details = QLabel(
            "Port  1\n"
            "Slot  25\n"
            "State  Loaded\n"
            "Alignment  Aligned\n"
            "Align. Angle  0 deg\n"
            "Diameter  300 mm\n"
            "Type  Patterned"
        )
        self.wafer_details.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        self.wafer_details.setStyleSheet("font-size: 9px;")
        top.addWidget(self.wafer_details, 1)
        layout.addLayout(top)

        title = QLabel("Wafer Operations")
        title.setProperty("section", True)
        layout.addWidget(title)

        operations_box = QFrame()
        operations_box.setStyleSheet(
            """
            QFrame {
                background: #d0ccbc;
                border: 1px solid #b0ab9d;
            }
            """
        )
        operations = QVBoxLayout(operations_box)
        operations.setContentsMargins(7, 7, 7, 8)
        operations.setSpacing(7)

        button_row = QHBoxLayout()
        button_row.setSpacing(5)
        button_row.addWidget(self._operation_button("Load", "wafer"))
        button_row.addWidget(self._operation_button("Load &&\nAlign", "load-align"))
        button_row.addWidget(self._operation_button("Align", "align"))
        operations.addLayout(button_row)

        unload = QPushButton("Unload Wafer")
        unload.setIcon(_pixmap_icon("wafer", 22))
        unload.setIconSize(QSize(22, 22))
        unload.setFixedHeight(31)
        operations.addWidget(unload)

        recovery = QPushButton("Automatic Recovery")
        recovery.setIcon(_pixmap_icon("recovery", 28))
        recovery.setIconSize(QSize(26, 26))
        recovery.setFixedHeight(34)
        operations.addWidget(recovery)
        layout.addWidget(operations_box)

        orient = QLabel("Change Orientation:")
        orient.setStyleSheet("font-weight: 600;")
        layout.addWidget(orient)
        layout.addLayout(self._orientation_row())
        layout.addStretch(1)
        return panel

    def _operation_button(self, label: str, icon_name: str) -> QPushButton:
        button = QPushButton(label)
        button.setIcon(_pixmap_icon(icon_name, 26))
        button.setIconSize(QSize(25, 25))
        button.setFixedSize(48, 62)
        return button

    def _orientation_row(self) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setSpacing(6)
        for text, notch, selected in [
            ("Up\n(0)", "up", False),
            ("Right\n(90)", "right", False),
            ("Down\n(180)", "down", True),
            ("Left\n(270)", "left", False),
        ]:
            item = QVBoxLayout()
            item.setSpacing(1)
            item.addWidget(OrientationDisk(notch), alignment=Qt.AlignHCenter)
            label = QLabel(text)
            label.setAlignment(Qt.AlignCenter)
            label.setStyleSheet("font-size: 9px;")
            item.addWidget(label)
            item.addWidget(RadioDot(selected), alignment=Qt.AlignHCenter)
            row.addLayout(item)
        return row

    def _load_port(self, port_number: int) -> QWidget:
        panel = QFrame()
        panel.setStyleSheet(
            """
            QFrame#loadPort {
                background: transparent;
                border: 0;
            }
            QLabel#portTab {
                background: #f0f0f0;
                border: 1px solid #777777;
                border-radius: 4px;
                font-weight: 600;
                padding: 1px 20px;
            }
            """
        )
        panel.setObjectName("loadPort")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)

        commands = QHBoxLayout()
        commands.setSpacing(4)
        load = QPushButton("Load")
        load.setIcon(_pixmap_icon("cassette", 28))
        load.setIconSize(QSize(28, 28))
        load.setFixedSize(76, 40)
        unload = QPushButton("Unload")
        unload.setIcon(_pixmap_icon("cassette-disabled", 28))
        unload.setIconSize(QSize(28, 28))
        unload.setFixedSize(76, 40)
        commands.addWidget(load)
        commands.addWidget(unload)
        layout.addLayout(commands)

        prefix = ">" if port_number == 1 else ""
        tab = QLabel(f"{prefix}  Port {port_number}" if prefix else f"Port {port_number}")
        tab.setObjectName("portTab")
        tab.setAlignment(Qt.AlignCenter)
        layout.addWidget(tab, alignment=Qt.AlignHCenter)

        cassette = CassetteBody(port_number)
        layout.addWidget(cassette, 1)

        if port_number == 1:
            text = (
                "Carrier State   Mapped\n"
                "Port State      Carrier Unlocked & Open...\n"
                "Transfer        Carrier Allocated to Equip...\n"
                "Port Size       300 mm"
            )
        elif port_number == 2:
            text = (
                "Carrier State   Mapped\n"
                "Port State      Carrier Present & Unclam...\n"
                "Transfer        Ready to Unload\n"
                "Port Size       300 mm"
            )
        else:
            text = (
                "Carrier State   No Cassette\n"
                "Port State      Ready to Load\n"
                "Transfer        Ready to Load\n"
                "Port Size       300 mm"
            )
        state = QLabel(text)
        state.setAlignment(Qt.AlignHCenter)
        state.setStyleSheet("font-size: 9px;")
        layout.addWidget(state)
        return panel

    def set_visible_ports(self, choice: str):
        count = len(self.port_widgets) if choice == "All" else max(1, min(int(choice), len(self.port_widgets)))
        for port_number, widget in self.port_widgets.items():
            widget.setVisible(port_number <= count)

    def update_recipe(self, recipe: dict):
        self.setToolTip(
            "Inspection: {inspection}\nDevice: {device}\nStep: {step}".format(
                inspection=recipe.get("inspection", ""),
                device=recipe.get("device", ""),
                step=recipe.get("step", ""),
            )
        )
