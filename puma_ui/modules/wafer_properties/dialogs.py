from __future__ import annotations

from typing import Optional

from ...qt_compat import (
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSlider,
    QTableWidget,
    QTableWidgetItem,
    Qt,
    QVBoxLayout,
    QWidget,
)
from ...widgets import ClassicButton


DEFAULT_WAFER_PROPERTIES = {
    "orientation": "Down (180 deg.)",
    "type": "Patterned",
    "laser_power_sensitive": True,
    "laser_power_factor": "0.03500",
    "layer": "_KT_Low_Power [ 0.03500 ]",
    "dark_wafer_auto_focus": True,
    "wafer_darkness_level": "Dark",
}


class WaferMenuDialog(QDialog):
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setWindowTitle("Wafer")
        self.setFixedSize(190, 250)
        self.open_wafer_properties = False
        self.open_alignment = False
        self.open_wafer_map = False
        self.setStyleSheet(
            """
            QDialog {
                background: #d7d4c9;
                font-family: Arial, Helvetica, sans-serif;
                font-size: 10px;
            }
            """
        )
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(10)

        properties = ClassicButton("Wafer\nProperties")
        properties.clicked.connect(self._accept_properties)
        layout.addWidget(properties)
        alignment = ClassicButton("Alignment", arrow=True)
        alignment.clicked.connect(self._accept_alignment)
        layout.addWidget(alignment)
        wafer_map = ClassicButton("Wafer Map", arrow=True)
        wafer_map.clicked.connect(self._accept_wafer_map)
        layout.addWidget(wafer_map)
        layout.addWidget(ClassicButton("Select Defect\nData", arrow=True))
        layout.addStretch(1)

    def _accept_properties(self):
        self.open_wafer_properties = True
        self.accept()

    def _accept_alignment(self):
        self.open_alignment = True
        self.accept()

    def _accept_wafer_map(self):
        self.open_wafer_map = True
        self.accept()


