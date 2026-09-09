from __future__ import annotations

from copy import deepcopy
from typing import Optional

from ...qt_compat import (
    QColor,
    QComboBox,
    QDialog,
    QDoubleSpinBox,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QListWidget,
    QMenuBar,
    QMessageBox,
    QPainter,
    QPen,
    QPushButton,
    QRadioButton,
    QSpinBox,
    QStyle,
    QTableWidget,
    QTableWidgetItem,
    Qt,
    QTimer,
    QVBoxLayout,
    QWidget,
)


SIMULATED_ALIGNMENT_IMAGES = [
    "Sim Cross Mark 1 (DF)",
    "Sim Cross Mark 2 (DF)",
    "Sim Cross Mark 3 (BF)",
    "Sim Cross Mark Offset",
]


class ImageDisplayWindow(QDialog):
    def __init__(
        self,
        parent: Optional[QWidget] = None,
        *,
        embedded: bool = False,
        alignment_mode: str = "DF",
    ):
        super().__init__(parent)
        self.embedded = bool(embedded)
        self.alignment_mode = "BF" if str(alignment_mode).upper() == "BF" else "DF"
        self.bf_magnification = "Low Mag"
        self.setWindowTitle("Image Display Window")
        if self.embedded:
            self.setWindowFlags(Qt.Widget)
            self.setMinimumSize(0, 0)
        else:
            self.resize(960, 790)
            self.setMinimumSize(900, 700)
        self.image_count = 0
        self.available_images = ["1 (Left)", "2 (Right)", "3 (Center)", *SIMULATED_ALIGNMENT_IMAGES]
        self.cycle_images = ["Sim Cross Mark 1 (DF)", "Sim Cross Mark 2 (DF)", "Sim Cross Mark 3 (BF)"]
        self.cycle_delay_seconds = 1.0
        self.use_current_optics_for_alignment = False
        self.loaded_optics_source = "Current Machine"
        self.advanced_optics_state = None
        self.cycle_timer = QTimer(self)
        self.cycle_timer.timeout.connect(self._cycle_next_image)
        self._build_ui()
        self.set_alignment_mode(self.alignment_mode)

    def _build_ui(self):
        self.setStyleSheet(
            """
            QDialog {
                background: #c9c5bb;
                color: #111111;
                font-family: Arial, Helvetica, sans-serif;
                font-size: 10px;
            }
            QMenuBar {
                background: #d7d4cc;
                border-bottom: 1px solid #8c8982;
            }
            QMenuBar::item {
                padding: 2px 7px;
            }
            QPushButton {
                background: #e5e2d8;
                border-top: 1px solid #ffffff;
                border-left: 1px solid #ffffff;
                border-right: 1px solid #77736b;
                border-bottom: 1px solid #77736b;
                min-height: 22px;
                padding: 1px 8px;
            }
            QPushButton:disabled, QComboBox:disabled, QLineEdit:disabled {
                color: #8d8a83;
                background: #d2cec4;
            }
            QPushButton:checked {
                background: #c7d9e8;
                border: 1px solid #3b6e91;
                font-weight: 700;
            }
            QFrame#toolStrip, QFrame#leftPanel, QFrame#statusStrip {
                background: #c9c5bb;
                border: 1px solid #8f8b82;
            }
            QFrame#groupPanel {
                background: #c9c5bb;
                border: 1px solid #8f8b82;
            }
            QComboBox, QLineEdit, QSpinBox {
                background: #ffffff;
                border: 1px solid #77736b;
                min-height: 20px;
            }
            QTableWidget {
                background: #f4f4f0;
                border: 1px solid #77736b;
                gridline-color: #9d9990;
            }
            """
        )

        root = QVBoxLayout(self)
        root.setContentsMargins(2, 2, 2, 2)
        root.setSpacing(2)

        self.window_menu_bar = self._menu_bar()
        root.addWidget(self.window_menu_bar)
        root.addWidget(self._tool_strip())

        content = QHBoxLayout()
        content.setSpacing(2)
        content.addWidget(self._left_panel(), 0)
        content.addWidget(self._image_panel(), 1)
        root.addLayout(content, 1)
        root.addWidget(self._status_strip())
        self._display_current_image(self.current_image.currentText())

    def _menu_bar(self) -> QMenuBar:
        menu = QMenuBar()
        file_menu = menu.addMenu("File")
        file_menu.addAction("Save Current Image...", self._save_current_image)
        view_menu = menu.addMenu("View")
        view_menu.addAction("Image Display").setEnabled(False)
        actions_menu = menu.addMenu("Actions")
        actions_menu.addAction("Acquire", self._acquire_image)
        actions_menu.addAction("Cycle Image Setup...", self._open_cycle_image_setup)
        actions_menu.addAction("Advanced Optics...", self._open_advanced_optics)
        stage_menu = menu.addMenu("Move Stage")
        stage_menu.addAction("Move to Origin", self._reset_stage)
        color_menu = menu.addMenu("Color")
        color_menu.addAction("Toggle Target Highlight", self._toggle_highlight)
        zoom_menu = menu.addMenu("Zoom")
        for percent in (50, 100, 200):
            zoom_menu.addAction(f"{percent}%", lambda checked=False, value=percent: self._set_zoom(value))
        help_menu = menu.addMenu("Help")
        help_menu.addAction(
            "Image Display Help",
            lambda: QMessageBox.information(
                self,
                "Image Display Help",
                "Use Acquire to capture the simulated stage image and the arrow controls to move the stage.",
            ),
        )
        return menu

    def _tool_strip(self) -> QFrame:
        strip = QFrame()
        strip.setObjectName("toolStrip")
        layout = QHBoxLayout(strip)
        layout.setContentsMargins(5, 3, 5, 3)
        layout.setSpacing(6)

        tools = [
            (QStyle.SP_DialogSaveButton, "Save Current Image", self._save_current_image),
            (QStyle.SP_DirOpenIcon, "Acquire Image", self._acquire_image),
            (QStyle.SP_FileDialogDetailedView, "Advanced Optics", self._open_advanced_optics),
            (QStyle.SP_ArrowUp, "Previous Image", self._show_previous_image),
            (QStyle.SP_ArrowDown, "Next Image", self._show_next_image),
        ]
        for icon, tooltip, handler in tools:
            button = QPushButton("")
            button.setFixedSize(26, 24)
            button.setIcon(self.style().standardIcon(icon))
            button.setToolTip(tooltip)
            button.clicked.connect(handler)
            layout.addWidget(button)

        self.center_image_button = QPushButton("Center Image")
        self.center_image_button.setFixedWidth(82)
        self.center_image_button.clicked.connect(lambda: self._set_zoom(100))
        layout.addWidget(self.center_image_button)
        layout.addWidget(QLabel("X:"))
        self.x_edit = QLineEdit("0.000")
        self.x_edit.setFixedWidth(58)
        layout.addWidget(self.x_edit)
        layout.addWidget(QLabel("Y:"))
        self.y_edit = QLineEdit("0.000")
        self.y_edit.setFixedWidth(58)
        layout.addWidget(self.y_edit)
        layout.addWidget(StagePositionWidget())
        self.zoom_combo = QComboBox()
        self.zoom_combo.addItems(["50 %", "100 %", "200 %"])
        self.zoom_combo.setCurrentText("100 %")
        self.zoom_combo.setFixedWidth(62)
        self.zoom_combo.currentTextChanged.connect(
            lambda text: self._set_zoom(int(text.split()[0]))
        )
        layout.addWidget(self.zoom_combo)
        zoom_button = QPushButton("Zoom (%)")
        zoom_button.setFixedWidth(76)
        zoom_button.clicked.connect(lambda: self._set_zoom(100))
        layout.addWidget(zoom_button)
        layout.addStretch(1)
        return strip

    def _left_panel(self) -> QFrame:
        panel = QFrame()
        panel.setObjectName("leftPanel")
        panel.setFixedWidth(230 if self.embedded else 300)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(4)
        layout.addWidget(self._relative_motion_panel(), 0)
        layout.addWidget(self._optics_panel(), 1)
        return panel

    def _relative_motion_panel(self) -> QFrame:
        panel = QFrame()
        panel.setObjectName("groupPanel")
        panel.setFixedHeight(220 if self.embedded else 250)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(8, 4, 8, 8)
        layout.setSpacing(6)
        layout.addWidget(QLabel("Relative Motion"))

        grid = QGridLayout()
        grid.setSpacing(2)
        moves = [
            (0, 0, "\\", -1, -1),
            (0, 1, "^", 0, -1),
            (0, 2, "/", 1, -1),
            (1, 0, "<", -1, 0),
            (1, 2, ">", 1, 0),
            (2, 0, "/", -1, 1),
            (2, 1, "v", 0, 1),
            (2, 2, "\\", 1, 1),
        ]
        for row, column, text, dx, dy in moves:
            button = QPushButton(text)
            button.setFixedSize(28, 25)
            button.setStyleSheet("color: #0b20d0; font-weight: 700;")
            button.clicked.connect(lambda checked=False, dx=dx, dy=dy: self._move_stage(dx, dy))
            grid.addWidget(button, row, column)
        center = QFrame()
        center.setFixedSize(28, 25)
        center.setStyleSheet("background: #d6d2c8; border: 1px solid #aaa69c;")
        grid.addWidget(center, 1, 1)
        grid.setColumnStretch(3, 1)
        layout.addLayout(grid)

        fixed_row = QHBoxLayout()
        self.custom_step_radio = QRadioButton()
        fixed_row.addWidget(self.custom_step_radio)
        self.custom_motion_step = QDoubleSpinBox()
        self.custom_motion_step.setDecimals(3)
        self.custom_motion_step.setRange(0.001, 100000.0)
        self.custom_motion_step.setValue(100.0)
        self.custom_motion_step.setSuffix(" um")
        fixed_row.addWidget(self.custom_motion_step, 1)
        layout.addLayout(fixed_row)

        step_row = QHBoxLayout()
        self.preset_step_radio = QRadioButton()
        self.preset_step_radio.setChecked(True)
        step_row.addWidget(self.preset_step_radio)
        self.motion_step = QComboBox()
        self.motion_step.addItems(["500 um", "250 um", "100 um", "50 um"])
        step_row.addWidget(self.motion_step, 1)
        layout.addLayout(step_row)
        layout.addStretch(1)
        return panel

    def _optics_panel(self) -> QFrame:
        panel = QFrame()
        panel.setObjectName("groupPanel")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(8, 10, 8, 8)
        layout.setSpacing(5)

        form = QGridLayout()
        form.setHorizontalSpacing(5)
        form.setVerticalSpacing(4)
        self.optics_controls = {}
        for row, (label, values) in enumerate(
            [
                ("Pixel Size:", ["SL8685", "SL8686"]),
                ("Sample Rate:", ["3.2(Default)", "1.6", "6.4"]),
                ("Incidence:", ["Oblique", "Normal"]),
                ("Polarization:", ["P-POL", "S-POL"]),
            ]
        ):
            form.addWidget(QLabel(label), row, 0)
            combo = QComboBox()
            combo.addItems(values)
            combo.setFixedWidth(118)
            form.addWidget(combo, row, 1)
            self.optics_controls[label.rstrip(":")] = combo
        form.addWidget(QLabel("Focus Offset:"), 4, 0)
        self.optics_focus = QLineEdit("0.001 um")
        self.optics_focus.setFixedWidth(80)
        form.addWidget(self.optics_focus, 4, 1)
        layout.addLayout(form)

        self.optics_table = QTableWidget(3, 6)
        self.optics_table.setHorizontalHeaderLabels(["Ch", "On", "Pol", "Light", "IRIS", "Mode"])
        self.optics_table.verticalHeader().setVisible(False)
        self.optics_table.setFixedHeight(92)
        rows = [
            ["1", "x", "S", "9.99", "OPEN", "DDark"],
            ["2", "x", "S", "9.99", "OPEN", "DDark"],
            ["3", "x", "S", "9.99", "OPEN", "Dark"],
        ]
        for row, values in enumerate(rows):
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                if column == 1:
                    item.setCheckState(Qt.Checked)
                    item.setText("")
                self.optics_table.setItem(row, column, item)
        self.optics_table.resizeColumnsToContents()
        layout.addWidget(self.optics_table)

        buttons = QHBoxLayout()
        advanced = QPushButton("Advanced Optics...")
        advanced.setFixedWidth(118)
        advanced.clicked.connect(self._open_advanced_optics)
        buttons.addWidget(advanced)
        buttons.addStretch(1)
        layout.addLayout(buttons)
        self.use_for_alignment_button = QPushButton("Use for Alignment...")
        self.use_for_alignment_button.setFixedWidth(118)
        self.use_for_alignment_button.clicked.connect(self._use_for_alignment)
        layout.addWidget(self.use_for_alignment_button)

        layout.addSpacing(10)
        layout.addWidget(QLabel("Optics Source:"))
        source_row = QHBoxLayout()
        self.optics_source = QComboBox()
        self.optics_source.addItems(
            ["Current Machine", "Alignment", "Test 1 Optics", "Test 2 Optics", "Test 3 Optics"]
        )
        source_row.addWidget(self.optics_source)
        load = QPushButton("Load")
        load.setFixedWidth(50)
        load.clicked.connect(self._load_optics_source)
        source_row.addWidget(load)
        layout.addLayout(source_row)
        return panel

    def _image_panel(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(4, 0, 4, 0)
        layout.setSpacing(4)

        view_mode_row = QHBoxLayout()
        view_mode_row.setSpacing(6)
        view_mode_row.addWidget(QLabel("Image Display"))
        view_mode_row.addStretch(1)
        view_mode_row.addWidget(QLabel("Imaging Mode:"))
        self.imaging_mode_combo = QComboBox()
        self.imaging_mode_combo.addItems(["DF", "BF"])
        self.imaging_mode_combo.setFixedWidth(58)
        self.imaging_mode_combo.currentTextChanged.connect(self.set_alignment_mode)
        view_mode_row.addWidget(self.imaging_mode_combo)
        self.bf_magnification_panel = QWidget()
        magnification_layout = QHBoxLayout(self.bf_magnification_panel)
        magnification_layout.setContentsMargins(0, 0, 0, 0)
        magnification_layout.setSpacing(2)
        magnification_layout.addWidget(QLabel("Magnification:"))
        self.low_mag_button = QPushButton("Low Mag")
        self.high_mag_button = QPushButton("High Mag")
        for button in (self.low_mag_button, self.high_mag_button):
            button.setCheckable(True)
            button.setFixedWidth(72)
            magnification_layout.addWidget(button)
        self.low_mag_button.clicked.connect(lambda: self._set_bf_magnification("Low Mag"))
        self.high_mag_button.clicked.connect(lambda: self._set_bf_magnification("High Mag"))
        view_mode_row.addWidget(self.bf_magnification_panel)
        layout.addLayout(view_mode_row)

        viewport_row = QHBoxLayout()
        self.viewport = ImageViewport(compact=self.embedded)
        viewport_row.addWidget(self.viewport, 1)
        viewport_row.addWidget(IntensityScale(), 0)
        layout.addLayout(viewport_row, 1)

        bottom = QHBoxLayout()
        acquire = QPushButton("Acquire")
        acquire.setFixedWidth(88)
        acquire.clicked.connect(self._acquire_image)
        bottom.addWidget(acquire)
        bottom.addWidget(QLabel("Current\nImage:"))
        self.current_image = QComboBox()
        self.current_image.addItems(self.available_images)
        self.current_image.currentTextChanged.connect(self._display_current_image)
        bottom.addWidget(self.current_image, 1)

        previous = QPushButton("")
        previous.setToolTip("Previous Image")
        previous.setIcon(self.style().standardIcon(QStyle.SP_ArrowBack))
        previous.setFixedSize(30, 26)
        previous.clicked.connect(self._show_previous_image)
        bottom.addWidget(previous)

        next_image = QPushButton("")
        next_image.setToolTip("Next Image")
        next_image.setIcon(self.style().standardIcon(QStyle.SP_ArrowForward))
        next_image.setFixedSize(30, 26)
        next_image.clicked.connect(self._show_next_image)
        bottom.addWidget(next_image)

        self.start_cycle_button = QPushButton("")
        self.start_cycle_button.setToolTip("Start Cycling")
        self.start_cycle_button.setIcon(self.style().standardIcon(QStyle.SP_MediaPlay))
        self.start_cycle_button.setFixedSize(30, 26)
        self.start_cycle_button.clicked.connect(self._start_cycling)
        bottom.addWidget(self.start_cycle_button)

        self.stop_cycle_button = QPushButton("")
        self.stop_cycle_button.setToolTip("Stop Cycling")
        self.stop_cycle_button.setIcon(self.style().standardIcon(QStyle.SP_MediaStop))
        self.stop_cycle_button.setFixedSize(30, 26)
        self.stop_cycle_button.setEnabled(False)
        self.stop_cycle_button.clicked.connect(self._stop_cycling)
        bottom.addWidget(self.stop_cycle_button)

        more = QPushButton("...")
        more.setToolTip("Cycle Image Setup")
        more.setFixedSize(36, 26)
        more.clicked.connect(self._open_cycle_image_setup)
        bottom.addWidget(more)
        layout.addLayout(bottom)
        return panel

    def _status_strip(self) -> QFrame:
        strip = QFrame()
        strip.setObjectName("statusStrip")
        strip.setFixedHeight(20)
        layout = QHBoxLayout(strip)
        layout.setContentsMargins(4, 0, 4, 0)
        layout.addWidget(QLabel("For Help, press F1"))
        layout.addStretch(1)
        self.status_label = QLabel("X =")
        layout.addWidget(self.status_label)
        layout.addWidget(QLabel("Y ="))
        layout.addWidget(QLabel("Intensity ="))
        return strip

    def _move_stage(self, dx: int, dy: int):
        if self.custom_step_radio.isChecked():
            step = self.custom_motion_step.value()
        else:
            step_text = self.motion_step.currentText().split()[0]
            step = float(step_text)
        x = self._field_value(self.x_edit) + dx * step
        y = self._field_value(self.y_edit) + dy * step
        self.x_edit.setText(f"{x:.3f}")
        self.y_edit.setText(f"{y:.3f}")
        self.status_label.setText(f"X = {x:.3f} um")

    def _reset_stage(self):
        self.x_edit.setText("0.000")
        self.y_edit.setText("0.000")
        self.status_label.setText("Stage moved to origin")

    def _toggle_highlight(self):
        self.viewport.highlight = not self.viewport.highlight
        self.viewport.update()

    def _set_zoom(self, percent: int):
        percent = min(200, max(50, int(percent)))
        self.viewport.zoom_percent = percent
        if hasattr(self, "zoom_combo") and self.zoom_combo.currentText() != f"{percent} %":
            self.zoom_combo.blockSignals(True)
            self.zoom_combo.setCurrentText(f"{percent} %")
            self.zoom_combo.blockSignals(False)
        self.viewport.update()
        if hasattr(self, "status_label"):
            self.status_label.setText(f"Image zoom {percent}%")

    def _save_current_image(self):
        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Save Current Image",
            "image-display.png",
            "PNG Image (*.png);;JPEG Image (*.jpg *.jpeg)",
        )
        if not filename:
            return
        if not self.viewport.grab().save(filename):
            QMessageBox.warning(self, "Save Current Image", "The image could not be saved.")
            return
        self.status_label.setText(f"Saved image to {filename}")

    def _acquire_image(self):
        self.image_count += 1
        x = self._field_value(self.x_edit)
        y = self._field_value(self.y_edit)
        enabled_channels = [
            row + 1
            for row in range(self.optics_table.rowCount())
            if self.optics_table.item(row, 1).checkState() == Qt.Checked
        ]
        if not enabled_channels:
            QMessageBox.warning(self, "Acquire", "Select at least one channel in the On column.")
            return
        labels = []
        channel_names = {1: "Left", 2: "Right", 3: "Center"}
        for channel in enabled_channels:
            label = (
                f"Capture {self.image_count} - Channel {channel} ({channel_names[channel]}) "
                f"({x:.0f},{y:.0f})"
            )
            labels.append(label)
            self.available_images.append(label)
            self.current_image.addItem(label)
        self.current_image.setCurrentText(labels[-1])
        self.status_label.setText(f"Acquired {len(labels)} channel image(s)")
        self.viewport.highlight = not self.viewport.highlight
        self.viewport.update()

    def _display_current_image(self, image_name: str):
        self.viewport.set_image(image_name)
        if image_name and hasattr(self, "status_label"):
            self.status_label.setText(f"Viewing {image_name}")

    def set_alignment_mode(self, mode: str):
        self.alignment_mode = "BF" if str(mode).upper() == "BF" else "DF"
        if hasattr(self, "imaging_mode_combo") and self.imaging_mode_combo.currentText() != self.alignment_mode:
            self.imaging_mode_combo.blockSignals(True)
            self.imaging_mode_combo.setCurrentText(self.alignment_mode)
            self.imaging_mode_combo.blockSignals(False)
        if hasattr(self, "bf_magnification_panel"):
            self.bf_magnification_panel.setVisible(self.alignment_mode == "BF")
            self.low_mag_button.setChecked(self.bf_magnification == "Low Mag")
            self.high_mag_button.setChecked(self.bf_magnification == "High Mag")
        if hasattr(self, "viewport"):
            self.viewport.set_alignment_view(self.alignment_mode, self.bf_magnification)
        if hasattr(self, "current_image"):
            target_image = (
                "Sim Cross Mark 3 (BF)"
                if self.alignment_mode == "BF"
                else "Sim Cross Mark 1 (DF)"
            )
            self.current_image.setCurrentText(target_image)
        if hasattr(self, "status_label"):
            suffix = f" - {self.bf_magnification}" if self.alignment_mode == "BF" else ""
            self.status_label.setText(f"{self.alignment_mode} image display{suffix}")

    def _set_bf_magnification(self, magnification: str):
        self.bf_magnification = "High Mag" if magnification == "High Mag" else "Low Mag"
        self.low_mag_button.setChecked(self.bf_magnification == "Low Mag")
        self.high_mag_button.setChecked(self.bf_magnification == "High Mag")
        self.viewport.set_alignment_view("BF", self.bf_magnification)
        self.status_label.setText(f"BF image display - {self.bf_magnification}")

    def _show_previous_image(self):
        self._select_relative_image(-1)

    def _show_next_image(self):
        self._select_relative_image(1)

    def _select_relative_image(self, direction: int):
        total = self.current_image.count()
        if total <= 0:
            return
        next_index = (self.current_image.currentIndex() + direction) % total
        self.current_image.setCurrentIndex(next_index)

    def _start_cycling(self):
        if not self.cycle_images:
            self.cycle_images = [self.current_image.itemText(index) for index in range(self.current_image.count())]
        if not self.cycle_images:
            return
        if self.current_image.currentText() not in self.cycle_images:
            self.current_image.setCurrentText(self.cycle_images[0])
        self.cycle_timer.start(max(100, int(self.cycle_delay_seconds * 1000)))
        self.start_cycle_button.setEnabled(False)
        self.stop_cycle_button.setEnabled(True)
        self.status_label.setText("Cycling images")

    def _stop_cycling(self):
        self.cycle_timer.stop()
        self.start_cycle_button.setEnabled(True)
        self.stop_cycle_button.setEnabled(False)
        self.status_label.setText("Image cycling stopped")

    def _cycle_next_image(self):
        if not self.cycle_images:
            self._stop_cycling()
            return
        current = self.current_image.currentText()
        try:
            current_cycle_index = self.cycle_images.index(current)
        except ValueError:
            current_cycle_index = -1
        next_image = self.cycle_images[(current_cycle_index + 1) % len(self.cycle_images)]
        self.current_image.setCurrentText(next_image)

    def _open_cycle_image_setup(self):
        dialog = CycleImageSetupDialog(
            self.available_images,
            self.cycle_images,
            self.cycle_delay_seconds,
            self,
        )
        result = dialog.exec() if hasattr(dialog, "exec") else dialog.exec_()
        if result == QDialog.Accepted:
            self.cycle_images = dialog.result_cycle_images
            self.cycle_delay_seconds = dialog.result_delay_seconds
            if dialog.play_requested:
                self._start_cycling()

    def _open_advanced_optics(self):
        dialog = AdvancedOpticsDialog(self, state=self.advanced_optics_state)
        result = dialog.exec() if hasattr(dialog, "exec") else dialog.exec_()
        if result == QDialog.Accepted and dialog.result_settings:
            self.advanced_optics_state = deepcopy(dialog.result_settings)
            self.status_label.setText("Advanced inspection optics updated")

    def _load_optics_source(self):
        source = self.optics_source.currentText()
        if source == "Alignment":
            values = {
                "Pixel Size": "SL8686",
                "Sample Rate": "1.6",
                "Incidence": "Normal",
                "Polarization": "S-POL",
                "focus": "0.125 um",
                "lights": ["7.40", "7.40", "2.30"],
            }
        elif source.startswith("Test "):
            test_number = int(source.split()[1])
            values = {
                "Pixel Size": "SL8685" if test_number == 1 else "SL8686",
                "Sample Rate": "3.2(Default)" if test_number == 1 else "1.6",
                "Incidence": "Oblique",
                "Polarization": "P-POL",
                "focus": f"{test_number * 0.050:.3f} um",
                "lights": [f"{8.6 - test_number * 0.2:.2f}", "7.40", "2.30"],
            }
        else:
            values = {
                "Pixel Size": "SL8685",
                "Sample Rate": "3.2(Default)",
                "Incidence": "Oblique",
                "Polarization": "P-POL",
                "focus": "0.001 um",
                "lights": ["9.99", "9.99", "9.99"],
            }
        for name, control in self.optics_controls.items():
            control.setCurrentText(values[name])
        self.optics_focus.setText(values["focus"])
        for row, light in enumerate(values["lights"]):
            self.optics_table.item(row, 3).setText(light)
        self.loaded_optics_source = source
        self.status_label.setText(f"Loaded optics from {source}")

    def _use_for_alignment(self):
        self.use_current_optics_for_alignment = True
        self.status_label.setText("Current inspection optics selected for alignment")

    def keyPressEvent(self, event):  # noqa: N802 - Qt override
        if event.key() == Qt.Key_Left:
            self._show_previous_image()
            event.accept()
            return
        if event.key() == Qt.Key_Right:
            self._show_next_image()
            event.accept()
            return
        super().keyPressEvent(event)

    @staticmethod
    def _field_value(field: QLineEdit) -> float:
        try:
            return float(field.text())
        except ValueError:
            return 0.0


