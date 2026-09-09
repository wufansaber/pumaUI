from __future__ import annotations

from copy import deepcopy

from ...qt_compat import (
    QCheckBox,
    QColor,
    QComboBox,
    QDialog,
    QDoubleSpinBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QListWidget,
    QMessageBox,
    QPainter,
    QPen,
    QProgressBar,
    QPushButton,
    QSlider,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    Qt,
    QVBoxLayout,
    QWidget,
)


def default_segmentation_state() -> dict:
    return {
        "sites": [],
        "regions": {},
        "sdi": {"groups": {}, "image_box": [0.20, 0.20, 0.35, 0.35]},
        "valid": False,
    }


def normalized_segmentation_state(state: dict | None) -> dict:
    result = default_segmentation_state()
    if isinstance(state, dict):
        result.update(deepcopy(state))
    result["sites"] = deepcopy(result.get("sites") or [])
    result["regions"] = deepcopy(result.get("regions") or {})
    result["sdi"] = deepcopy(result.get("sdi") or default_segmentation_state()["sdi"])
    return result


def validate_segmentation_regions(regions) -> list[str]:
    errors = []
    for region_name, region in (regions or {}).items():
        channels = list(region.get("channels") or [])
        active_types = {
            channel.get("type", "Off")
            for channel in channels
            if channel.get("type", "Off") != "Off"
        }
        if len(active_types) > 1:
            errors.append(f"{region_name}: all enabled channels must use one Segmentation Type")
        for channel_index, channel in enumerate(channels, start=1):
            segmentation_type = channel.get("type", "Off")
            breaks = list(channel.get("breaks") or [])
            if segmentation_type == "Off" and breaks:
                errors.append(f"{region_name} Channel {channel_index}: Off channels cannot contain breaks")
                continue
            if segmentation_type == "Median Based Segmentation":
                invalid_axes = [item for item in breaks if item.get("axis") != "Histogram"]
            elif segmentation_type in {
                "Projection Based Segmentation",
                "Median-Edge Based Segmentation",
            }:
                invalid_axes = [item for item in breaks if item.get("axis") not in {"X", "Y"}]
            else:
                invalid_axes = []
            if invalid_axes:
                errors.append(
                    f"{region_name} Channel {channel_index}: break type does not match Segmentation Type"
                )
            group_ids = sorted({int(item.get("group", 0)) for item in breaks})
            if group_ids and group_ids != list(range(group_ids[-1] + 1)):
                errors.append(
                    f"{region_name} Channel {channel_index}: Segment Group IDs must be consecutive from 0"
                )
            source = channel.get("source", "Own Channel")
            if source == "Own Channel":
                continue
            if segmentation_type not in {
                "Projection Based Segmentation",
                "Median-Edge Based Segmentation",
            }:
                errors.append(
                    f"{region_name} Channel {channel_index}: cross-channel segmentation requires PBS or MEBS"
                )
                continue
            try:
                source_index = int(str(source).rsplit(" ", 1)[-1]) - 1
                source_channel = channels[source_index]
            except (IndexError, TypeError, ValueError):
                errors.append(f"{region_name} Channel {channel_index}: invalid source channel")
                continue
            if source_channel.get("type", "Off") == "Off" or not source_channel.get("breaks"):
                errors.append(
                    f"{region_name} Channel {channel_index}: source channel has no segmentation grid"
                )
    return errors


