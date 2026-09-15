from __future__ import annotations

import hashlib
import hmac
from dataclasses import dataclass
from datetime import date, timedelta

from .qt_compat import (
    QCheckBox,
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
)


KEY_LENGTH = 6
KEY_PERIOD_DAYS = 5
KEY_EPOCH = date(2026, 1, 1)
MAX_ATTEMPTS = 5

# This seed is shared only by the operator validator and the separately
# distributed administrator generator. Changing it invalidates every key.
_KEY_SEED = bytes.fromhex(
    "8251b8d19235a255afbd569a79b2d94c"
    "e11ee2108a9f8f940d600dce817d02c9"
)


@dataclass(frozen=True)
class KeyPeriod:
    index: int
    starts_on: date
    ends_on: date


def key_period(day: date | None = None) -> KeyPeriod:
    target = day or date.today()
    elapsed_days = (target - KEY_EPOCH).days
    index = elapsed_days // KEY_PERIOD_DAYS
    starts_on = KEY_EPOCH + timedelta(days=index * KEY_PERIOD_DAYS)
    return KeyPeriod(
        index=index,
        starts_on=starts_on,
        ends_on=starts_on + timedelta(days=KEY_PERIOD_DAYS - 1),
    )


def generate_startup_key(day: date | None = None) -> str:
    period = key_period(day)
    message = f"PUMA9980|STARTUP|V1|{period.index:+012d}".encode("ascii")
    digest = hmac.new(_KEY_SEED, message, hashlib.sha256).digest()
    offset = digest[-1] & 0x0F
    binary = int.from_bytes(digest[offset : offset + 4], "big") & 0x7FFFFFFF
    return f"{binary % (10 ** KEY_LENGTH):0{KEY_LENGTH}d}"


def verify_startup_key(value: str, day: date | None = None) -> bool:
    candidate = str(value or "").strip()
    if len(candidate) != KEY_LENGTH or not candidate.isascii() or not candidate.isdigit():
        return False
    return hmac.compare_digest(candidate, generate_startup_key(day))


class StartupKeyDialog(QDialog):
    def __init__(self, day: date | None = None, parent=None):
        super().__init__(parent)
        self.day = day or date.today()
        self.attempts = 0
        period = key_period(self.day)
        self.setWindowTitle("Puma 9980 - Startup Authorization")
        self.setFixedSize(430, 260)
        self.setStyleSheet(
            "QDialog { background: #cfcbc2; font-family: Arial; font-size: 11px; }"
            "QLineEdit { background: white; border: 1px solid #77736b; "
            "font-size: 22px; min-height: 38px; padding: 2px 8px; }"
            "QPushButton { background: #e8e6dd; border: 1px solid #77736b; "
            "min-height: 30px; padding: 2px 12px; }"
            "QFrame#keyPanel { background: #efede5; border: 1px solid #8c8982; }"
        )

        layout = QVBoxLayout(self)
        title = QLabel("Enter Startup Key")
        title.setStyleSheet("font-size: 16px; font-weight: 700;")
        layout.addWidget(title)
        layout.addWidget(
            QLabel(
                "A six-digit offline authorization key is required to open this software."
            )
        )

        panel = QFrame()
        panel.setObjectName("keyPanel")
        panel_layout = QVBoxLayout(panel)
        self.key_input = QLineEdit()
        self.key_input.setMaxLength(KEY_LENGTH)
        self.key_input.setPlaceholderText("6-digit key")
        self.key_input.setEchoMode(QLineEdit.Password)
        self.key_input.returnPressed.connect(self._verify)
        panel_layout.addWidget(self.key_input)

        self.show_key = QCheckBox("Show key")
        self.show_key.toggled.connect(
            lambda checked: self.key_input.setEchoMode(
                QLineEdit.Normal if checked else QLineEdit.Password
            )
        )
        panel_layout.addWidget(self.show_key)
        layout.addWidget(panel)

        self.period_label = QLabel(
            f"Current key period: {period.starts_on.isoformat()} through "
            f"{period.ends_on.isoformat()}"
        )
        layout.addWidget(self.period_label)
        self.status = QLabel(f"Attempts remaining: {MAX_ATTEMPTS}")
        self.status.setStyleSheet("color: #333333;")
        layout.addWidget(self.status)

        buttons = QHBoxLayout()
        buttons.addStretch(1)
        self.unlock_button = QPushButton("Unlock")
        self.unlock_button.clicked.connect(self._verify)
        cancel = QPushButton("Exit")
        cancel.clicked.connect(self.reject)
        buttons.addWidget(self.unlock_button)
        buttons.addWidget(cancel)
        layout.addLayout(buttons)

    def _verify(self):
        if verify_startup_key(self.key_input.text(), self.day):
            self.status.setText("Authorization accepted.")
            self.accept()
            return

        self.attempts += 1
        remaining = MAX_ATTEMPTS - self.attempts
        self.key_input.clear()
        if remaining <= 0:
            self.status.setText("Too many invalid attempts. The software will close.")
            self.reject()
            return
        self.status.setText(
            f"Invalid key. Attempts remaining: {remaining}"
        )
        self.status.setStyleSheet("color: #b00020; font-weight: 700;")
        self.key_input.setFocus()

