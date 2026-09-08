from __future__ import annotations

from datetime import datetime
from pathlib import Path

from ...qt_compat import (
    QAbstractItemView,
    QComboBox,
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    Qt,
    QVBoxLayout,
)
from ...widgets import ClassicButton
from ..results_review.models import import_klarf_text


LOT_RESULTS = [
    ("Lot_300_180_001", "Deep", "Wafer 01", "Valid", "2026-08-31 14:25:10"),
    ("Lot_300_180_002", "Deep", "Wafer 12", "Valid", "2026-09-01 09:18:42"),
    ("Engineering_DOI", "Layer1", "Wafer 03", "Complete", "2026-09-02 17:03:21"),
]


class SelectDefectDataDialog(QDialog):
    def __init__(self, attached_data=None, parent=None):
        super().__init__(parent)
        self.attached_data = dict(attached_data or {})
        self.changed = False
        self.setWindowTitle("Select Defect Data")
        self.setFixedSize(280, 330)
        self.setStyleSheet(
            "QDialog { background: #d7d4c9; font-family: Arial; font-size: 10px; }"
            "QPushButton { min-height: 30px; }"
        )
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 18)
        layout.setSpacing(12)
        title = QLabel("Attach defect data for Setup-Review")
        title.setStyleSheet("font-weight: 700;")
        layout.addWidget(title)
        select_lot = ClassicButton("Select Lot", arrow=True)
        select_lot.clicked.connect(self._select_lot)
        layout.addWidget(select_lot)
        import_klarf = ClassicButton("Import KLARF", arrow=True)
        import_klarf.clicked.connect(self._import_klarf)
        layout.addWidget(import_klarf)
        self.detach_button = ClassicButton("Detach Defect Data")
        self.detach_button.clicked.connect(self._detach)
        layout.addWidget(self.detach_button)
        self.status = QLabel()
        self.status.setWordWrap(True)
        self.status.setFrameStyle(QLabel.Panel | QLabel.Sunken)
        self.status.setMinimumHeight(58)
        layout.addWidget(self.status)
        layout.addStretch(1)
        end = ClassicButton("End")
        end.clicked.connect(self.accept)
        layout.addWidget(end)
        self._refresh_status()

    def _select_lot(self):
        dialog = SelectLotResultsDialog(self)
        result = dialog.exec() if hasattr(dialog, "exec") else dialog.exec_()
        if result == QDialog.Accepted and dialog.selected_result:
            self.attached_data = dialog.selected_result
            self.changed = True
            self._refresh_status()

    def _import_klarf(self):
        filename, _ = QFileDialog.getOpenFileName(
            self,
            "Open KLARF",
            str(Path.home()),
            "KLARF Files (*.klarf *.001 *.txt);;All Files (*)",
        )
        if not filename:
            return
        save_dialog = SaveImportedLotResultDialog(Path(filename).stem, self)
        result = save_dialog.exec() if hasattr(save_dialog, "exec") else save_dialog.exec_()
        if result != QDialog.Accepted:
            return
        try:
            text = Path(filename).read_text(encoding="utf-8", errors="replace")
            parsed = import_klarf_text(text, source_path=filename)
        except (OSError, ValueError) as exc:
            QMessageBox.warning(self, "Import KLARF", str(exc))
            return
        wafer_dialog = SelectImportedWaferDialog([parsed.get("wafer_id", "ImportedWafer")], self)
        wafer_result = wafer_dialog.exec() if hasattr(wafer_dialog, "exec") else wafer_dialog.exec_()
        if wafer_result != QDialog.Accepted:
            return
        parsed.update(
            {
                "type": "Lot Result",
                "name": save_dialog.name_edit.text().strip(),
                "source": filename,
                "wafer": wafer_dialog.selected_wafer,
                "wafer_id": wafer_dialog.selected_wafer,
                "attached": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "status": "Converted from KLARF",
            }
        )
        self.attached_data = parsed
        self.changed = True
        self._refresh_status()

    def _detach(self):
        if not self.attached_data:
            return
        answer = QMessageBox.question(
            self,
            "Detach Defect Data",
            "Detach the currently attached defect data from this recipe?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if answer == QMessageBox.Yes:
            self.attached_data = {}
            self.changed = True
            self._refresh_status()

    def _refresh_status(self):
        if self.attached_data:
            self.status.setText(
                f"Attached: {self.attached_data.get('name', '')}\n"
                f"Type: {self.attached_data.get('type', 'Lot Result')}"
            )
        else:
            self.status.setText("No defect data attached.")
        self.detach_button.setEnabled(bool(self.attached_data))

    @staticmethod
    def _simulated_defects(seed: str):
        shift = sum(ord(character) for character in seed) % 9 / 100.0
        return [
            {"id": 1, "x": 0.22 + shift, "y": 0.28, "class_code": 0},
            {"id": 2, "x": 0.51, "y": 0.46 + shift, "class_code": 0},
            {"id": 3, "x": 0.72 - shift, "y": 0.68, "class_code": 0},
        ]


class SelectLotResultsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.selected_result = None
        self.setWindowTitle("Select Lot Results")
        self.resize(760, 490)
        self.setStyleSheet(
            "QDialog { background: #efede2; font-family: Arial; font-size: 10px; }"
            "QLineEdit, QTableWidget { background: white; min-height: 24px; }"
            "QPushButton { min-width: 86px; min-height: 24px; }"
        )
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 16)
        search_row = QHBoxLayout()
        search_row.addWidget(QLabel("Find"))
        self.find_edit = QLineEdit()
        self.find_edit.textChanged.connect(self._populate)
        search_row.addWidget(self.find_edit, 1)
        clear = QPushButton("Clear")
        clear.clicked.connect(self.find_edit.clear)
        search_row.addWidget(clear)
        layout.addLayout(search_row)

        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["Name", "Process Step", "Wafer", "Status", "Inspection Time"])
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.doubleClicked.connect(self._open)
        layout.addWidget(self.table, 1)
        buttons = QHBoxLayout()
        buttons.addStretch(1)
        open_button = QPushButton("Open")
        open_button.clicked.connect(self._open)
        cancel = QPushButton("Cancel")
        cancel.clicked.connect(self.reject)
        buttons.addWidget(open_button)
        buttons.addWidget(cancel)
        layout.addLayout(buttons)
        self._populate()

    def _populate(self, text: str = ""):
        needle = text.strip().lower()
        rows = [row for row in LOT_RESULTS if not needle or needle in " ".join(row).lower()]
        self.table.setRowCount(0)
        for values in rows:
            row = self.table.rowCount()
            self.table.insertRow(row)
            for column, value in enumerate(values):
                self.table.setItem(row, column, QTableWidgetItem(value))
        if rows:
            self.table.selectRow(0)

    def _open(self):
        row = self.table.currentRow()
        if row < 0:
            return
        self.selected_result = {
            "type": "Lot Result",
            "name": self.table.item(row, 0).text(),
            "step": self.table.item(row, 1).text(),
            "wafer": self.table.item(row, 2).text(),
            "status": self.table.item(row, 3).text(),
            "attached": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "defects": SelectDefectDataDialog._simulated_defects(
                self.table.item(row, 0).text()
            ),
        }
        self.accept()


