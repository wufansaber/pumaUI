from __future__ import annotations

import os
import sys
from datetime import date
from pathlib import Path

if os.name != "nt":
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from key_generator import StartupKeyGeneratorDialog
from puma_ui.qt_compat import QApplication
from puma_ui.startup_access import StartupKeyDialog
try:
    from PySide6.QtTest import QTest
except ImportError:
    from PyQt5.QtTest import QTest


def save(widget, path):
    widget.show()
    QApplication.processEvents()
    QTest.qWait(80)
    widget.repaint()
    QApplication.processEvents()
    if not widget.grab().save(str(path)):
        raise RuntimeError(f"Unable to save {path}")
    widget.close()


def main():
    app = QApplication.instance() or QApplication([])
    app.setStyle("Fusion")
    output = ROOT / ".artifacts" / "startup-access-qa"
    output.mkdir(parents=True, exist_ok=True)

    day = date(2026, 9, 15)
    save(StartupKeyDialog(day), output / "startup-key-dialog.png")
    generator = StartupKeyGeneratorDialog()
    generator.date_input.setText(day.isoformat())
    generator._generate()
    save(generator, output / "startup-key-generator.png")
    print(f"Rendered startup access QA screenshots to {output}")


if __name__ == "__main__":
    main()
