from __future__ import annotations

import hashlib
import hmac
from dataclasses import dataclass
from datetime import date, timedelta

from . import theme
from .qt_compat import (
    QCheckBox,
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    Qt,
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
        self.setFixedSize(460, 322)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 18)
        layout.setSpacing(10)

        title = QLabel("Enter Startup Key")
        theme.role_label(title, "display")
        layout.addWidget(title)

        intro = QLabel(
            "A six-digit offline authorization key is required to open this software."
        )
        intro.setWordWrap(True)
        theme.role_label(intro, "caption")
        layout.addWidget(intro)

        panel = QFrame()
        panel.setObjectName("keyPanel")
        panel.setStyleSheet(
            "QFrame#keyPanel { background: #f7f5ee; border: 1px solid #a8a49a;"
            " border-radius: 3px; }"
        )
        panel_layout = QVBoxLayout(panel)
        panel_layout.setContentsMargins(14, 12, 14, 12)
        panel_layout.setSpacing(8)

        field_label = QLabel("Startup key")
        theme.role_label(field_label, "field")
        panel_layout.addWidget(field_label)

        self.key_input = QLineEdit()
        self.key_input.setMaxLength(KEY_LENGTH)
        self.key_input.setPlaceholderText("6-digit key")
        self.key_input.setEchoMode(QLineEdit.Password)
        self.key_input.setAlignment(Qt.AlignCenter)
        self.key_input.setStyleSheet(
            "QLineEdit { font-size: 22px; font-weight: 600; min-height: 38px;"
            " padding: 2px 10px; letter-spacing: 6px; }"
        )
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
        theme.role_label(self.period_label, "caption")
        layout.addWidget(self.period_label)
        self.status = QLabel(f"Attempts remaining: {MAX_ATTEMPTS}")
        theme.role_label(self.status, "caption")
        layout.addWidget(self.status)

        layout.addStretch(1)
        buttons = QHBoxLayout()
        buttons.setSpacing(8)
        buttons.addStretch(1)
        self.unlock_button = QPushButton("Unlock")
        theme.apply_role(self.unlock_button, "primary")
        self.unlock_button.clicked.connect(self._verify)
        cancel = QPushButton("Exit")
        cancel.clicked.connect(self.reject)
        buttons.addWidget(self.unlock_button)
        buttons.addWidget(cancel)
        layout.addLayout(buttons)

    def _verify(self):
        if verify_startup_key(self.key_input.text(), self.day):
            self.status.setText("Authorization accepted.")
            self.status.setStyleSheet("color: #2f7d3f; font-weight: 600;")
            self.accept()
            return

        self.attempts += 1
        remaining = MAX_ATTEMPTS - self.attempts
        self.key_input.clear()
        if remaining <= 0:
            self.status.setText("Too many invalid attempts. The software will close.")
            self.status.setStyleSheet("color: #a8332a; font-weight: 600;")
            self.reject()
            return
        self.status.setText(
            f"Invalid key. Attempts remaining: {remaining}"
        )
        self.status.setStyleSheet("color: #a8332a; font-weight: 600;")
        self.key_input.setFocus()