class CycleImageSetupDialog(QDialog):
    def __init__(
        self,
        available_images,
        cycle_images,
        delay_seconds: float,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self.setWindowTitle("Cycle Image Setup")
        self.setFixedSize(780, 620)
        self.available_images = list(available_images)
        self.initial_cycle_images = [image for image in cycle_images if image in self.available_images]
        self.result_cycle_images = list(self.initial_cycle_images)
        self.result_delay_seconds = delay_seconds
        self.play_requested = False
        self._build_ui(delay_seconds)

    def _build_ui(self, delay_seconds: float):
        self.setStyleSheet(
            """
            QDialog {
                background: #ece9d8;
                color: #111111;
                font-family: Arial, Helvetica, sans-serif;
                font-size: 10px;
            }
            QPushButton {
                background: #f1efe3;
                border-top: 1px solid #ffffff;
                border-left: 1px solid #ffffff;
                border-right: 1px solid #77736b;
                border-bottom: 1px solid #77736b;
                min-height: 24px;
                padding: 2px 10px;
            }
            QListWidget, QDoubleSpinBox {
                background: #ffffff;
                border: 1px solid #7f9db9;
            }
            QFrame#mainGroup, QFrame#delayGroup, QFrame#orderGroup {
                border: 1px solid #d8d2bc;
                background: #ece9d8;
            }
            QLabel[groupTitle="true"] {
                color: #0b55d9;
                background: #ece9d8;
                padding: 0 4px;
            }
            """
        )

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 18, 16, 14)
        root.setSpacing(12)

        main_group = QFrame()
        main_group.setObjectName("mainGroup")
        main_layout = QVBoxLayout(main_group)
        main_layout.setContentsMargins(36, 18, 36, 18)
        main_layout.setSpacing(8)
        main_layout.addWidget(QLabel("Add image(s) from Image List to Cycle List to cycle:"))

        columns = QGridLayout()
        columns.setHorizontalSpacing(24)
        columns.addWidget(QLabel("Images List"), 0, 0, alignment=Qt.AlignCenter)
        columns.addWidget(QLabel("Cycle List"), 0, 2, alignment=Qt.AlignCenter)

        self.images_list = QListWidget()
        self.images_list.setFixedSize(220, 315)
        self.cycle_list = QListWidget()
        self.cycle_list.setFixedSize(220, 315)
        self._populate_lists()
        columns.addWidget(self.images_list, 1, 0)

        transfer = QVBoxLayout()
        transfer.addStretch(1)
        add = QPushButton("Add >>")
        remove = QPushButton("<< Remove")
        add.setFixedWidth(95)
        remove.setFixedWidth(95)
        add.clicked.connect(self._add_selected_images)
        remove.clicked.connect(self._remove_selected_images)
        transfer.addWidget(add)
        transfer.addSpacing(14)
        transfer.addWidget(remove)
        transfer.addStretch(2)
        columns.addLayout(transfer, 1, 1)
        columns.addWidget(self.cycle_list, 1, 2)
        columns.addWidget(self._order_panel(), 1, 3)
        main_layout.addLayout(columns)
        root.addWidget(main_group, 1)

        delay_group = QFrame()
        delay_group.setObjectName("delayGroup")
        delay_group.setFixedHeight(78)
        delay_title = QLabel("Cycle Delay Time [sec]")
        delay_title.setProperty("groupTitle", True)
        delay_title.setParent(delay_group)
        delay_title.move(10, -1)
        delay_layout = QHBoxLayout(delay_group)
        delay_layout.setContentsMargins(92, 20, 0, 10)
        self.delay_spin = QDoubleSpinBox()
        self.delay_spin.setDecimals(1)
        self.delay_spin.setRange(0.1, 60.0)
        self.delay_spin.setSingleStep(0.1)
        self.delay_spin.setValue(delay_seconds)
        self.delay_spin.setSuffix(" sec")
        self.delay_spin.setFixedWidth(150)
        delay_layout.addWidget(self.delay_spin)
        delay_layout.addStretch(1)
        root.addWidget(delay_group)

        footer = QHBoxLayout()
        footer.setContentsMargins(34, 0, 330, 0)
        ok = QPushButton("OK")
        play = QPushButton("Play")
        cancel = QPushButton("Cancel")
        ok.setFixedWidth(98)
        play.setFixedWidth(98)
        cancel.setFixedWidth(98)
        ok.clicked.connect(self._accept_without_play)
        play.clicked.connect(self._accept_and_play)
        cancel.clicked.connect(self.reject)
        footer.addWidget(ok)
        footer.addStretch(1)
        footer.addWidget(play)
        footer.addStretch(1)
        footer.addWidget(cancel)
        root.addLayout(footer)

    def _order_panel(self) -> QFrame:
        panel = QFrame()
        panel.setObjectName("orderGroup")
        panel.setFixedSize(78, 176)
        title = QLabel("Set Order")
        title.setProperty("groupTitle", True)
        title.setParent(panel)
        title.move(11, -1)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(22, 20, 22, 10)
        layout.setSpacing(6)
        buttons = [
            ("|^", self._move_selected_to_top),
            ("^", lambda: self._move_selected(-1)),
            ("v", lambda: self._move_selected(1)),
            ("v|", self._move_selected_to_bottom),
        ]
        for text, handler in buttons:
            button = QPushButton(text)
            button.setFixedSize(28, 26)
            button.clicked.connect(handler)
            layout.addWidget(button)
        return panel

    def _populate_lists(self):
        cycle_set = set(self.initial_cycle_images)
        self.images_list.clear()
        self.cycle_list.clear()
        self.images_list.addItems([image for image in self.available_images if image not in cycle_set])
        self.cycle_list.addItems(self.initial_cycle_images)
        if self.images_list.count():
            self.images_list.setCurrentRow(0)
        if self.cycle_list.count():
            self.cycle_list.setCurrentRow(0)

    def _add_selected_images(self):
        for item in self.images_list.selectedItems():
            row = self.images_list.row(item)
            taken = self.images_list.takeItem(row)
            self.cycle_list.addItem(taken.text())
        if self.cycle_list.count():
            self.cycle_list.setCurrentRow(self.cycle_list.count() - 1)

    def _remove_selected_images(self):
        for item in self.cycle_list.selectedItems():
            row = self.cycle_list.row(item)
            taken = self.cycle_list.takeItem(row)
            self.images_list.addItem(taken.text())
        if self.images_list.count():
            self.images_list.setCurrentRow(self.images_list.count() - 1)

    def _move_selected(self, delta: int):
        row = self.cycle_list.currentRow()
        target = row + delta
        if row < 0 or target < 0 or target >= self.cycle_list.count():
            return
        item = self.cycle_list.takeItem(row)
        self.cycle_list.insertItem(target, item)
        self.cycle_list.setCurrentRow(target)

    def _move_selected_to_top(self):
        row = self.cycle_list.currentRow()
        if row <= 0:
            return
        item = self.cycle_list.takeItem(row)
        self.cycle_list.insertItem(0, item)
        self.cycle_list.setCurrentRow(0)

    def _move_selected_to_bottom(self):
        row = self.cycle_list.currentRow()
        last = self.cycle_list.count() - 1
        if row < 0 or row >= last:
            return
        item = self.cycle_list.takeItem(row)
        self.cycle_list.addItem(item)
        self.cycle_list.setCurrentRow(last)

    def _accept_without_play(self):
        self.play_requested = False
        self._capture_results()
        self.accept()

    def _accept_and_play(self):
        self.play_requested = True
        self._capture_results()
        self.accept()

    def _capture_results(self):
        self.result_cycle_images = [self.cycle_list.item(index).text() for index in range(self.cycle_list.count())]
        self.result_delay_seconds = self.delay_spin.value()


