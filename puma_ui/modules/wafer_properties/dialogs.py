from __future__ import annotations

from copy import deepcopy
from typing import Optional

from ...qt_compat import (
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QDialog,
    QDoubleSpinBox,
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
    "layer_types": [
        {"name": "_KT_Low_Power", "laser_power_limit": 0.035},
        {"name": "9000 Power Limit", "laser_power_limit": 0.121},
        {"name": "9000 Dose Limit", "laser_power_limit": 0.242},
    ],
}


class WaferMenuDialog(QDialog):
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setWindowTitle("Wafer")
        self.setFixedSize(190, 250)
        self.open_wafer_properties = False
        self.open_alignment = False
        self.open_wafer_map = False
        self.open_select_defect_data = False
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
        defect_data = ClassicButton("Select Defect\nData", arrow=True)
        defect_data.clicked.connect(self._accept_select_defect_data)
        layout.addWidget(defect_data)
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

    def _accept_select_defect_data(self):
        self.open_select_defect_data = True
        self.accept()


class WaferPropertiesDialog(QDialog):
    def __init__(self, properties=None, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setWindowTitle("Wafer Properties")
        self.properties = deepcopy(DEFAULT_WAFER_PROPERTIES)
        if properties:
            self.properties.update(deepcopy(properties))
        self.result_properties = None
        self._original_orientation = self.properties["orientation"]
        self._original_type = self.properties["type"]
        self._laser_scale = 10000000
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
        self.layer_combo.currentIndexChanged.connect(self._layer_changed)
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
        current_layer = self.properties.get("layer", "")
        current_name = current_layer.split(" [", 1)[0]
        self._reload_layers(self.properties.get("layer_types"), current_name)
        for index in range(self.layer_combo.count()):
            if self.layer_combo.itemData(index)["name"] == current_name:
                self.layer_combo.setCurrentIndex(index)
                break
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
        current = self.layer_combo.currentData() or {}
        dialog = EditLayerDatabaseDialog(
            self.properties.get("layer_types"), current.get("name"), self,
        )
        result = dialog.exec() if hasattr(dialog, "exec") else dialog.exec_()
        if result == QDialog.Accepted and dialog.result_layers is not None:
            self.properties["layer_types"] = deepcopy(dialog.result_layers)
            self._reload_layers(dialog.result_layers, dialog.selected_layer_name)

    @staticmethod
    def _layer_text(layer):
        return f"{layer['name']} [ {float(layer['laser_power_limit']):.5f} ]"

    def _reload_layers(self, layers=None, selected_name=None):
        layers = deepcopy(layers or DEFAULT_WAFER_PROPERTIES["layer_types"])
        if not selected_name and self.layer_combo.currentData():
            selected_name = self.layer_combo.currentData().get("name")
        self.layer_combo.blockSignals(True)
        self.layer_combo.clear()
        for layer in layers:
            self.layer_combo.addItem(self._layer_text(layer), layer)
        match = next(
            (index for index in range(self.layer_combo.count())
             if self.layer_combo.itemData(index).get("name") == selected_name),
            0,
        )
        self.layer_combo.setCurrentIndex(match)
        self.layer_combo.blockSignals(False)
        self._layer_changed(match)

    def _layer_changed(self, index):
        layer = self.layer_combo.itemData(index) if index >= 0 else None
        if not layer or not hasattr(self, "laser_power_factor"):
            return
        limit = float(layer.get("laser_power_limit", self._laser_max))
        try:
            current = float(self.laser_power_factor.text())
        except ValueError:
            current = limit
        if current > limit:
            self._set_laser_factor(limit)

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

        orientation_changed = self.orientation_combo.currentText() != self._original_orientation
        type_changed = self.type_combo.currentText() != self._original_type
        if orientation_changed:
            proceed = QMessageBox.question(
                self,
                "Wafer Orientation",
                "Changing wafer orientation will lose alignment data and rotate wafer geometry. "
                "Save the modified inspection under a new name?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if proceed != QMessageBox.Yes:
                return
        if type_changed:
            proceed = QMessageBox.warning(
                self,
                "Wafer Type",
                "Changing wafer type will invalidate all tests for this recipe.",
                QMessageBox.Ok | QMessageBox.Cancel,
                QMessageBox.Cancel,
            )
            if proceed != QMessageBox.Ok:
                return

        self.result_properties = {
            "orientation": self.orientation_combo.currentText(),
            "type": self.type_combo.currentText(),
            "laser_power_sensitive": self.laser_power_sensitive.isChecked(),
            "laser_power_factor": factor_text,
            "layer": self.layer_combo.currentText(),
            "layer_types": [
                deepcopy(self.layer_combo.itemData(index))
                for index in range(self.layer_combo.count())
            ],
            "dark_wafer_auto_focus": self.dark_wafer_auto_focus.isChecked(),
            "wafer_darkness_level": self.dark_level_value.text(),
            "orientation_changed": orientation_changed,
            "type_changed": type_changed,
        }
        self.accept()


class LayerSettingDialog(QDialog):
    def __init__(self, layer=None, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.result_layer = None
        self.setWindowTitle("Modify a Layer" if layer else "Add a Layer")
        layout = QGridLayout(self)
        layout.addWidget(QLabel("Layer Name"), 0, 0)
        self.name = QLineEdit(str((layer or {}).get("name", "")))
        self.name.setMaxLength(32)
        layout.addWidget(self.name, 0, 1)
        layout.addWidget(QLabel("Laser Power Limit"), 1, 0)
        self.limit = QDoubleSpinBox()
        self.limit.setRange(0.0, 10.0)
        self.limit.setDecimals(7)
        self.limit.setValue(float((layer or {}).get("laser_power_limit", 0.035)))
        layout.addWidget(self.limit, 1, 1)
        buttons = QHBoxLayout()
        buttons.addStretch(1)
        ok = QPushButton("OK")
        ok.clicked.connect(self._finish)
        cancel = QPushButton("Cancel")
        cancel.clicked.connect(self.reject)
        buttons.addWidget(ok)
        buttons.addWidget(cancel)
        layout.addLayout(buttons, 2, 0, 1, 2)

    def _finish(self):
        name = self.name.text().strip()
        if not name:
            QMessageBox.warning(self, "Layer", "Layer name is required.")
            return
        self.result_layer = {"name": name, "laser_power_limit": self.limit.value()}
        self.accept()


class EditLayerDatabaseDialog(QDialog):
    def __init__(self, layers=None, selected_layer_name=None, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.layers = deepcopy(layers or DEFAULT_WAFER_PROPERTIES["layer_types"])
        self.selected_layer_name = selected_layer_name
        self.result_layers = None
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

        self.table = QTableWidget(0, 2)
        self.table.setHorizontalHeaderLabels(["Layer", "Laser Power Limit"])
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table.itemSelectionChanged.connect(self._selection_changed)
        self.table.itemDoubleClicked.connect(lambda _item: self._modify())
        layout.addWidget(self.table, 1)

        actions = QHBoxLayout()
        actions.addStretch(1)
        add = QPushButton("Add...")
        add.clicked.connect(self._add)
        self.modify_button = QPushButton("Modify...")
        self.delete_button = QPushButton("Delete")
        self.modify_button.clicked.connect(self._modify)
        self.delete_button.clicked.connect(self._delete)
        actions.addWidget(add)
        actions.addWidget(self.modify_button)
        actions.addWidget(self.delete_button)
        actions.addStretch(1)
        layout.addLayout(actions)

        self.add_current = QPushButton("Add Current Recipe's Setting")
        self.add_current.setEnabled(False)
        layout.addWidget(self.add_current, alignment=Qt.AlignHCenter)

        buttons = QHBoxLayout()
        buttons.addStretch(1)
        ok = QPushButton("OK")
        ok.setFixedWidth(90)
        ok.clicked.connect(self._finish)
        cancel = QPushButton("Cancel")
        cancel.setFixedWidth(90)
        cancel.clicked.connect(self.reject)
        buttons.addWidget(ok)
        buttons.addSpacing(28)
        buttons.addWidget(cancel)
        buttons.addStretch(1)
        layout.addLayout(buttons)
        self._refresh()

    def _refresh(self, selected_name=None):
        selected_name = selected_name or self.selected_layer_name
        self.table.blockSignals(True)
        self.table.setRowCount(0)
        selected_row = -1
        for layer in self.layers:
            row = self.table.rowCount()
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(layer["name"]))
            self.table.setItem(row, 1, QTableWidgetItem(f"{float(layer['laser_power_limit']):.7f}"))
            if layer["name"] == selected_name:
                selected_row = row
        self.table.blockSignals(False)
        if selected_row >= 0:
            self.table.selectRow(selected_row)
        self._selection_changed()

    def _selected_row(self):
        rows = self.table.selectionModel().selectedRows()
        return rows[0].row() if rows else -1

    def _selection_changed(self):
        enabled = self._selected_row() >= 0
        self.modify_button.setEnabled(enabled)
        self.delete_button.setEnabled(enabled)

    def _insert_layer(self, layer, replace_row=None):
        name = str(layer.get("name", "")).strip()
        limit = float(layer.get("laser_power_limit", -1))
        if not name or len(name) > 32:
            QMessageBox.warning(self, "Layer", "Layer name must contain 1 to 32 characters.")
            return False
        if limit < 0 or limit > 10:
            QMessageBox.warning(self, "Layer", "Laser power limit must be between 0 and 10.")
            return False
        if any(item["name"] == name for index, item in enumerate(self.layers) if index != replace_row):
            QMessageBox.warning(self, "Layer", "Layer name must be unique.")
            return False
        normalized = {"name": name, "laser_power_limit": limit}
        if replace_row is None:
            self.layers.append(normalized)
        else:
            self.layers[replace_row] = normalized
        self.selected_layer_name = name
        self._refresh(name)
        return True

    def _add(self):
        dialog = LayerSettingDialog(parent=self)
        if (dialog.exec() if hasattr(dialog, "exec") else dialog.exec_()) == QDialog.Accepted:
            self._insert_layer(dialog.result_layer)

    def _modify(self):
        row = self._selected_row()
        if row < 0:
            return
        dialog = LayerSettingDialog(self.layers[row], self)
        if (dialog.exec() if hasattr(dialog, "exec") else dialog.exec_()) == QDialog.Accepted:
            self._insert_layer(dialog.result_layer, row)

    def _delete(self):
        row = self._selected_row()
        if row < 0:
            return
        self.layers.pop(row)
        if not self.layers:
            self.selected_layer_name = None
        elif row < len(self.layers):
            self.selected_layer_name = self.layers[row]["name"]
        else:
            self.selected_layer_name = self.layers[-1]["name"]
        self._refresh(self.selected_layer_name)

    def _finish(self):
        if not self.layers:
            QMessageBox.warning(self, "Layer Database", "At least one layer is required.")
            return
        row = self._selected_row()
        self.selected_layer_name = self.layers[row]["name"] if row >= 0 else self.layers[0]["name"]
        self.result_layers = deepcopy(self.layers)
        self.accept()