class SegmentationDialog(QDialog):
    def __init__(self, state=None, care_groups=None, wafer_ready=True, parent=None):
        super().__init__(parent)
        self.state = normalized_segmentation_state(state)
        self.care_groups = deepcopy(care_groups or [])
        self.wafer_ready = bool(wafer_ready)
        self.result_state = None
        self.changed = False
        self.setWindowTitle("Segmentation")
        self.resize(900, 620)
        self.setStyleSheet(
            "QDialog { background: #cfcbc2; font-family: Arial; font-size: 10px; }"
            "QPushButton { background: #e8e6dd; border: 1px solid #77736b; min-height: 28px; padding: 3px 10px; }"
            "QFrame#summary { background: #efede5; border: 1px solid #8c8982; }"
        )
        root = QHBoxLayout(self)
        commands = QVBoxLayout()
        for label, handler in [
            ("Segmentation Image\nGrab", self._image_grab),
            ("Segmentation\nSetup", self._setup),
            ("Single Die\nInspection", self._sdi),
        ]:
            button = QPushButton(label)
            button.setFixedSize(250, 58)
            button.clicked.connect(handler)
            commands.addWidget(button)
            if label.startswith("Segmentation Image"):
                self.image_grab_button = button
                button.setEnabled(self.wafer_ready)
                button.setToolTip(
                    "" if self.wafer_ready else "Load and align the patterned wafer before grabbing images."
                )
            elif label.startswith("Single Die"):
                self.sdi_button = button
                button.setEnabled(self.wafer_ready)
                button.setToolTip(
                    "" if self.wafer_ready else "Load and align the patterned wafer in the test orientation before SDI setup."
                )
        commands.addStretch(1)
        root.addLayout(commands)
        content = QVBoxLayout()
        title = QLabel("Sensitivity Setup - Segmentation")
        title.setStyleSheet("font-size: 14px; font-weight: 700;")
        content.addWidget(title)
        self.preview = SegmentationSummary(self.state)
        content.addWidget(self.preview, 1)
        self.summary = QLabel()
        self.summary.setObjectName("summary")
        self.summary.setMinimumHeight(80)
        self.summary.setWordWrap(True)
        content.addWidget(self.summary)
        buttons = QHBoxLayout()
        buttons.addStretch(1)
        finish = QPushButton("Finish")
        finish.clicked.connect(self._finish)
        cancel = QPushButton("Cancel")
        cancel.clicked.connect(self.reject)
        buttons.addWidget(finish)
        buttons.addWidget(cancel)
        content.addLayout(buttons)
        root.addLayout(content, 1)
        self._refresh()

    def _image_grab(self):
        if not self.wafer_ready:
            QMessageBox.warning(
                self,
                "Segmentation Image Grab",
                "Load and align the patterned wafer before grabbing segmentation images.",
            )
            return
        dialog = SegmentationImageGrabDialog(self.state["sites"], self)
        result = dialog.exec() if hasattr(dialog, "exec") else dialog.exec_()
        if result == QDialog.Accepted:
            self.state["sites"] = dialog.result_sites
            self.state["valid"] = False
            self.changed = True
            self._refresh()

    def _setup(self):
        if not any(site.get("grabbed") for site in self.state["sites"]):
            QMessageBox.warning(self, "Segmentation Setup", "Grab at least one segmentation image first.")
            return
        dialog = SegmentationSetupDialog(self.state["regions"], self.care_groups, self)
        result = dialog.exec() if hasattr(dialog, "exec") else dialog.exec_()
        if result == QDialog.Accepted:
            self.state["regions"] = dialog.result_regions
            self.state["valid"] = not validate_segmentation_regions(self.state["regions"]) and any(
                channel.get("type", "Off") != "Off"
                for region in self.state["regions"].values()
                for channel in region.get("channels", [])
            )
            self.changed = True
            self._refresh()

    def _sdi(self):
        if not self.wafer_ready:
            QMessageBox.warning(
                self,
                "Single Die Inspection",
                "Load and align the patterned wafer in the test orientation before SDI setup.",
            )
            return
        dialog = SingleDieInspectionDialog(self.state["sdi"], self.care_groups, self)
        result = dialog.exec() if hasattr(dialog, "exec") else dialog.exec_()
        if result == QDialog.Accepted:
            self.state["sdi"] = dialog.result_state
            self.changed = True
            self._refresh()

    def _refresh(self):
        grabbed = sum(bool(site.get("grabbed")) for site in self.state["sites"])
        configured = sum(
            any(channel.get("type", "Off") != "Off" for channel in region.get("channels", []))
            for region in self.state["regions"].values()
        )
        sdi_count = sum(bool(item.get("enabled")) for item in self.state["sdi"].get("groups", {}).values())
        self.summary.setText(
            f"Image Sites: {len(self.state['sites'])} | Images Grabbed: {grabbed}\n"
            f"Segmented Regions: {configured} | SDI Care Area Groups: {sdi_count} | "
            f"Status: {'Valid' if self.state['valid'] else 'Setup required'}"
        )
        self.preview.state = self.state
        self.preview.update()

    def _finish(self):
        self.result_state = deepcopy(self.state)
        self.accept()


class SegmentationSummary(QWidget):
    def __init__(self, state, parent=None):
        super().__init__(parent)
        self.state = state
        self.setMinimumSize(500, 380)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor("#657a82"))
        painter.setPen(QPen(QColor("#87999f"), 1))
        for offset in range(0, self.width(), 24):
            painter.drawLine(offset, 0, offset, self.height())
        for offset in range(0, self.height(), 24):
            painter.drawLine(0, offset, self.width(), offset)
        for index, site in enumerate(self.state.get("sites", [])):
            x = int(site["x"] * self.width())
            y = int(site["y"] * self.height())
            painter.setBrush(QColor("#42d5eb" if site.get("grabbed") else "#ffdf00"))
            painter.setPen(QPen(QColor("#111111"), 1))
            painter.drawEllipse(x - 8, y - 8, 16, 16)
            painter.drawText(x + 10, y + 4, str(index + 1))


