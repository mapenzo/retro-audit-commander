"""UI dependency and authorization lifecycle tests."""

import unittest
from pathlib import Path

from retro_audit.contracts import ActivityReporter, ApplicationServices, CheckResult
from retro_audit.registry import ToolRegistry
from retro_audit.ui import CommanderMenu, RetroAuditApp, SplashConfig


class FakeTool:
    tool_id = "fake"
    display_name = "Auditoría simulada"
    shortcut = "F9"

    def execute(self, target: str, _report: ActivityReporter | None = None) -> CheckResult:
        return CheckResult("OK", target)


class FakeReportWriter:
    def save(self, _content: str) -> Path:
        return Path("fake-report.txt")


class UiArchitectureTests(unittest.IsolatedAsyncioTestCase):
    async def test_registered_tool_appears_without_ui_code_changes(self) -> None:
        services = ApplicationServices(ToolRegistry((FakeTool(),)), FakeReportWriter())
        app = RetroAuditApp(services, splash_config=SplashConfig.disabled())
        async with app.run_test(size=(120, 40)) as pilot:
            await pilot.pause()
            self.assertIn("F9  Auditoría simulada", app.command_catalog)
            await pilot.click("#menu_audit")
            await pilot.pause()
            self.assertIsInstance(app.screen, CommanderMenu)
            self.assertIsNotNone(app.screen.query_one("#menu_tool_fake"))

    async def test_editing_target_revokes_authorization(self) -> None:
        services = ApplicationServices(ToolRegistry((FakeTool(),)), FakeReportWriter())
        app = RetroAuditApp(services, splash_config=SplashConfig.disabled())
        async with app.run_test(size=(120, 40)) as pilot:
            target = app.query_one("#target")
            authorization = app.query_one("#authorized")
            target.value = "first.example"
            await pilot.pause()
            await pilot.click("#authorized")
            self.assertTrue(authorization.value)
            self.assertEqual(app.authorized_target, "first.example")
            target.value = "second.example"
            await pilot.pause()
            self.assertFalse(authorization.value)
            self.assertIsNone(app.authorized_target)

    async def test_registered_shortcut_executes_generic_worker(self) -> None:
        services = ApplicationServices(ToolRegistry((FakeTool(),)), FakeReportWriter())
        app = RetroAuditApp(services, splash_config=SplashConfig.disabled())
        async with app.run_test(size=(120, 40)) as pilot:
            app.query_one("#target").value = "example.test"
            await pilot.pause()
            await pilot.click("#authorized")
            await pilot.press("f9")
            await pilot.pause()
            self.assertIn("[OK]", app.latest_result)
            self.assertIn("example.test", app.latest_result)


if __name__ == "__main__":
    unittest.main()
