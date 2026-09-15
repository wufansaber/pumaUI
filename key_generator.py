from __future__ import annotations

import argparse
import sys
from datetime import date

from puma_ui.qt_compat import (
    QApplication,
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)
from puma_ui.startup_access import generate_startup_key, key_period


class StartupKeyGeneratorDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Puma 9980 Startup Key Generator")
        self.setFixedSize(470, 300)
        self.setStyleSheet(
            "QDialog { background: #cfcbc2; font-family: Arial; font-size: 11px; }"
            "QLineEdit { background: white; border: 1px solid #77736b; min-height: 28px; }"
            "QPushButton { background: #e8e6dd; border: 1px solid #77736b; "
            "min-height: 30px; padding: 2px 12px; }"
            "QFrame#resultPanel { background: #efede5; border: 1px solid #8c8982; }"
        )

        layout = QVBoxLayout(self)
        title = QLabel("Offline Startup Key Generator")
        title.setStyleSheet("font-size: 16px; font-weight: 700;")
        layout.addWidget(title)

        date_row = QHBoxLayout()
        date_row.addWidget(QLabel("Date (YYYY-MM-DD):"))
        self.date_input = QLineEdit(date.today().isoformat())
        self.date_input.returnPressed.connect(self._generate)
        date_row.addWidget(self.date_input, 1)
        self.generate_button = QPushButton("Generate")
        self.generate_button.clicked.connect(self._generate)
        date_row.addWidget(self.generate_button)
        layout.addLayout(date_row)

        panel = QFrame()
        panel.setObjectName("resultPanel")
        panel_layout = QVBoxLayout(panel)
        panel_layout.addWidget(QLabel("Six-digit startup key"))
        self.key_label = QLabel()
        self.key_label.setStyleSheet(
            "font-family: Consolas; font-size: 34px; font-weight: 700; color: #173f5f;"
        )
        panel_layout.addWidget(self.key_label)
        self.validity_label = QLabel()
        panel_layout.addWidget(self.validity_label)
        layout.addWidget(panel)

        buttons = QHBoxLayout()
        self.copy_button = QPushButton("Copy Key")
        self.copy_button.clicked.connect(self._copy)
        close = QPushButton("Close")
        close.clicked.connect(self.accept)
        buttons.addWidget(self.copy_button)
        buttons.addStretch(1)
        buttons.addWidget(close)
        layout.addLayout(buttons)
        self._generate()

    def _selected_date(self):
        try:
            return date.fromisoformat(self.date_input.text().strip())
        except ValueError:
            QMessageBox.warning(
                self,
                "Invalid Date",
                "Enter the date in YYYY-MM-DD format.",
            )
            return None

    def _generate(self):
        selected = self._selected_date()
        if selected is None:
            return
        period = key_period(selected)
        self.key_label.setText(generate_startup_key(selected))
        self.validity_label.setText(
            f"Valid from {period.starts_on.isoformat()} through {period.ends_on.isoformat()}"
        )

    def _copy(self):
        QApplication.clipboard().setText(self.key_label.text())


def main(arguments=None):
    parser = argparse.ArgumentParser(description="Generate a Puma 9980 startup key.")
    parser.add_argument("--date", help="Date in YYYY-MM-DD format")
    options = parser.parse_args(arguments)
    if options.date:
        selected = date.fromisoformat(options.date)
        period = key_period(selected)
        print(generate_startup_key(selected))
        print(f"Valid: {period.starts_on.isoformat()} through {period.ends_on.isoformat()}")
        return 0

    app = QApplication.instance() or QApplication(sys.argv)
    app.setApplicationName("Puma 9980 Startup Key Generator")
    app.setStyle("Fusion")
    dialog = StartupKeyGeneratorDialog()
    dialog.show()
    if hasattr(app, "exec"):
        return app.exec()
    return app.exec_()


if __name__ == "__main__":
    raise SystemExit(main())