class SegmentationImageGrabDialog(QDialog):
    def __init__(self, sites, parent=None):
        super().__init__(parent)
        self.result_sites = deepcopy(sites or [])
        self.current_position = [0.50, 0.50]
        self.setWindowTitle("Segmentation Image Grab")
        self.resize(1040, 650)
        root = QVBoxLayout(self)
        panes = QHBoxLayout()
        left = QVBoxLayout()
        left.addWidget(QLabel("Mark Sites"))
        self.canvas = SiteCanvas(self.result_sites, self._position_changed)
        left.addWidget(self.canvas, 1)
        instructions = QHBoxLayout()
        mark = QPushButton("Mark New Site")
        mark.clicked.connect(self._mark)
        modify = QPushButton("Modify Site")
        modify.clicked.connect(self._modify)
        delete = QPushButton("Delete")
        delete.clicked.connect(self._delete)
        instructions.addWidget(mark)
        instructions.addWidget(modify)
        instructions.addWidget(delete)
        left.addLayout(instructions)
        panes.addLayout(left, 3)
        right = QVBoxLayout()
        right.addWidget(QLabel("Selected Sites"))
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["Site", "X", "Y", "Images"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.itemSelectionChanged.connect(self._refresh_image_summary)
        right.addWidget(self.table, 1)
        right.addWidget(QLabel("Images"))
        image_tools = QHBoxLayout()
        self.image_channel = QComboBox()
        self.image_channel.addItems(["Channel 1", "Channel 2", "Channel 3", "All Channels"])
        self.image_channel.currentTextChanged.connect(self._refresh_image_summary)
        self.image_mode = QComboBox()
        self.image_mode.addItems(["Raw", "Segmented", "Overlay", "Blink"])
        self.image_mode.currentTextChanged.connect(self._refresh_image_summary)
        previous = QPushButton("Previous")
        previous.clicked.connect(lambda: self._navigate_site(-1))
        next_site = QPushButton("Next")
        next_site.clicked.connect(lambda: self._navigate_site(1))
        self.measure = QPushButton("Measure")
        self.measure.setCheckable(True)
        self.measure.toggled.connect(self._refresh_image_summary)
        self.show_overlay = QCheckBox("Show Overlay")
        self.show_overlay.setChecked(True)
        self.show_overlay.toggled.connect(self._refresh_image_summary)
        for widget in (
            self.image_channel, self.image_mode, previous, next_site,
            self.measure, self.show_overlay,
        ):
            image_tools.addWidget(widget)
        right.addLayout(image_tools)
        self.images = QLabel("Unavailable")
        self.images.setFrameStyle(QFrame.Panel | QFrame.Sunken)
        self.images.setMinimumHeight(180)
        self.images.setAlignment(Qt.AlignCenter)
        right.addWidget(self.images)
        zoom_row = QHBoxLayout()
        zoom_row.addWidget(QLabel("Zoom"))
        self.image_zoom = QSlider(Qt.Horizontal)
        self.image_zoom.setRange(50, 400)
        self.image_zoom.setValue(100)
        self.image_zoom.valueChanged.connect(self._refresh_image_summary)
        zoom_row.addWidget(self.image_zoom, 1)
        fit = QPushButton("Fit")
        fit.clicked.connect(lambda: self.image_zoom.setValue(100))
        zoom_row.addWidget(fit)
        right.addLayout(zoom_row)
        panes.addLayout(right, 2)
        root.addLayout(panes, 1)
        footer = QHBoxLayout()
        self.grab_mode = QComboBox()
        self.grab_mode.addItems(["Grab Missing Images", "Re-Grab all Images"])
        footer.addWidget(self.grab_mode)
        grab = QPushButton("Grab Images")
        grab.clicked.connect(self._grab)
        footer.addWidget(grab)
        self.progress = QProgressBar()
        footer.addWidget(self.progress, 1)
        abort = QPushButton("Abort")
        abort.clicked.connect(lambda: self.progress.setValue(0))
        footer.addWidget(abort)
        finish = QPushButton("Finish")
        finish.clicked.connect(self._finish)
        cancel = QPushButton("Cancel")
        cancel.clicked.connect(self.reject)
        footer.addWidget(finish)
        footer.addWidget(cancel)
        root.addLayout(footer)
        self._refresh()

    def _navigate_site(self, offset):
        if not self.result_sites:
            return
        row = self.table.currentRow()
        row = 0 if row < 0 else (row + int(offset)) % len(self.result_sites)
        self.table.selectRow(row)
        self._refresh_image_summary()

    def _refresh_image_summary(self, *_args):
        grabbed = sum(bool(site.get("grabbed")) for site in self.result_sites)
        row = self.table.currentRow()
        site = row + 1 if row >= 0 else "-"
        measurement = " | Distance 0.00 um" if self.measure.isChecked() else ""
        overlay = "On" if self.show_overlay.isChecked() else "Off"
        self.images.setText(
            f"{grabbed} site image set(s) available | Site {site}\n"
            f"{self.image_channel.currentText()} | {self.image_mode.currentText()} | "
            f"Zoom {self.image_zoom.value()}% | Overlay {overlay}{measurement}"
        )

    def _position_changed(self, position):
        self.current_position = list(position)

    def _mark(self):
        self.result_sites.append(
            {"x": self.current_position[0], "y": self.current_position[1], "grabbed": False}
        )
        self._refresh()

    def _modify(self):
        row = self.table.currentRow()
        if row >= 0:
            self.result_sites[row].update(
                {"x": self.current_position[0], "y": self.current_position[1], "grabbed": False}
            )
            self._refresh()

    def _delete(self):
        row = self.table.currentRow()
        if row >= 0:
            self.result_sites.pop(row)
            self._refresh()

    def _grab(self):
        if not self.result_sites:
            QMessageBox.warning(self, "Segmentation Image Grab", "Mark at least one site first.")
            return
        regrab = self.grab_mode.currentIndex() == 1
        targets = [site for site in self.result_sites if regrab or not site.get("grabbed")]
        for index, site in enumerate(targets):
            site["grabbed"] = True
            site["image_id"] = f"SEG-{self.result_sites.index(site) + 1:03d}"
            self.progress.setValue(int((index + 1) / max(1, len(targets)) * 100))
        self._refresh()

    def _finish(self):
        if not self.result_sites:
            QMessageBox.warning(
                self,
                "Segmentation Image Grab",
                "Mark at least one site before clicking Finish.",
            )
            return
        missing = [site for site in self.result_sites if not site.get("grabbed")]
        if missing:
            QMessageBox.warning(
                self,
                "Segmentation Image Grab",
                "Grab images for every selected site before clicking Finish.",
            )
            return
        self.accept()

    def _refresh(self):
        self.table.setRowCount(len(self.result_sites))
        for row, site in enumerate(self.result_sites):
            self.table.setItem(row, 0, QTableWidgetItem(str(row + 1)))
            self.table.setItem(row, 1, QTableWidgetItem(f"{site['x']:.4f}"))
            self.table.setItem(row, 2, QTableWidgetItem(f"{site['y']:.4f}"))
            self.table.setItem(row, 3, QTableWidgetItem("Available" if site.get("grabbed") else "Unavailable"))
        if self.result_sites and self.table.currentRow() < 0:
            self.table.selectRow(0)
        self._refresh_image_summary()
        self.canvas.sites = self.result_sites
        self.canvas.update()


class SiteCanvas(QWidget):
    def __init__(self, sites, on_position, parent=None):
        super().__init__(parent)
        self.sites = sites
        self.on_position = on_position
        self.position = (0.50, 0.50)
        self.setMinimumSize(480, 460)

    def mousePressEvent(self, event):
        pos = event.position() if hasattr(event, "position") else event.pos()
        self.position = (
            max(0.0, min(1.0, pos.x() / max(1, self.width()))),
            max(0.0, min(1.0, pos.y() / max(1, self.height()))),
        )
        self.on_position(self.position)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor("#6b8088"))
        painter.setPen(QPen(QColor("#8ea0a6"), 1))
        for offset in range(0, self.width(), 24):
            painter.drawLine(offset, 0, offset, self.height())
        for offset in range(0, self.height(), 24):
            painter.drawLine(0, offset, self.width(), offset)
        for index, site in enumerate(self.sites):
            x = int(site["x"] * self.width())
            y = int(site["y"] * self.height())
            painter.setPen(QPen(QColor("#ffdf00"), 2))
            painter.drawLine(x - 8, y, x + 8, y)
            painter.drawLine(x, y - 8, x, y + 8)
            painter.drawText(x + 10, y + 4, str(index + 1))
        x = int(self.position[0] * self.width())
        y = int(self.position[1] * self.height())
        painter.setPen(QPen(QColor("#ff3030"), 2))
        painter.drawLine(x - 12, y, x + 12, y)
        painter.drawLine(x, y - 12, x, y + 12)