class AdvancedOpticsDialog(QDialog):
    def __init__(self, parent: Optional[QWidget] = None, state: Optional[dict] = None):
        super().__init__(parent)
        self.initial_state = deepcopy(state or {})
        self.profiles = deepcopy(self.initial_state.get("profiles", {}))
        self.applied_settings = deepcopy(self.initial_state.get("current", {}))
        self.result_settings = None
        self.setWindowTitle("Advanced Inspection Optics Settings")
        self.setFixedSize(610, 500)
        self._build_ui()
        if self.applied_settings:
            self._apply_snapshot(self.applied_settings)

    def _build_ui(self):
        self.setStyleSheet(
            """
            QDialog {
                background: #cfcac1;
                color: #111111;
                font-family: Arial, Helvetica, sans-serif;
                font-size: 10px;
            }
            QPushButton {
                background: #e7e4da;
                border-top: 1px solid #ffffff;
                border-left: 1px solid #ffffff;
                border-right: 1px solid #77736b;
                border-bottom: 1px solid #77736b;
                min-height: 24px;
                padding: 1px 12px;
            }
            QComboBox, QLineEdit, QDoubleSpinBox {
                background: #ffffff;
                border: 1px solid #77736b;
                min-height: 21px;
            }
            QTableWidget {
                background: #f5f5f2;
                border: 1px solid #77736b;
                gridline-color: #9c988f;
            }
            QFrame#namedSettings {
                border: 1px solid #8f8b82;
                background: #cfcac1;
            }
            QLabel#groupTitle {
                background: #cfcac1;
                padding: 0 4px;
            }
            """
        )

        root = QVBoxLayout(self)
        root.setContentsMargins(22, 18, 22, 14)
        root.setSpacing(10)

        root.addLayout(self._settings_form())
        root.addWidget(self._channel_table())
        root.addStretch(1)
        root.addWidget(self._named_settings_panel())
        root.addLayout(self._footer())

    def _settings_form(self) -> QGridLayout:
        form = QGridLayout()
        form.setHorizontalSpacing(8)
        form.setVerticalSpacing(8)
        form.setColumnMinimumWidth(0, 155)
        form.setColumnMinimumWidth(1, 28)

        rows = [
            ("Pixel Size:", "magnifier", self._combo(["SL8685", "SL8686", "SL8687"], 132)),
            ("Sample Rate:", "rate", self._combo(["3.2(Default)", "1.6", "6.4"], 132)),
            ("Beam Incidence:", "beam", self._combo(["Oblique", "Normal"], 132)),
            ("Polarization:", "polar", self._combo(["P-POL", "S-POL"], 132)),
        ]
        self.pixel_size = rows[0][2]
        self.sample_rate = rows[1][2]
        self.beam_incidence = rows[2][2]
        self.polarization = rows[3][2]
        for row, (label, icon, control) in enumerate(rows):
            form.addWidget(QLabel(label), row, 0, alignment=Qt.AlignRight | Qt.AlignVCenter)
            form.addWidget(OpticsIcon(icon), row, 1, alignment=Qt.AlignCenter)
            form.addWidget(control, row, 2)

        form.addWidget(QLabel("Focus Offset:"), 4, 0, alignment=Qt.AlignRight | Qt.AlignVCenter)
        form.addWidget(OpticsIcon("focus"), 4, 1, alignment=Qt.AlignCenter)
        self.focus_offset = QDoubleSpinBox()
        self.focus_offset.setDecimals(3)
        self.focus_offset.setRange(-50.0, 50.0)
        self.focus_offset.setSingleStep(0.001)
        self.focus_offset.setValue(0.001)
        self.focus_offset.setSuffix(" um")
        self.focus_offset.setFixedWidth(82)
        form.addWidget(self.focus_offset, 4, 2)
        form.setColumnStretch(3, 1)
        return form

    def _channel_table(self) -> QTableWidget:
        self.channel_table = QTableWidget(3, 7)
        self.channel_table.setHorizontalHeaderLabels(
            ["Channel", "Enable", "Polarization", "Light Level", "IRIS", "Imaging Mode", "Use Fourier Filter"]
        )
        self.channel_table.verticalHeader().setVisible(False)
        self.channel_table.setFixedHeight(110)
        rows = [
            ["1 (Left)", "", "S-POL", "9.99", "OPEN", "DoubleDarkField", ""],
            ["2 (Right)", "", "S-POL", "9.99", "OPEN", "DoubleDarkField", ""],
            ["3 (Center)", "", "S-POL", "9.99", "OPEN", "DarkField", ""],
        ]
        for row, values in enumerate(rows):
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                if column in [1, 6]:
                    item.setText("")
                    item.setCheckState(Qt.Checked)
                self.channel_table.setItem(row, column, item)
        self.channel_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.channel_table.horizontalHeader().setSectionResizeMode(5, QHeaderView.Stretch)
        self.channel_table.horizontalHeader().setSectionResizeMode(6, QHeaderView.ResizeToContents)
        return self.channel_table

    def _named_settings_panel(self) -> QWidget:
        wrapper = QWidget()
        layout = QVBoxLayout(wrapper)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        title = QLabel("Inspection Optics Named Settings")
        title.setObjectName("groupTitle")
        title.setFixedWidth(170)
        title.move(10, 0)

        panel = QFrame()
        panel.setObjectName("namedSettings")
        panel_layout = QHBoxLayout(panel)
        panel_layout.setContentsMargins(16, 18, 16, 12)
        panel_layout.setSpacing(18)
        self.named_settings = QComboBox()
        self.named_settings.setEditable(True)
        self.named_settings.addItems(["", "Current Machine", "Alignment Default"])
        for name in sorted(self.profiles):
            if self.named_settings.findText(name) < 0:
                self.named_settings.addItem(name)
        self.named_settings.lineEdit().setMaxLength(21)
        self.named_settings.setFixedWidth(150)
        panel_layout.addWidget(self.named_settings)
        more = QPushButton("...")
        more.setFixedWidth(26)
        more.setToolTip("Browse Review Optics named settings")
        more.clicked.connect(self.named_settings.showPopup)
        panel_layout.addWidget(more)
        panel_layout.addStretch(1)
        load = QPushButton("Load")
        save = QPushButton("Save")
        delete = QPushButton("Delete")
        load.clicked.connect(self._load_named_setting)
        save.clicked.connect(self._save_named_setting)
        delete.clicked.connect(self._delete_named_setting)
        for button in [load, save, delete]:
            button.setFixedWidth(70)
            panel_layout.addWidget(button)
        layout.addWidget(panel)
        title.setParent(panel)
        title.move(10, -1)
        return wrapper

    def _footer(self) -> QHBoxLayout:
        footer = QHBoxLayout()
        footer.addStretch(1)
        apply_button = QPushButton("Apply")
        apply_button.setFixedWidth(80)
        apply_button.clicked.connect(self._apply)
        footer.addWidget(apply_button)
        footer.addSpacing(18)
        ok = QPushButton("OK")
        ok.setFixedWidth(80)
        ok.clicked.connect(self._accept)
        footer.addWidget(ok)
        footer.addSpacing(28)
        cancel = QPushButton("Cancel")
        cancel.setFixedWidth(80)
        cancel.clicked.connect(self.reject)
        footer.addWidget(cancel)
        footer.addStretch(1)
        return footer

    @staticmethod
    def _combo(values, width: int) -> QComboBox:
        combo = QComboBox()
        combo.addItems(values)
        combo.setFixedWidth(width)
        return combo

    def _set_named_setting(self, value: str):
        index = self.named_settings.findText(value)
        if index < 0:
            self.named_settings.addItem(value)
            index = self.named_settings.findText(value)
        self.named_settings.setCurrentIndex(index)

    def _save_named_setting(self):
        value = self.named_settings.currentText().strip()
        if not value:
            QMessageBox.warning(self, "Review Optics Named Settings", "Enter a name before saving.")
            return
        if len(value) > 21:
            QMessageBox.warning(self, "Review Optics Named Settings", "The name is limited to 21 characters.")
            return
        self.profiles[value] = self._snapshot()
        self._set_named_setting(value)

    def _delete_named_setting(self):
        index = self.named_settings.currentIndex()
        name = self.named_settings.currentText().strip()
        if index <= 0 or not name:
            return
        answer = QMessageBox.question(
            self,
            "Delete Review Optics",
            f"Delete the Review Optics setting '{name}'?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if answer == QMessageBox.Yes:
            self.profiles.pop(name, None)
            self.named_settings.removeItem(index)

    def _load_named_setting(self):
        name = self.named_settings.currentText().strip()
        settings = self.profiles.get(name)
        if settings:
            self._apply_snapshot(settings)
        elif name == "Alignment Default":
            self._apply_snapshot({
                "pixel_size": "SL8685",
                "sample_rate": "3.2(Default)",
                "beam_incidence": "Oblique",
                "polarization": "P-POL",
                "focus_offset": 0.0,
            })
        elif name == "Current Machine" and self.applied_settings:
            self._apply_snapshot(self.applied_settings)

    def _snapshot(self) -> dict:
        channels = []
        for row in range(self.channel_table.rowCount()):
            values = []
            for column in range(self.channel_table.columnCount()):
                item = self.channel_table.item(row, column)
                values.append({
                    "text": item.text(),
                    "checked": item.checkState() == Qt.Checked if column in (1, 6) else None,
                })
            channels.append(values)
        return {
            "pixel_size": self.pixel_size.currentText(),
            "sample_rate": self.sample_rate.currentText(),
            "beam_incidence": self.beam_incidence.currentText(),
            "polarization": self.polarization.currentText(),
            "focus_offset": self.focus_offset.value(),
            "channels": channels,
        }

    def _apply_snapshot(self, settings: dict):
        controls = {
            "pixel_size": self.pixel_size,
            "sample_rate": self.sample_rate,
            "beam_incidence": self.beam_incidence,
            "polarization": self.polarization,
        }
        for key, control in controls.items():
            value = settings.get(key)
            if value and control.findText(str(value)) >= 0:
                control.setCurrentText(str(value))
        if "focus_offset" in settings:
            self.focus_offset.setValue(float(settings["focus_offset"]))
        channels = settings.get("channels") or []
        for row, values in enumerate(channels[: self.channel_table.rowCount()]):
            for column, value in enumerate(values[: self.channel_table.columnCount()]):
                item = self.channel_table.item(row, column)
                if not item or not isinstance(value, dict):
                    continue
                item.setText(str(value.get("text", item.text())))
                if column in (1, 6) and value.get("checked") is not None:
                    item.setCheckState(Qt.Checked if value["checked"] else Qt.Unchecked)

    def _apply(self):
        self.applied_settings = self._snapshot()
        self.setWindowTitle("Advanced Review Optics Settings - Applied")

    def _accept(self):
        self._apply()
        self.result_settings = {
            "named_setting": self.named_settings.currentText().strip() or "Current Machine",
            "current": deepcopy(self.applied_settings),
            "profiles": deepcopy(self.profiles),
            "configured": True,
        }
        self.accept()


class OpticsIcon(QWidget):
    def __init__(self, kind: str, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.kind = kind
        self.setFixedSize(24, 22)

    def paintEvent(self, event):  # noqa: N802 - Qt override
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        if self.kind == "magnifier":
            painter.setBrush(QColor("#4859dc"))
            painter.setPen(QPen(QColor("#111111"), 1))
            painter.drawEllipse(4, 3, 11, 11)
            painter.drawLine(13, 13, 20, 20)
            painter.setPen(QPen(QColor("#ffffff"), 1))
            painter.drawEllipse(6, 5, 6, 6)
        elif self.kind == "rate":
            painter.setPen(QPen(QColor("#111111"), 1))
            for x in [5, 10, 15, 20]:
                painter.drawLine(x, 5, x, 17)
            painter.drawLine(3, 11, 22, 11)
        elif self.kind == "beam":
            painter.setPen(QPen(QColor("#1d42d2"), 2))
            painter.drawLine(4, 7, 13, 16)
            painter.setPen(QPen(QColor("#d4bd00"), 3))
            painter.drawLine(12, 15, 20, 15)
        elif self.kind == "polar":
            painter.setPen(QPen(QColor("#111111"), 1))
            for x in [5, 9, 13, 17, 21]:
                painter.drawArc(x - 2, 6, 4, 10, 90 * 16, 180 * 16)
        elif self.kind == "focus":
            painter.setPen(QPen(QColor("#111111"), 1))
            painter.drawLine(12, 2, 12, 20)
            painter.drawLine(4, 11, 20, 11)
            painter.setBrush(QColor("#0b8f24"))
            painter.drawEllipse(9, 8, 6, 6)


class StagePositionWidget(QWidget):
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setFixedSize(88, 30)

    def paintEvent(self, event):  # noqa: N802 - Qt override
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setBrush(QColor("#c224ca"))
        painter.setPen(QPen(QColor("#c224ca"), 1))
        painter.drawEllipse(5, 6, 23, 23)
        painter.setPen(QPen(QColor("#0000cc"), 4))
        painter.drawLine(31, 18, 74, 18)
        painter.drawLine(74, 11, 84, 18)
        painter.drawLine(84, 18, 74, 25)


class ImageViewport(QWidget):
    def __init__(self, parent: Optional[QWidget] = None, *, compact: bool = False):
        super().__init__(parent)
        if compact:
            self.setMinimumSize(320, 420)
        else:
            self.setMinimumSize(520, 560)
        self.highlight = False
        self.current_image_name = ""
        self.zoom_percent = 100
        self.alignment_mode = "DF"
        self.bf_magnification = "Low Mag"

    def set_image(self, image_name: str):
        self.current_image_name = image_name
        self.highlight = image_name.endswith("(Center)") or self._is_simulated_alignment_image()
        self.update()

    def set_alignment_view(self, mode: str, magnification: str = "Low Mag"):
        self.alignment_mode = "BF" if str(mode).upper() == "BF" else "DF"
        self.bf_magnification = "High Mag" if magnification == "High Mag" else "Low Mag"
        self.update()

    def paintEvent(self, event):  # noqa: N802 - Qt override
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.fillRect(self.rect(), QColor("#c9c5bb"))

        base_rect = self.rect().adjusted(34, 30, -24, -26)
        scale = self.zoom_percent / 100.0
        extra_x = int(base_rect.width() * (scale - 1.0) / 2)
        extra_y = int(base_rect.height() * (scale - 1.0) / 2)
        rect = base_rect.adjusted(-extra_x, -extra_y, extra_x, extra_y)
        painter.fillRect(rect, self._background_for_image())
        if self._is_simulated_alignment_image():
            self._paint_simulated_alignment_image(painter, rect)
        painter.setPen(QPen(QColor("#1e28b8"), 1))
        painter.drawRect(rect)

        for index in range(0, 11):
            value = index * 50
            x = rect.left() + int(rect.width() * index / 10)
            y = rect.top() + int(rect.height() * index / 10)
            painter.drawLine(x, rect.top() - 5, x, rect.top())
            painter.drawLine(x, rect.bottom(), x, rect.bottom() + 5)
            painter.drawText(x - 8, rect.top() - 10, str(value))
            painter.drawLine(rect.left() - 5, y, rect.left(), y)
            painter.drawLine(rect.right(), y, rect.right() + 5, y)
            painter.drawText(rect.left() - 28, y + 4, str(value))
            painter.drawText(rect.right() + 8, y + 4, str(value))

        center_x = rect.left() + int(rect.width() * 0.53)
        center_y = rect.top() + int(rect.height() * 0.52)
        painter.setPen(QPen(QColor("#2530d4"), 1))
        painter.drawLine(center_x - 42, center_y, center_x + 42, center_y)
        painter.drawLine(center_x, center_y - 42, center_x, center_y + 42)
        if self.highlight:
            painter.setPen(QPen(QColor("#8a8a8a"), 1))
            painter.drawEllipse(center_x - 5, center_y - 5, 10, 10)
        if self.current_image_name:
            painter.setPen(QPen(QColor("#333333"), 1))
            painter.drawText(rect.left() + 12, rect.top() + 20, self.current_image_name)

    def _is_simulated_alignment_image(self) -> bool:
        return self.current_image_name.startswith("Sim Cross Mark")

    def _paint_simulated_alignment_image(self, painter: QPainter, rect):
        seed = sum(ord(character) for character in self.current_image_name)
        dark_field = self.alignment_mode != "BF" and (
            "(DF)" in self.current_image_name or "Capture" in self.current_image_name
        )
        base = QColor("#242424") if dark_field else QColor("#e7e7e2")
        street = QColor("#080808") if not dark_field else QColor("#5a5a5a")
        die_fill = QColor("#b9bab5") if not dark_field else QColor("#333333")
        mark_color = QColor("#f1f1eb") if dark_field else QColor("#1c1c1c")
        glow_color = QColor("#6bd66d") if dark_field else QColor("#4b7fff")

        painter.fillRect(rect, base)
        magnification_factor = 1.0
        if self.alignment_mode == "BF":
            magnification_factor = 2.25 if self.bf_magnification == "High Mag" else 0.85
        die_w = max(32, int((rect.width() // 8) * magnification_factor))
        die_h = max(28, int((rect.height() // 9) * magnification_factor))
        offset_x = seed % die_w
        offset_y = (seed // 3) % die_h

        for x in range(rect.left() - offset_x, rect.right(), die_w):
            painter.fillRect(x, rect.top(), 4, rect.height(), street)
        for y in range(rect.top() - offset_y, rect.bottom(), die_h):
            painter.fillRect(rect.left(), y, rect.width(), 4, street)

        painter.setPen(QPen(QColor("#6f6f6a") if not dark_field else QColor("#424242"), 1, Qt.DotLine))
        for x in range(rect.left() + die_w // 2 - offset_x, rect.right(), die_w):
            painter.drawLine(x, rect.top(), x, rect.bottom())
        for y in range(rect.top() + die_h // 2 - offset_y, rect.bottom(), die_h):
            painter.drawLine(rect.left(), y, rect.right(), y)

        for index in range(120):
            x = rect.left() + ((seed * 17 + index * 37) % max(1, rect.width()))
            y = rect.top() + ((seed * 29 + index * 19) % max(1, rect.height()))
            noise_value = 85 + ((seed + index * 23) % 90)
            painter.setPen(QPen(QColor(noise_value, noise_value, noise_value), 1))
            painter.drawPoint(x, y)

        mark_x = rect.left() + int(rect.width() * (0.48 + ((seed % 9) - 4) * 0.006))
        mark_y = rect.top() + int(rect.height() * (0.50 + (((seed // 7) % 9) - 4) * 0.006))
        mark_extent = 72 if self.alignment_mode == "BF" and self.bf_magnification == "High Mag" else 46
        painter.setPen(QPen(mark_color, 9))
        painter.drawLine(mark_x - mark_extent, mark_y, mark_x + mark_extent, mark_y)
        painter.drawLine(mark_x, mark_y - mark_extent, mark_x, mark_y + mark_extent)
        painter.setPen(QPen(base, 3))
        painter.drawLine(mark_x - 20, mark_y, mark_x + 20, mark_y)
        painter.drawLine(mark_x, mark_y - 20, mark_x, mark_y + 20)

        painter.setPen(QPen(glow_color, 1))
        painter.drawRect(mark_x - 64, mark_y - 64, 128, 128)
        painter.setPen(QPen(QColor("#2530d4"), 1))
        painter.drawLine(mark_x - 22, mark_y, mark_x + 22, mark_y)
        painter.drawLine(mark_x, mark_y - 22, mark_x, mark_y + 22)

        painter.setPen(QPen(die_fill, 1))
        painter.drawText(rect.left() + 12, rect.bottom() - 34, "Synthetic wafer image data")
        view_name = (
            f"BF {self.bf_magnification}"
            if self.alignment_mode == "BF"
            else "DF Single Mag"
        )
        painter.drawText(
            rect.left() + 12,
            rect.bottom() - 18,
            f"{view_name} | Cross mark X {mark_x - rect.center().x()} px, Y {mark_y - rect.center().y()} px",
        )

    def _background_for_image(self) -> QColor:
        if self.alignment_mode == "BF":
            return QColor("#dbe5e8" if self.bf_magnification == "Low Mag" else "#c8d9de")
        if self.current_image_name.endswith("(Left)"):
            return QColor("#fffdf7")
        if self.current_image_name.endswith("(Right)"):
            return QColor("#f7fbff")
        if self.current_image_name.endswith("(Center)"):
            return QColor("#ffffff")
        return QColor("#fbfbfb")


class IntensityScale(QWidget):
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setFixedSize(48, 560)

    def paintEvent(self, event):  # noqa: N802 - Qt override
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor("#c9c5bb"))
        painter.setPen(QPen(QColor("#111111"), 1))
        painter.drawText(7, 18, "4095")
        top = 36
        left = 14
        height = self.height() - 110
        width = 18
        for offset in range(height):
            ratio = offset / max(1, height - 1)
            color = self._color_at(ratio)
            painter.fillRect(left, top + offset, width, 1, color)
        painter.setPen(QPen(QColor("#77736b"), 1))
        painter.drawRect(left, top, width, height)
        painter.fillRect(left, top + height + 10, width + 15, 20, QColor("#ffffff"))
        painter.drawRect(left, top + height + 10, width + 15, 20)
        painter.drawText(left + 3, top + height + 25, "0")

    @staticmethod
    def _color_at(ratio: float) -> QColor:
        if ratio < 0.2:
            return QColor(255, int(255 * ratio / 0.2), 255)
        if ratio < 0.4:
            return QColor(255, int(255 - 255 * (ratio - 0.2) / 0.2), 0)
        if ratio < 0.65:
            return QColor(0, int(200 - 120 * (ratio - 0.4) / 0.25), 220)
        return QColor(0, int(90 - 90 * (ratio - 0.65) / 0.35), int(220 - 160 * (ratio - 0.65) / 0.35))