class SaveImportedLotResultDialog(QDialog):
    def __init__(self, default_name: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Save Lot Results")
        self.setFixedSize(420, 180)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 22, 24, 18)
        row = QHBoxLayout()
        row.addWidget(QLabel("Lot Result Name:"))
        self.name_edit = QLineEdit(default_name)
        row.addWidget(self.name_edit, 1)
        layout.addLayout(row)
        layout.addStretch(1)
        buttons = QHBoxLayout()
        buttons.addStretch(1)
        save = QPushButton("Save")
        save.clicked.connect(self._accept)
        cancel = QPushButton("Cancel")
        cancel.clicked.connect(self.reject)
        buttons.addWidget(save)
        buttons.addWidget(cancel)
        layout.addLayout(buttons)

    def _accept(self):
        if not self.name_edit.text().strip():
            QMessageBox.warning(self, "Save Lot Results", "Lot Result Name is required.")
            return
        self.accept()


class SelectImportedWaferDialog(QDialog):
    def __init__(self, wafer_ids, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Select Wafer")
        self.setFixedSize(360, 180)
        self.selected_wafer = ""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 22, 24, 18)
        layout.addWidget(QLabel("Select the Wafer ID to attach to the inspection recipe."))
        self.wafer_combo = QComboBox()
        self.wafer_combo.addItems([str(item) for item in wafer_ids if str(item).strip()])
        self.selected_wafer = self.wafer_combo.currentText()
        layout.addWidget(self.wafer_combo)
        layout.addStretch(1)
        buttons = QHBoxLayout()
        buttons.addStretch(1)
        ok = QPushButton("OK")
        ok.clicked.connect(self._accept)
        cancel = QPushButton("Cancel")
        cancel.clicked.connect(self.reject)
        buttons.addWidget(ok)
        buttons.addWidget(cancel)
        layout.addLayout(buttons)

    def _accept(self):
        self.selected_wafer = self.wafer_combo.currentText().strip()
        if not self.selected_wafer:
            QMessageBox.warning(self, "Select Wafer", "Select a Wafer ID before continuing.")
            return
        self.accept()
