from __future__ import annotations

import unittest
from datetime import date, timedelta
from unittest.mock import MagicMock, patch

from key_generator import StartupKeyGeneratorDialog
from puma_ui import app as app_module
from puma_ui.qt_compat import QApplication, QDialog
from puma_ui.startup_access import (
    KEY_LENGTH,
    KEY_PERIOD_DAYS,
    MAX_ATTEMPTS,
    StartupKeyDialog,
    generate_startup_key,
    key_period,
    verify_startup_key,
)


class StartupAccessTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_key_is_six_ascii_digits_and_deterministic(self):
        day = date(2026, 9, 15)
        generated = generate_startup_key(day)
        self.assertEqual(generated, "745213")
        self.assertEqual(len(generated), KEY_LENGTH)
        self.assertTrue(generated.isascii())
        self.assertTrue(generated.isdigit())
        self.assertEqual(generate_startup_key(day), generated)

    def test_key_changes_only_at_five_day_period_boundary(self):
        day = date(2026, 9, 15)
        period = key_period(day)
        self.assertEqual((period.ends_on - period.starts_on).days + 1, KEY_PERIOD_DAYS)
        self.assertEqual(generate_startup_key(period.starts_on), generate_startup_key(period.ends_on))
        self.assertNotEqual(
            generate_startup_key(period.ends_on),
            generate_startup_key(period.ends_on + timedelta(days=1)),
        )

    def test_verification_rejects_wrong_shape_and_wrong_period(self):
        day = date(2026, 9, 15)
        key = generate_startup_key(day)
        self.assertTrue(verify_startup_key(key, day))
        self.assertFalse(verify_startup_key(key, day + timedelta(days=KEY_PERIOD_DAYS)))
        self.assertFalse(verify_startup_key("12345", day))
        self.assertFalse(verify_startup_key("12345A", day))
        self.assertFalse(verify_startup_key("１２３４５６", day))

    def test_startup_dialog_accepts_current_key(self):
        day = date(2026, 9, 15)
        dialog = StartupKeyDialog(day)
        dialog.key_input.setText(generate_startup_key(day))
        dialog._verify()
        self.assertEqual(dialog.result(), QDialog.Accepted)

    def test_startup_dialog_rejects_after_five_invalid_attempts(self):
        dialog = StartupKeyDialog(date(2026, 9, 15))
        for _ in range(MAX_ATTEMPTS):
            dialog.key_input.setText("000000")
            dialog._verify()
        self.assertEqual(dialog.attempts, MAX_ATTEMPTS)
        self.assertEqual(dialog.result(), QDialog.Rejected)
        self.assertIn("Too many", dialog.status.text())

    def test_generator_displays_key_and_validity_for_selected_date(self):
        dialog = StartupKeyGeneratorDialog()
        dialog.date_input.setText("2026-09-15")
        dialog._generate()
        self.assertEqual(dialog.key_label.text(), generate_startup_key(date(2026, 9, 15)))
        self.assertIn("2026-09-13", dialog.validity_label.text())
        self.assertIn("2026-09-17", dialog.validity_label.text())

    def test_application_does_not_create_main_window_when_key_dialog_is_rejected(self):
        fake_application = MagicMock()
        fake_key_dialog = MagicMock()
        fake_key_dialog.exec.return_value = QDialog.Rejected
        with patch.object(app_module, "QApplication", return_value=fake_application), patch.object(
            app_module, "StartupKeyDialog", return_value=fake_key_dialog
        ), patch.object(app_module, "PumaMainWindow") as main_window:
            result = app_module.main()
        self.assertEqual(result, 1)
        main_window.assert_not_called()

    def test_application_opens_main_window_after_key_is_accepted(self):
        fake_application = MagicMock()
        fake_application.exec.return_value = 0
        fake_key_dialog = MagicMock()
        fake_key_dialog.exec.return_value = QDialog.Accepted
        fake_window = MagicMock()
        with patch.object(app_module, "QApplication", return_value=fake_application), patch.object(
            app_module, "StartupKeyDialog", return_value=fake_key_dialog
        ), patch.object(app_module, "PumaMainWindow", return_value=fake_window):
            result = app_module.main()
        self.assertEqual(result, 0)
        fake_window.show.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
