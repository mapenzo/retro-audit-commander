"""Tests for registry extensibility and secure report persistence."""

import stat
import tempfile
import unittest
from pathlib import Path

from retro_audit.contracts import ActivityReporter, CheckResult
from retro_audit.registry import ToolRegistry
from retro_audit.reporting import ReportService


class FakeTool:
    tool_id = "fake"
    display_name = "Herramienta falsa"
    shortcut = "F9"

    def execute(self, target: str, report: ActivityReporter | None = None) -> CheckResult:
        if report:
            report(target)
        return CheckResult("OK", target)


class RegistryTests(unittest.TestCase):
    def test_tool_can_be_added_without_ui_changes(self) -> None:
        registry = ToolRegistry((FakeTool(),))
        tool = registry.get("fake")
        self.assertIsNotNone(tool)
        self.assertEqual(tool.execute("example.test").title, "OK")  # type: ignore[union-attr]

    def test_duplicate_tool_ids_are_rejected(self) -> None:
        with self.assertRaises(ValueError):
            ToolRegistry((FakeTool(), FakeTool()))


class ReportServiceTests(unittest.TestCase):
    def test_reports_are_unique_and_private(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            service = ReportService(Path(directory) / "reports")
            first = service.save("one")
            second = service.save("two")
            self.assertNotEqual(first, second)
            self.assertEqual(stat.S_IMODE(first.stat().st_mode), 0o600)

    def test_symlinked_report_directory_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            real_directory = root / "real"
            real_directory.mkdir()
            link = root / "reports"
            link.symlink_to(real_directory, target_is_directory=True)
            with self.assertRaises(OSError):
                ReportService(link).save("sensitive")


if __name__ == "__main__":
    unittest.main()