class SegmentationSetupDialog(QDialog):
    def __init__(self, regions, care_groups, parent=None):
        super().__init__(parent)
        self.result_regions = deepcopy(regions or {})
        self.care_groups = care_groups or []
        self.current_region = ""
        self.current_channel = 0
        self.break_clipboard = None
        self._loading = False
        self.setWindowTitle("Segmentation Setup")
        self.resize(1120, 690)
        root = QHBoxLayout(self)
        left = QVBoxLayout()
        left.addWidget(QLabel("Select Region"))
        self.region_list = QListWidget()
        names = [group.get("name", f"Region {index + 1}") for index, group in enumerate(self.care_groups)]
        if not names:
            names = ["Default"]
        self.region_list.addItems(names)
        self.region_list.currentTextChanged.connect(self._region_changed)
        left.addWidget(self.region_list, 1)
        root.addLayout(left, 1)
        center = QVBoxLayout()
        center.addWidget(QLabel("Image View / Segmentation Map"))
        self.plot = SegmentationPlot()
        center.addWidget(self.plot, 1)
        root.addLayout(center, 4)
        controls = QVBoxLayout()
        controls.addWidget(QLabel("Channel"))
        self.channel = QComboBox()
        self.channel.addItems(["Channel 1", "Channel 2", "Channel 3"])
        self.channel.currentIndexChanged.connect(self._channel_changed)
        controls.addWidget(self.channel)
        controls.addWidget(QLabel("Segmentation Type"))
        self.segmentation_type = QComboBox()
        self.segmentation_type.addItems([
            "Off",
            "Median Based Segmentation",
            "Projection Based Segmentation",
            "Median-Edge Based Segmentation",
        ])
        self.segmentation_type.currentTextChanged.connect(self._type_changed)
        controls.addWidget(self.segmentation_type)
        controls.addWidget(QLabel("Use Segments From"))
        self.source = QComboBox()
        self.source.addItems(["Own Channel", "Channel 1", "Channel 2", "Channel 3"])
        self.source.currentTextChanged.connect(self._source_changed)
        controls.addWidget(self.source)
        controls.addWidget(QLabel("Projection Dilation"))
        self.dilation = QSpinBox()
        self.dilation.setRange(-64, 64)
        self.dilation.valueChanged.connect(self._dilation_changed)
        controls.addWidget(self.dilation)
        controls.addWidget(QLabel("Segment Breaks"))
        self.break_table = QTableWidget(0, 3)
        self.break_table.setHorizontalHeaderLabels(["Axis", "Position", "Group"])
        self.break_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.break_table.setMinimumHeight(165)
        self.break_table.setMaximumHeight(190)
        self.break_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.break_table.itemSelectionChanged.connect(self._break_selected)
        controls.addWidget(self.break_table)
        self.break_position = QDoubleSpinBox()
        self.break_position.setRange(0.01, 0.99)
        self.break_position.setDecimals(3)
        self.break_position.setSingleStep(0.01)
        self.break_position.valueChanged.connect(self._break_position_changed)
        controls.addWidget(QLabel("Break Position"))
        controls.addWidget(self.break_position)
        self.group_id = QSpinBox()
        self.group_id.setRange(0, 7)
        self.group_id.valueChanged.connect(self._group_changed)
        controls.addWidget(QLabel("Segment Group ID"))
        controls.addWidget(self.group_id)
        self.break_buttons = {}
        for label, handler in [
            ("Cut Histogram", lambda: self._add_break("Histogram")),
            ("Cut X Projection", lambda: self._add_break("X")),
            ("Cut Y Projection", lambda: self._add_break("Y")),
            ("Auto Breaks", self._auto_breaks),
            ("Delete Break", self._delete_break),
            ("Delete All", self._delete_all),
            ("Copy", self._copy),
            ("Paste", self._paste),
        ]:
            button = QPushButton(label)
            button.clicked.connect(handler)
            controls.addWidget(button)
            self.break_buttons[label] = button
        controls.addStretch(1)
        finish = QPushButton("Finish")
        finish.clicked.connect(self.accept)
        cancel = QPushButton("Cancel")
        cancel.clicked.connect(self.reject)
        controls.addWidget(finish)
        controls.addWidget(cancel)
        root.addLayout(controls, 2)
        self.region_list.setCurrentRow(0)

    def _ensure_region(self, name):
        if name not in self.result_regions:
            self.result_regions[name] = {
                "channels": [
                    {"type": "Off", "breaks": [], "dilation": 0, "source": "Own Channel"}
                    for _ in range(3)
                ]
            }
        return self.result_regions[name]

    def _region_changed(self, name):
        if not name:
            return
        self.current_region = name
        self._ensure_region(name)
        self._load_channel()

    def _channel_changed(self, index):
        self.current_channel = max(0, index)
        self._load_channel()

    def _current(self):
        region = self._ensure_region(self.current_region or "Default")
        return region["channels"][self.current_channel]

    def _load_channel(self):
        if not self.current_region:
            return
        self._loading = True
        channel = self._current()
        self.segmentation_type.setCurrentText(channel["type"])
        self.source.setCurrentText(channel.get("source", "Own Channel"))
        self.dilation.setValue(int(channel.get("dilation", 0)))
        cross_channel = channel["type"] in {
            "Projection Based Segmentation",
            "Median-Edge Based Segmentation",
        }
        self.source.setEnabled(cross_channel)
        selected_row = self.break_table.currentRow()
        self.break_table.setRowCount(len(channel["breaks"]))
        for row, item in enumerate(channel["breaks"]):
            self.break_table.setItem(row, 0, QTableWidgetItem(str(item.get("axis", ""))))
            self.break_table.setItem(row, 1, QTableWidgetItem(f"{float(item.get('position', 0.5)):.3f}"))
            self.break_table.setItem(row, 2, QTableWidgetItem(str(int(item.get("group", 0)))))
        if channel["breaks"]:
            self.break_table.selectRow(min(max(0, selected_row), len(channel["breaks"]) - 1))
        self._loading = False
        self.plot.segmentation_type = channel["type"]
        self.plot.breaks = channel["breaks"]
        self.plot.update()
        self._update_break_actions(channel["type"])
        self._break_selected()

    def _update_break_actions(self, segmentation_type):
        median = segmentation_type == "Median Based Segmentation"
        projection = segmentation_type in {
            "Projection Based Segmentation",
            "Median-Edge Based Segmentation",
        }
        self.break_buttons["Cut Histogram"].setEnabled(median)
        self.break_buttons["Cut X Projection"].setEnabled(projection)
        self.break_buttons["Cut Y Projection"].setEnabled(projection)
        self.break_buttons["Auto Breaks"].setEnabled(projection)

    def _break_selected(self):
        if self._loading:
            return
        row = self.break_table.currentRow()
        breaks = self._current()["breaks"]
        enabled = 0 <= row < len(breaks)
        self.break_position.setEnabled(enabled)
        self.group_id.setEnabled(enabled)
        if not enabled:
            return
        self._loading = True
        self.break_position.setValue(float(breaks[row].get("position", 0.5)))
        self.group_id.setValue(int(breaks[row].get("group", 0)))
        self._loading = False

    def _break_position_changed(self, value):
        if self._loading:
            return
        row = self.break_table.currentRow()
        breaks = self._current()["breaks"]
        if 0 <= row < len(breaks):
            breaks[row]["position"] = float(value)
            self._load_channel()

    def _group_changed(self, value):
        if self._loading:
            return
        row = self.break_table.currentRow()
        breaks = self._current()["breaks"]
        if 0 <= row < len(breaks):
            breaks[row]["group"] = int(value)
            self._load_channel()

    def _type_changed(self, value):
        if self._loading:
            return
        region = self._ensure_region(self.current_region)
        active_types = {
            channel["type"] for channel in region["channels"]
            if channel["type"] != "Off" and channel is not self._current()
        }
        if value != "Off" and active_types and value not in active_types:
            QMessageBox.warning(
                self,
                "Segmentation Type",
                "All enabled channels in a region must use the same Segmentation Type.",
            )
            self._loading = True
            self.segmentation_type.setCurrentText(next(iter(active_types)))
            self._loading = False
            value = next(iter(active_types))
        current = self._current()
        if current.get("type", "Off") != value:
            current["breaks"] = []
        current["type"] = value
        cross_channel = value in {
            "Projection Based Segmentation",
            "Median-Edge Based Segmentation",
        }
        self.source.setEnabled(cross_channel)
        if not cross_channel:
            current["source"] = "Own Channel"
            self._loading = True
            self.source.setCurrentText("Own Channel")
            self._loading = False
        self.plot.segmentation_type = value
        self.plot.breaks = current["breaks"]
        self._update_break_actions(value)
        self.plot.update()

    def _source_changed(self, value):
        if self._loading:
            return
        current = self._current()
        if value != "Own Channel" and current.get("type") not in {
            "Projection Based Segmentation",
            "Median-Edge Based Segmentation",
        }:
            QMessageBox.warning(
                self,
                "Use Segments From",
                "Cross-channel segmentation is available only for PBS or MEBS.",
            )
            self._loading = True
            self.source.setCurrentText("Own Channel")
            self._loading = False
            value = "Own Channel"
        current["source"] = value

    def _dilation_changed(self, value):
        if not self._loading:
            self._current()["dilation"] = int(value)

    def _add_break(self, axis):
        channel = self._current()
        if channel["type"] == "Off":
            QMessageBox.warning(self, "Segmentation Map", "Select a Segmentation Type first.")
            return
        if channel["type"] == "Median Based Segmentation" and axis != "Histogram":
            QMessageBox.warning(self, "Segmentation Map", "Median-based segmentation uses Cut Histogram.")
            return
        if channel["type"] != "Median Based Segmentation" and axis == "Histogram":
            QMessageBox.warning(self, "Segmentation Map", "Projection-based segmentation uses Cut X or Cut Y Projection.")
            return
        channel["breaks"].append(
            {
                "axis": axis,
                "position": min(0.90, 0.25 + len(channel["breaks"]) * 0.18),
                "group": self.group_id.value(),
            }
        )
        self._load_channel()
        self.break_table.selectRow(len(channel["breaks"]) - 1)

    def _auto_breaks(self):
        if "Projection" not in self._current()["type"] and "Median-Edge" not in self._current()["type"]:
            QMessageBox.information(self, "Auto Breaks", "Auto Breaks applies to Projection-based segmentation.")
            return
        self._current()["breaks"] = [
            {"axis": "X", "position": 0.36, "group": 0},
            {"axis": "Y", "position": 0.63, "group": 1},
        ]
        self._load_channel()

    def _delete_break(self):
        breaks = self._current()["breaks"]
        if breaks:
            row = self.break_table.currentRow()
            breaks.pop(row if 0 <= row < len(breaks) else -1)
            self._load_channel()

    def _delete_all(self):
        self._current()["breaks"] = []
        self._load_channel()

    def _copy(self):
        self.break_clipboard = deepcopy(self._current()["breaks"])

    def _paste(self):
        if self.break_clipboard is None:
            QMessageBox.information(self, "Paste Segments", "Copy Segment breaks first.")
            return
        if self._current()["type"] == "Off":
            QMessageBox.warning(self, "Paste Segments", "Select a Segmentation Type for the target channel first.")
            return
        self._current()["breaks"] = deepcopy(self.break_clipboard)
        self._load_channel()

    def _finish(self):
        errors = validate_segmentation_regions(self.result_regions)
        if errors:
            QMessageBox.warning(self, "Segmentation Setup", "\n".join(errors))
            return
        self.accept()


