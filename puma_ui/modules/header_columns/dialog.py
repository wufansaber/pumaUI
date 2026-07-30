from __future__ import annotations

from typing import Dict, List, Optional, Tuple

from ...qt_compat import QCheckBox, QDialog, QHBoxLayout, QPushButton, QVBoxLayout, QWidget


class ConfigureHeaderColumnsDialog(QDialog):
    def __init__(
        self,
        columns: List[Tuple[str, str]],
        visible_columns: Dict[str, bool],
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self.setWindowTitle("Configure Header Columns")
        self.setFixedSize(300, 330)
        self.columns = columns
        self.visible_columns = dict(visible_columns)
        self.result_columns = None
        self.checkboxes = {}
        self._build_ui()

    def _build_ui(self):
        self.setStyleSheet(
            """
            QDialog {
                background: #d7d4c9;
                font-family: Arial, Helvetica, sans-serif;
                font-size: 10px;
            }
            QPushButton {
                background: #e7e5dc;
                border-top: 1px solid #ffffff;
                border-left: 1px solid #ffffff;
                border-right: 1px solid #77736b;
                border-bottom: 1px solid #77736b;
                min-height: 26px;
                padding: 2px 14px;
            }
            """
        )
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 12)
        layout.setSpacing(8)

        for key, title in self.columns:
            checkbox = QCheckBox(title)
            checkbox.setChecked(self.visible_columns.get(key, True))
            self.checkboxes[key] = checkbox
            layout.addWidget(checkbox)

        layout.addStretch(1)
        buttons = QHBoxLayout()
        reset = QPushButton("Reset")
        reset.clicked.connect(self._reset)
        cancel = QPushButton("Cancel")
        cancel.clicked.connect(self.reject)
        ok = QPushButton("OK")
        ok.clicked.connect(self._accept)
        buttons.addWidget(reset)
        buttons.addStretch(1)
        buttons.addWidget(cancel)
        buttons.addWidget(ok)
        layout.addLayout(buttons)

    def _reset(self):
        for index, (key, title) in enumerate(self.columns):
            self.checkboxes[key].setChecked(index < 4)

    def _accept(self):
        self.result_columns = {key: checkbox.isChecked() for key, checkbox in self.checkboxes.items()}
        if not any(self.result_columns.values()):
            first_key = self.columns[0][0]
            self.result_columns[first_key] = True
        self.accept()
