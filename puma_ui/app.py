from __future__ import annotations

import sys

from .main_window import PumaMainWindow
from .interaction_guard import install_wheel_edit_guard
from .qt_compat import QApplication, Qt


def main():
    if hasattr(Qt, "AA_EnableHighDpiScaling"):
        QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    if hasattr(Qt, "AA_UseHighDpiPixmaps"):
        QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

    app = QApplication(sys.argv)
    app.setApplicationName("Puma 9980 UI Prototype")
    app.setStyle("Fusion")
    install_wheel_edit_guard(app)
    window = PumaMainWindow()
    window.show()
    if hasattr(app, "exec"):
        sys.exit(app.exec())
    sys.exit(app.exec_())