class SegmentationPlot(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.segmentation_type = "Off"
        self.breaks = []
        self.setMinimumSize(500, 430)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor("#20272a"))
        margin = 38
        painter.setPen(QPen(QColor("#aeb9bd"), 1))
        painter.drawLine(margin, self.height() - margin, self.width() - 20, self.height() - margin)
        painter.drawLine(margin, 20, margin, self.height() - margin)
        width = self.width() - margin - 24
        height = self.height() - 70
        painter.setPen(QPen(QColor("#72cee8"), 2))
        previous = None
        for index in range(max(1, width)):
            x = index / max(1, width - 1)
            if "Projection" in self.segmentation_type:
                value = 0.30 + 0.18 * (1 if int(x * 10) % 2 else 0)
            else:
                value = 0.18 + 0.72 * (1.0 - abs(2 * x - 1.0))
            point = (margin + index, self.height() - margin - int(value * height))
            if previous:
                painter.drawLine(previous[0], previous[1], point[0], point[1])
            previous = point
        colors = ["#ffdf00", "#ff5252", "#65df65", "#c987ff", "#48d7dc", "#ff9c45"]
        for index, item in enumerate(self.breaks):
            painter.setPen(QPen(QColor(colors[item.get("group", index) % len(colors)]), 3))
            position = float(item.get("position", 0.5))
            if item.get("axis") == "Y":
                y = int(20 + position * height)
                painter.drawLine(margin, y, self.width() - 20, y)
            else:
                x = int(margin + position * width)
                painter.drawLine(x, 20, x, self.height() - margin)


