"""Tests for complete, discoverable operating guidance."""

import unittest
from pathlib import Path

from textual.widgets import Static

from retro_audit.contracts import ApplicationServices
from retro_audit.factory import AuditServiceFactory
from retro_audit.ui import CommanderInfoWindow, RetroAuditApp, SplashConfig


class FakeReportWriter:
    def save(self, _content: str) -> Path:
        return Path("fake-report.txt")


class ToolGuidanceTests(unittest.TestCase):
    def test_every_registered_tool_has_complete_guidance(self) -> None:
        tools = AuditServiceFactory.create_tool_registry().all()

        self.assertEqual(len(tools), 9)
        for tool in tools:
            with self.subTest(tool=tool.tool_id):
                self.assertTrue(tool.guide.purpose.strip())
                self.assertGreaterEqual(len(tool.guide.steps), 3)
                self.assertTrue(all(step.strip() for step in tool.guide.steps))
                self.assertTrue(tool.guide.output.strip())
                self.assertTrue(tool.guide.safety.strip())


class ToolGuidanceUiTests(unittest.IsolatedAsyncioTestCase):
    async def test_help_window_explains_every_registered_tool(self) -> None:
        registry = AuditServiceFactory.create_tool_registry()
        app = RetroAuditApp(
            ApplicationServices(registry, FakeReportWriter()),
            splash_config=SplashConfig.disabled(),
        )

        async with app.run_test(size=(120, 42)) as pilot:
            await pilot.click("#menu_help")
            await pilot.pause()
            await pilot.click("#menu_help_guide")
            await pilot.pause()

            self.assertIsInstance(app.screen, CommanderInfoWindow)
            guide_text = str(app.screen.query_one("#info_body", Static).render())
            self.assertIn("INICIO RÁPIDO", guide_text)
            self.assertIn("QUÉ HACE:", guide_text)
            self.assertIn("CÓMO USAR:", guide_text)
            self.assertIn("RESULTADO:", guide_text)
            self.assertIn("SEGURIDAD:", guide_text)
            for tool in registry.all():
                self.assertIn(tool.display_name.upper(), guide_text)


if __name__ == "__main__":
    unittest.main()