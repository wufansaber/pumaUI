from __future__ import annotations

from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]
MANUAL = ROOT / "docs" / "UserManual-9980-zh"
AUDIT = ROOT / "docs" / "MANUAL_PAGE_AUDIT.md"


def number_tuple(value: str):
    parts = value.strip().split(".")
    first = parts[0].upper()
    chapter = ord(first) - ord("A") + 15 if first in {"A", "B", "C"} else int(first)
    return (chapter, *(int(part) for part in parts[1:]))


def covered(number: str, ranges):
    target = number_tuple(number)
    for start, end in ranges:
        if start[: len(target)] == target:
            return True
        if end is None:
            if target[: len(start)] == start:
                return True
            continue
        width = max(len(target), len(start), len(end))
        low = start + (0,) * (width - len(start))
        high = end + (999,) * (width - len(end))
        probe = target + (0,) * (width - len(target))
        if low <= probe <= high:
            return True
    return False


class ManualDocumentCoverageTests(unittest.TestCase):
    def test_every_numbered_manual_heading_has_a_final_audit_range(self):
        audit_text = AUDIT.read_text(encoding="utf-8")
        self.assertNotIn("| PENDING", audit_text)
        self.assertNotIn("| PARTIAL", audit_text)
        ranges = []
        for cell in re.findall(r"^\|\s*([^|]+?)\s*\|", audit_text, re.MULTILINE):
            match = re.fullmatch(r"([0-9A-C]+(?:\.[0-9]+)+)(?:-([0-9A-C]+(?:\.[0-9]+)+|end))?", cell.strip())
            if not match:
                continue
            start = number_tuple(match.group(1))
            if match.group(2) == "end":
                end = (start[0], 999)
            elif match.group(2):
                end = number_tuple(match.group(2))
            else:
                end = None
            ranges.append((start, end))

        headings = []
        for path in sorted(MANUAL.glob("*.md")):
            for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
                match = re.match(r"^#{2,6}\s+((?:\d+|[ABC])(?:\.\d+)+)(?:\s|$)", line)
                if match:
                    headings.append((match.group(1), path.name, line_number))
        self.assertGreater(len(headings), 400)
        missing = [item for item in headings if not covered(item[0], ranges)]
        self.assertEqual(missing, [], f"Uncovered manual headings: {missing[:25]}")


if __name__ == "__main__":
    unittest.main()