class SingleDieInspectionDialog(QDialog):
    def __init__(self, state, care_groups, parent=None):
        super().__init__(parent)
        self.result_state = deepcopy(state or default_segmentation_state()["sdi"])
        self.care_groups = care_groups or []
        self.setWindowTitle("Single Die Inspection")
        self.resize(1200, 700)
        self.setMinimumSize(1080, 620)
        root = QVBoxLayout(self)
        panes = QHBoxLayout()
        left = QVBoxLayout()
        left.addWidget(QLabel("Select Care Areas for SDI"))
        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(
            [
                "Care Area\nGroup", "SDI", "Pattern\nType", "Detected\nPattern",
                "Feature\nScore", "Minimum\nConsistency",
            ]
        )
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Fixed)
        for column, width in enumerate((145, 55, 210, 125, 95, 145)):
            self.table.setColumnWidth(column, width)
        self.table.verticalHeader().setDefaultSectionSize(34)
        self.table.setMinimumWidth(770)
        left.addWidget(self.table, 1)
        panes.addLayout(left, 4)
        right = QVBoxLayout()
        right.addWidget(QLabel("Images"))
        self.image_mode = QComboBox()
        self.image_mode.addItems(["Original", "Processed Image", "Graph with Peaks"])
        right.addWidget(self.image_mode)
        image_controls = QHBoxLayout()
        self.false_color = QCheckBox("False Color")
        image_controls.addWidget(self.false_color)
        self.auto_scale = QCheckBox("Auto Scale")
        self.auto_scale.setChecked(True)
        image_controls.addWidget(self.auto_scale)
        right.addLayout(image_controls)
        self.preview = SDIPreview(self.result_state)
        right.addWidget(self.preview, 1)
        self.zoom = QSlider(Qt.Horizontal)
        self.zoom.setRange(25, 300)
        self.zoom.setValue(100)
        self.zoom.setToolTip("Zoom SDI image")
        right.addWidget(self.zoom)
        panes.addLayout(right, 2)
        root.addLayout(panes, 1)
        buttons = QHBoxLayout()
        edit_box = QPushButton("Edit Box")
        edit_box.clicked.connect(self._edit_box)
        measure = QPushButton("Measure Cell Size")
        measure.clicked.connect(self._measure)
        self.measure_mode = QComboBox()
        self.measure_mode.addItems(["Measure Changed / Unmeasured", "Re-Grab Images"])
        sensitivity = QPushButton("Sensitivity...")
        sensitivity.clicked.connect(self._sensitivity)
        self.progress = QProgressBar()
        measure.setMinimumWidth(175)
        self.measure_mode.setMinimumWidth(220)
        buttons.addWidget(edit_box)
        buttons.addWidget(measure)
        buttons.addWidget(self.measure_mode)
        buttons.addWidget(sensitivity)
        buttons.addWidget(self.progress, 1)
        root.addLayout(buttons)
        footer = QHBoxLayout()
        footer.addStretch(1)
        finish = QPushButton("Finish")
        finish.clicked.connect(self._finish)
        cancel = QPushButton("Cancel")
        cancel.clicked.connect(self.reject)
        footer.addWidget(finish)
        footer.addWidget(cancel)
        root.addLayout(footer)
        self._populate()

    def _populate(self):
        names = [group.get("name", f"CAG {index + 1}") for index, group in enumerate(self.care_groups)]
        self.table.clearContents()
        self.table.setRowCount(len(names))
        stored = self.result_state.setdefault("groups", {})
        for row, name in enumerate(names):
            record = stored.setdefault(
                name,
                {
                    "enabled": False,
                    "pattern_type": "Auto",
                    "feature_score": None,
                    "minimum_consistency": None,
                    "detected_pattern_type": "-",
                    "needs_regrab": True,
                },
            )
            self.table.setItem(row, 0, QTableWidgetItem(name))
            enabled = QCheckBox()
            enabled.setChecked(bool(record.get("enabled")))
            enabled.toggled.connect(lambda checked, key=name: self._set_group(key, "enabled", checked))
            self.table.setCellWidget(row, 1, enabled)
            pattern = QComboBox()
            pattern.addItems(["Auto", "Force Horizontal", "Force Vertical"])
            pattern.setCurrentText(
                record.get("pattern_type", "Auto")
                if record.get("pattern_type", "Auto") in {"Auto", "Force Horizontal", "Force Vertical"}
                else "Auto"
            )
            pattern.currentTextChanged.connect(
                lambda value, key=name: self._set_group(key, "pattern_type", value)
            )
            self.table.setCellWidget(row, 2, pattern)
            self.table.setItem(
                row, 3, QTableWidgetItem(record.get("detected_pattern_type", "-"))
            )
            score = record.get("feature_score")
            score_item = QTableWidgetItem("-" if score is None else f"{score:.1f}")
            if score is not None:
                score_item.setForeground(
                    QColor("#138a32" if score >= 75 else "#bb8200" if score >= 50 else "#c43131")
                )
            self.table.setItem(row, 4, score_item)
            consistency = record.get("minimum_consistency")
            self.table.setItem(
                row,
                5,
                QTableWidgetItem("-" if consistency is None else f"{consistency:.3f}"),
            )

    def _set_group(self, name, key, value):
        record = self.result_state["groups"][name]
        if record.get(key) != value:
            record[key] = value
            record["needs_regrab"] = True
            self.result_state["measured"] = False

    def _measure(self):
        selected = [
            (name, record)
            for name, record in self.result_state.get("groups", {}).items()
            if record.get("enabled")
        ]
        if not selected:
            QMessageBox.warning(self, "Single Die Inspection", "Select at least one Care Area Group for SDI.")
            return
        regrab_all = self.measure_mode.currentIndex() == 1
        targets = [
            item for item in selected
            if regrab_all or item[1].get("needs_regrab", item[1].get("feature_score") is None)
        ]
        if not targets:
            QMessageBox.information(
                self,
                "Single Die Inspection",
                "All selected Care Area Groups already have current images.",
            )
            return
        detected = ["Horizontal", "Vertical", "Array"]
        for index, (name, record) in enumerate(targets):
            record["feature_score"] = round(82.0 - index * 6.4, 1)
            record["minimum_consistency"] = (
                round(max(0.0, 0.94 - index * 0.07), 3)
                if int(record.get("box_count", 1)) > 1
                else None
            )
            record["cell_pitch_x"] = round(0.65 + index * 0.08, 3)
            record["cell_pitch_y"] = round(0.72 + index * 0.06, 3)
            pattern = record.get("pattern_type", "Auto")
            record["detected_pattern_type"] = (
                pattern[len("Force "):]
                if pattern.startswith("Force ")
                else detected[index % len(detected)]
            )
            record["needs_regrab"] = False
            self.progress.setValue(int((index + 1) / len(targets) * 100))
        self.result_state["measured"] = all(
            record.get("feature_score") is not None and not record.get("needs_regrab")
            for _, record in selected
        )
        self._populate()
        self.preview.update()

    def _edit_box(self):
        dialog = SDIImageBoxDialog(self.result_state.get("image_box"), self)
        result = dialog.exec() if hasattr(dialog, "exec") else dialog.exec_()
        if result == QDialog.Accepted:
            self.result_state["image_box"] = dialog.result_box
            self.result_state["measured"] = False
            for record in self.result_state.get("groups", {}).values():
                if record.get("enabled"):
                    record["needs_regrab"] = True
            self.preview.update()

    def _sensitivity(self):
        dialog = SDISensitivityDialog(
            self.result_state.get("sensitivity"),
            list(self.result_state.get("groups", {})),
            self,
        )
        result = dialog.exec() if hasattr(dialog, "exec") else dialog.exec_()
        if result == QDialog.Accepted:
            self.result_state["sensitivity"] = dialog.result_state

    def _finish(self):
        enabled = [
            record for record in self.result_state.get("groups", {}).values()
            if record.get("enabled")
        ]
        if enabled and not self.result_state.get("measured"):
            QMessageBox.warning(
                self,
                "Single Die Inspection",
                "Measure Cell Size for every selected Care Area Group before Finish.",
            )
            return
        self.accept()


