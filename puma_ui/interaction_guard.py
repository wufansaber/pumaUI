from __future__ import annotations

from .qt_compat import (
    QApplication,
    QComboBox,
    QDoubleSpinBox,
    QEvent,
    QObject,
    QSlider,
    QSpinBox,
    QWidget,
)


class WheelEditGuard(QObject):
    """Require an explicit click before the wheel can edit a value control."""

    EDITOR_TYPES = (QComboBox, QSpinBox, QDoubleSpinBox, QSlider)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.active_editor = None

    def _editor_for(self, obj):
        current = obj if isinstance(obj, QWidget) else None
        while current is not None:
            if isinstance(current, self.EDITOR_TYPES):
                return current
            current = current.parentWidget()
        return None

    def _activate(self, editor):
        if self.active_editor is editor:
            return
        if self.active_editor is not None:
            try:
                self.active_editor.setProperty("wheelEditArmed", False)
            except RuntimeError:
                pass
        self.active_editor = editor
        editor.setProperty("wheelEditArmed", True)

    def _deactivate(self):
        if self.active_editor is not None:
            try:
                self.active_editor.setProperty("wheelEditArmed", False)
            except RuntimeError:
                pass
        self.active_editor = None

    def eventFilter(self, obj, event):  # noqa: N802 - Qt override
        event_type = event.type()
        if event_type not in (QEvent.MouseButtonPress, QEvent.Wheel):
            return False
        editor = self._editor_for(obj)
        if event_type == QEvent.MouseButtonPress:
            if editor is None:
                self._deactivate()
            else:
                self._activate(editor)
            return False
        if event_type == QEvent.Wheel and editor is not None:
            if editor is not self.active_editor or not editor.property("wheelEditArmed"):
                event.ignore()
                return True
        return False


def install_wheel_edit_guard(app=None):
    app = app or QApplication.instance()
    if app is None:
        return None
    existing = getattr(app, "_puma_wheel_edit_guard", None)
    if existing is not None:
        return existing
    guard = WheelEditGuard(app)
    app.installEventFilter(guard)
    app._puma_wheel_edit_guard = guard
    return guard
