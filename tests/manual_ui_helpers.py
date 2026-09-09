from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from puma_ui.qt_compat import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDialog,
    QLineEdit,
    QPushButton,
    Qt,
)

try:
    from PySide6.QtTest import QTest
except ImportError:
    from PyQt5.QtTest import QTest


def process_events(delay: int = 15) -> None:
    QTest.qWait(delay)
    QApplication.processEvents()


def click(widget) -> None:
    if not widget.isEnabled():
        raise AssertionError(f"Cannot click disabled widget: {widget!r}")
    if isinstance(widget, QCheckBox):
        widget.setFocus()
        QTest.keyClick(widget, Qt.Key_Space)
    else:
        QTest.mouseClick(
            widget,
            Qt.LeftButton,
            Qt.NoModifier,
            widget.rect().center(),
        )
    process_events()


def click_disabled(widget) -> None:
    if widget.isEnabled():
        raise AssertionError(f"Expected a disabled widget: {widget!r}")
    QTest.mouseClick(
        widget,
        Qt.LeftButton,
        Qt.NoModifier,
        widget.rect().center(),
    )
    process_events()


def visible_button(root, text: str) -> QPushButton:
    normalized = " ".join(text.split())
    matches = [
        button
        for button in root.findChildren(QPushButton)
        if button.isVisible() and " ".join(button.text().split()) == normalized
    ]
    if not matches:
        raise AssertionError(f"Visible button not found: {text!r}")
    enabled = [button for button in matches if button.isEnabled()]
    return enabled[0] if enabled else matches[0]


def replace_text(widget: QLineEdit, value: str) -> None:
    click(widget)
    QTest.keyClick(widget, Qt.Key_A, Qt.ControlModifier)
    QTest.keyClick(widget, Qt.Key_Backspace)
    if value:
        QTest.keyClicks(widget, value)
    process_events()


def select_combo(widget: QComboBox, text: str) -> None:
    index = widget.findText(text)
    if index < 0:
        raise AssertionError(f"Combo option not found: {text!r}")
    widget.setFocus()
    QTest.keyClick(widget, Qt.Key_Home)
    for _ in range(index):
        QTest.keyClick(widget, Qt.Key_Down)
    process_events()
    assert widget.currentText() == text


def close_workspace_page(window, button_text: str = "Cancel") -> None:
    page = window.workspace_stack.currentWidget()
    click(visible_button(page, button_text))
    process_events()
    assert window.workspace_stack.currentWidget() is not page