class SDISensitivityDialog(QDialog):
    def __init__(self, state, region_names, parent=None):
        super().__init__(parent)
        self.result_state = deepcopy(state or {})
        self.setWindowTitle("SDI Sensitivity Parameters")
        self.resize(760, 380)
        root = QVBoxLayout(self)
        root.addWidget(QLabel("Algorithm Parameters"))
        self.table = QTableWidget(len(region_names), 5)
        self.table.setHorizontalHeaderLabels(
            ["Select Region", "Run SDI", "Run CF SDI", "Secondary SDI", "Threshold"]
        )
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        for row, name in enumerate(region_names):
            record = self.result_state.setdefault(
                name,
                {
                    "run_sdi": False,
                    "run_cf_sdi": False,
                    "run_secondary_sdi": False,
                    "threshold": 45.0,
                },
            )
            self.table.setItem(row, 0, QTableWidgetItem(name))
            for column, key in enumerate(
                ("run_sdi", "run_cf_sdi", "run_secondary_sdi"), start=1
            ):
                control = QCheckBox()
                control.setChecked(bool(record.get(key)))
                self.table.setCellWidget(row, column, control)
            self.table.setItem(
                row, 4, QTableWidgetItem(f"{float(record.get('threshold', 45.0)):g}")
            )
        root.addWidget(self.table)
        buttons = QHBoxLayout()
        buttons.addStretch(1)
        ok = QPushButton("OK")
        ok.clicked.connect(self._finish)
        cancel = QPushButton("Cancel")
        cancel.clicked.connect(self.reject)
        buttons.addWidget(ok)
        buttons.addWidget(cancel)
        root.addLayout(buttons)

    def _finish(self):
        for row in range(self.table.rowCount()):
            name = self.table.item(row, 0).text()
            try:
                threshold = float(self.table.item(row, 4).text())
            except (AttributeError, TypeError, ValueError):
                QMessageBox.warning(self, "SDI Sensitivity", f"{name}: Threshold must be numeric.")
                return
            if threshold < 0:
                QMessageBox.warning(self, "SDI Sensitivity", f"{name}: Threshold cannot be negative.")
                return
            self.result_state[name].update(
                {
                    "run_sdi": self.table.cellWidget(row, 1).isChecked(),
                    "run_cf_sdi": self.table.cellWidget(row, 2).isChecked(),
                    "run_secondary_sdi": self.table.cellWidget(row, 3).isChecked(),
                    "threshold": threshold,
                }
            )
        self.accept()


