from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class ProjectDocumentationTests(unittest.TestCase):
    def test_internal_manual_is_not_distributed(self):
        self.assertFalse((ROOT / "docs" / "UserManual-9980.pdf").exists())
        self.assertFalse((ROOT / "docs" / "UserManual-9980-zh").exists())
        spec = (ROOT / "Puma9980UI.spec").read_text(encoding="utf-8")
        self.assertNotIn("UserManual-9980", spec)

    def test_help_uses_bundled_project_guide(self):
        self.assertTrue((ROOT / "docs" / "OPERATOR_GUIDE.md").is_file())
        source = (ROOT / "puma_ui" / "main_window.py").read_text(encoding="utf-8")
        self.assertNotIn("UserManual-9980.pdf", source)
        spec = (ROOT / "Puma9980UI.spec").read_text(encoding="utf-8")
        self.assertIn("docs/OPERATOR_GUIDE.md", spec)