class WaferPropertiesDialog(QDialog):
    def __init__(self, properties=None, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setWindowTitle("Wafer Properties")
        self.properties = dict(DEFAULT_WAFER_PROPERTIES)
        if properties:
            self.properties.update(properties)
        self.result_properties = None
        self._original_orientation = self.properties["orientation"]
        self._original_type = self.properties["type"]
        self._laser_scale = 100000
        self._laser_min = 0.0023455
        self._laser_max = 3.8278574
        self.setFixedSize(560, 640)
        self._build_ui()
        self._load_properties()
        self._update_enabled_state()

    def _build_ui(self):
        self.setStyleSheet(
            """
            QDialog {
                background: #d0ccc2;
                color: #111111;
                font-family: Arial, Helvetica, sans-serif;
                font-size: 10px;
            }
            QComboBox, QLineEdit {
                background: #ffffff;
                border: 1px solid #77736b;
                min-height: 24px;
            }
            QSlider#laserPowerSlider::groove:horizontal {
                height: 16px;
                background: #ed1c24;
                border: 1px solid #7b7b7b;
            }
            QSlider#laserPowerSlider::handle:horizontal {
                width: 12px;
                margin: -4px 0;
                background: #f1f1f1;
                border: 1px solid #777777;
            }
            QSlider#laserPowerSlider::sub-page:horizontal {
                background: #ed1c24;
            }
            QSlider#laserPowerSlider::add-page:horizontal {
                background: #ed1c24;
            }
            QSlider#darkLevelSlider::groove:horizontal {
                height: 4px;
                background: #777777;
                border: 1px solid #b8b8b8;
            }
            QSlider#darkLevelSlider::handle:horizontal {
                width: 12px;
                height: 18px;
                margin: -8px 0;
                background: #e8e8e8;
                border: 1px solid #777777;
            }
            QPushButton {
                background: #e7e5dc;
                border-top: 1px solid #ffffff;
                border-left: 1px solid #ffffff;
                border-right: 1px solid #77736b;
                border-bottom: 1px solid #77736b;
                min-height: 24px;
                padding: 2px 10px;
            }
            QFrame#groupBox {
                border: 1px solid #8f8b82;
                background: #d0ccc2;
            }
            QLabel#groupTitle {
                background: #d0ccc2;
                padding: 0 4px;
            }
            """
        )

        main = QVBoxLayout(self)
        main.setContentsMargins(22, 24, 22, 18)
        main.setSpacing(16)

        form = QGridLayout()
        form.setHorizontalSpacing(12)
        form.setVerticalSpacing(10)
        form.setColumnStretch(0, 1)
        form.setColumnStretch(1, 1)

        form.addWidget(QLabel("Orientation:"), 0, 0, alignment=Qt.AlignRight)
        self.orientation_combo = QComboBox()
        self.orientation_combo.addItems(["Up (0 deg.)", "Right (90 deg.)", "Down (180 deg.)", "Left (270 deg.)"])
        form.addWidget(self.orientation_combo, 0, 1)

        form.addWidget(QLabel("Type:"), 1, 0, alignment=Qt.AlignRight)
        self.type_combo = QComboBox()
        self.type_combo.addItems(["Patterned", "Blank"])
        form.addWidget(self.type_combo, 1, 1)
        main.addLayout(form)
        main.addSpacing(28)

        main.addWidget(self._laser_power_group())
        main.addWidget(self._dark_wafer_group())
        main.addStretch(1)

        buttons = QHBoxLayout()
        buttons.addStretch(1)
        ok = QPushButton("OK")
        ok.setFixedSize(94, 30)
        ok.clicked.connect(self._accept)
        cancel = QPushButton("Cancel")
        cancel.setFixedSize(94, 30)
        cancel.clicked.connect(self.reject)
        buttons.addWidget(ok)
        buttons.addSpacing(42)
        buttons.addWidget(cancel)
        buttons.addStretch(1)
        main.addLayout(buttons)

    def _laser_power_group(self) -> QWidget:
        group = QFrame()
        group.setObjectName("groupBox")
        layout = QVBoxLayout(group)
        layout.setContentsMargins(14, 4, 14, 12)
        layout.setSpacing(8)

        header = QHBoxLayout()
        self.laser_power_sensitive = QCheckBox("Laser Power Sensitive")
        self.laser_power_sensitive.toggled.connect(self._update_enabled_state)
        header.addWidget(self.laser_power_sensitive)
        header.addStretch(1)
        layout.addLayout(header)

        row = QGridLayout()
        row.setHorizontalSpacing(10)
        row.setVerticalSpacing(4)
        row.addWidget(QLabel("Laser Power Factor:"), 0, 0)
        self.laser_power_slider = QSlider(Qt.Horizontal)
        self.laser_power_slider.setObjectName("laserPowerSlider")
        self.laser_power_slider.setFixedSize(190, 22)
        self.laser_power_slider.setRange(
            int(self._laser_min * self._laser_scale),
            int(self._laser_max * self._laser_scale),
        )
        self.laser_power_slider.valueChanged.connect(self._laser_slider_changed)
        row.addWidget(self.laser_power_slider, 1, 0)
        row.addWidget(QLabel("Current Setting:"), 0, 1)
        self.laser_power_factor = QLineEdit()
        self.laser_power_factor.setFixedWidth(120)
        self.laser_power_factor.editingFinished.connect(self._laser_text_changed)
        row.addWidget(self.laser_power_factor, 1, 1)
        row.addWidget(QLabel("J/cm^2"), 1, 2)
        layout.addLayout(row)

        layout.addWidget(QLabel("Selecting new Layer:"))
        layer_row = QGridLayout()
        layer_row.setHorizontalSpacing(6)
        layer_row.addWidget(QLabel("Layer [ Laser Power Limit, J/cm^2 ]:"), 0, 0, 1, 2)
        self.layer_combo = QComboBox()
        self.layer_combo.addItems([
            "_KT_Low_Power [ 0.03500 ]",
            "9000 Power Limit [ 0.12100 ]",
            "9000 Dose Limit [ 0.24200 ]",
        ])
        layer_row.addWidget(self.layer_combo, 1, 0, 1, 2)
        layout.addLayout(layer_row)

        note = QLabel("* Layer does not exist in the template list")
        layout.addWidget(note)

        edit = QPushButton("Edit Settings...")
        edit.setFixedWidth(220)
        edit.clicked.connect(self._open_layer_database)
        layout.addWidget(edit, alignment=Qt.AlignHCenter)

        self.laser_widgets = [self.laser_power_slider, self.laser_power_factor, self.layer_combo, edit]
        return group

    def _dark_wafer_group(self) -> QWidget:
        group = QFrame()
        group.setObjectName("groupBox")
        layout = QGridLayout(group)
        layout.setContentsMargins(14, 4, 14, 12)
        layout.setHorizontalSpacing(12)
        layout.setVerticalSpacing(8)

        self.dark_wafer_auto_focus = QCheckBox("Dark Wafer Auto Focus Setting")
        self.dark_wafer_auto_focus.toggled.connect(self._update_enabled_state)
        layout.addWidget(self.dark_wafer_auto_focus, 0, 0, 1, 3)

        layout.addWidget(QLabel("Wafer Darkness Level:"), 1, 0, alignment=Qt.AlignRight)
        dark_slider_area = QVBoxLayout()
        self.dark_level_slider = QSlider(Qt.Horizontal)
        self.dark_level_slider.setObjectName("darkLevelSlider")
        self.dark_level_slider.setRange(0, 100)
        self.dark_level_slider.setSingleStep(1)
        self.dark_level_slider.setPageStep(10)
        self.dark_level_slider.setFixedWidth(160)
        self.dark_level_slider.valueChanged.connect(self._dark_slider_changed)
        dark_slider_area.addWidget(self.dark_level_slider)
        dark_labels = QHBoxLayout()
        dark_labels.addWidget(QLabel("Dark"))
        dark_labels.addStretch(1)
        dark_labels.addWidget(QLabel("Darkest"))
        dark_slider_area.addLayout(dark_labels)
        layout.addLayout(dark_slider_area, 1, 1)
        self.dark_level_value = QLabel("Dark")
        self.dark_level_value.setFixedWidth(56)
        layout.addWidget(self.dark_level_value, 1, 2)
        self.dark_widgets = [self.dark_level_slider, self.dark_level_value]
        return group

    def _load_properties(self):
        self.orientation_combo.setCurrentText(self.properties["orientation"])
        self.type_combo.setCurrentText(self.properties["type"])
        self.laser_power_sensitive.setChecked(bool(self.properties["laser_power_sensitive"]))
        self._set_laser_factor(float(self.properties["laser_power_factor"]))
        self.layer_combo.setCurrentText(self.properties["layer"])
        self.dark_wafer_auto_focus.setChecked(bool(self.properties["dark_wafer_auto_focus"]))
        self.dark_level_slider.setValue(100 if self.properties["wafer_darkness_level"] == "Darkest" else 0)
        self._dark_slider_changed(self.dark_level_slider.value())

    def _update_enabled_state(self):
        laser_enabled = self.laser_power_sensitive.isChecked()
        for widget in self.laser_widgets:
            widget.setEnabled(laser_enabled)
        dark_enabled = self.dark_wafer_auto_focus.isChecked()
        for widget in self.dark_widgets:
            widget.setEnabled(dark_enabled)

    def _open_layer_database(self):
        dialog = EditLayerDatabaseDialog(self)
        dialog.exec() if hasattr(dialog, "exec") else dialog.exec_()

    def _set_laser_factor(self, factor: float):
        bounded = min(max(factor, self._laser_min), self._laser_max)
        self.laser_power_slider.blockSignals(True)
        self.laser_power_slider.setValue(int(bounded * self._laser_scale))
        self.laser_power_slider.blockSignals(False)
        self.laser_power_factor.setText(f"{bounded:.5f}")

    def _laser_slider_changed(self, value: int):
        factor = value / self._laser_scale
        self.laser_power_factor.setText(f"{factor:.5f}")

    def _laser_text_changed(self):
        try:
            factor = float(self.laser_power_factor.text().strip())
        except ValueError:
            return
        self._set_laser_factor(factor)

    def _dark_slider_changed(self, value: int):
        self.dark_level_value.setText("Darkest" if value >= 50 else "Dark")

    def _accept(self):
        factor_text = self.laser_power_factor.text().strip()
        try:
            factor = float(factor_text)
        except ValueError:
            QMessageBox.warning(self, "Laser Power Factor", "Laser Power Factor must be a number.")
            return
        if factor < 0.0023455 or factor > 3.8278574:
            QMessageBox.warning(
                self,
                "Laser Power Factor",
                "Laser Power Factor must be between 0.0023455 and 3.8278574.",
            )
            return

        if self.orientation_combo.currentText() != self._original_orientation:
            QMessageBox.warning(
                self,
                "Wafer Orientation",
                "Changing wafer orientation will invalidate alignment data and modify recipe data.",
            )
        if self.type_combo.currentText() != self._original_type:
            QMessageBox.warning(
                self,
                "Wafer Type",
                "Changing wafer type will invalidate all tests for this recipe.",
            )

        self.result_properties = {
            "orientation": self.orientation_combo.currentText(),
            "type": self.type_combo.currentText(),
            "laser_power_sensitive": self.laser_power_sensitive.isChecked(),
            "laser_power_factor": factor_text,
            "layer": self.layer_combo.currentText(),
            "dark_wafer_auto_focus": self.dark_wafer_auto_focus.isChecked(),
            "wafer_darkness_level": self.dark_level_value.text(),
        }
        self.accept()


class EditLayerDatabaseDialog(QDialog):
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setWindowTitle("Edit Layer Database")
        self.setFixedSize(520, 620)
        self._build_ui()

    def _build_ui(self):
        self.setStyleSheet(
            """
            QDialog {
                background: #eeeadd;
                font-family: Arial, Helvetica, sans-serif;
                font-size: 10px;
            }
            QPushButton {
                background: #e7e5dc;
                border: 1px solid #77736b;
                min-height: 24px;
                padding: 2px 10px;
            }
            QTableWidget {
                background: white;
                border: 1px solid #8f8b82;
            }
            """
        )
        layout = QVBoxLayout(self)
        layout.setContentsMargins(34, 36, 34, 24)
        layout.setSpacing(14)

        table = QTableWidget(0, 2)
        table.setHorizontalHeaderLabels(["Layer", "Laser Power Limit"])
        table.verticalHeader().setVisible(False)
        table.setSelectionBehavior(QAbstractItemView.SelectRows)
        table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        for layer, limit in [("9000 Dose Limit", "0.24200"), ("9000 Power Limit", "0.12100")]:
            row = table.rowCount()
            table.insertRow(row)
            table.setItem(row, 0, QTableWidgetItem(layer))
            table.setItem(row, 1, QTableWidgetItem(limit))
        layout.addWidget(table, 1)

        actions = QHBoxLayout()
        actions.addStretch(1)
        actions.addWidget(QPushButton("Add..."))
        modify = QPushButton("Modify...")
        modify.setEnabled(False)
        delete = QPushButton("Delete")
        delete.setEnabled(False)
        actions.addWidget(modify)
        actions.addWidget(delete)
        actions.addStretch(1)
        layout.addLayout(actions)

        add_current = QPushButton("Add Current Recipe's Setting")
        add_current.setEnabled(False)
        layout.addWidget(add_current, alignment=Qt.AlignHCenter)

        buttons = QHBoxLayout()
        buttons.addStretch(1)
        ok = QPushButton("OK")
        ok.setFixedWidth(90)
        ok.clicked.connect(self.accept)
        cancel = QPushButton("Cancel")
        cancel.setFixedWidth(90)
        cancel.clicked.connect(self.reject)
        buttons.addWidget(ok)
        buttons.addSpacing(28)
        buttons.addWidget(cancel)
        buttons.addStretch(1)
        layout.addLayout(buttons)