class SDIPreview(QWidget):
    def __init__(self, state, parent=None):
        super().__init__(parent)
        self.state = state
        self.setMinimumSize(360, 420)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor("#5e737b"))
        painter.setPen(QPen(QColor("#80949b"), 1))
        for offset in range(0, self.width(), 18):
            painter.drawLine(offset, 0, offset, self.height())
        for offset in range(0, self.height(), 18):
            painter.drawLine(0, offset, self.width(), offset)
        x, y, width, height = self.state.get("image_box", [0.2, 0.2, 0.35, 0.35])
        painter.setBrush(Qt.NoBrush)
        painter.setPen(QPen(QColor("#ffdf00"), 3))
        painter.drawRect(
            int(x * self.width()),
            int(y * self.height()),
            int(width * self.width()),
            int(height * self.height()),
        )
        painter.setPen(QPen(QColor("#ffffff"), 1))
        painter.drawText(14, 24, "Channels 1 / 2 / 3")


class SDIImageBoxDialog(QDialog):
    def __init__(self, box, parent=None):
        super().__init__(parent)
        self.result_box = list(box or [0.20, 0.20, 0.35, 0.35])
        self.setWindowTitle("Modify SDI Image Box")
        self.setFixedSize(430, 300)
        layout = QGridLayout(self)
        self.controls = []
        for row, (label, value) in enumerate(zip(["X:", "Y:", "Width:", "Height:"], self.result_box)):
            control = QDoubleSpinBox()
            control.setRange(0.01, 0.98)
            control.setDecimals(3)
            control.setValue(float(value))
            self.controls.append(control)
            layout.addWidget(QLabel(label), row, 0)
            layout.addWidget(control, row, 1)
        mark = QPushButton("Mark and Advance")
        mark.clicked.connect(self._finish)
        cancel = QPushButton("Cancel")
        cancel.clicked.connect(self.reject)
        layout.addWidget(mark, 5, 0)
        layout.addWidget(cancel, 5, 1)

    def _finish(self):
        x, y, width, height = [control.value() for control in self.controls]
        if x + width > 1.0 or y + height > 1.0:
            QMessageBox.warning(self, "SDI Image Box", "The image box must remain inside the die.")
            return
        self.result_box = [x, y, width, height]
        self.accept()
