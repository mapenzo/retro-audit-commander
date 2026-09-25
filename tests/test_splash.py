"""Startup splash lifecycle, accessibility, and replay tests."""

from __future__ import annotations

import os
import unittest
from pathlib import Path
from unittest.mock import patch

from textual.widgets import Static

from retro_audit.contracts import ActivityReporter, ApplicationServices, CheckResult
from retro_audit.registry import ToolRegistry
from retro_audit.ui import CommanderMenu, RetroAuditApp, RetroSplashScreen, SplashConfig, UiScreenFactory


class FakeReportWriter:
    def save(self, _content: str) -> Path:
        return Path("fake-report.txt")


class RecordingTool:
    tool_id = "recording"
    display_name = "Herramienta de control"
    shortcut = "F9"
    requires_target = False
    requires_authorization = False
    input_fields = ()

    def __init__(self) -> None:
        self.executions = 0

    def execute(
        self,
        _target: str | None,
        _report: ActivityReporter | None = None,
        _options: dict[str, str] | None = None,
    ) -> CheckResult:
        self.executions += 1
        return CheckResult("OK", "executed")


def create_app(config: SplashConfig) -> RetroAuditApp:
    services = ApplicationServices(ToolRegistry(()), FakeReportWriter())
    return RetroAuditApp(services, splash_config=config)


class SplashConfigTests(unittest.TestCase):
    def test_environment_can_disable_splash_and_reduce_motion(self) -> None:
        with patch.dict(
            os.environ,
            {"RETRO_AUDIT_SKIP_SPLASH": "1", "RETRO_AUDIT_REDUCED_MOTION": "true"},
            clear=False,
        ):
            config = SplashConfig.from_environment("1.2.3")

        self.assertFalse(config.enabled)
        self.assertTrue(config.reduced_motion)
        self.assertEqual(config.application_version, "1.2.3")

    def test_factory_reads_project_version(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            config = UiScreenFactory.create_splash_config()

        self.assertEqual(config.application_version, "0.1.0")

    def test_invalid_timing_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            SplashConfig(duration_seconds=0)
        with self.assertRaises(ValueError):
            SplashConfig(frame_interval_seconds=0)


class SplashUiTests(unittest.IsolatedAsyncioTestCase):
    async def test_splash_animates_and_displays_version(self) -> None:
        app = create_app(SplashConfig(duration_seconds=1.0, frame_interval_seconds=0.01, application_version="9.8.7"))

        async with app.run_test(size=(80, 30)) as pilot:
            await pilot.pause(0.06)

            self.assertIsInstance(app.screen, RetroSplashScreen)
            self.assertGreater(app.screen.frame_index, 0)
            version_text = str(app.screen.query_one("#splash_version", Static).render())
            self.assertIn("v9.8.7", version_text)

    async def test_any_key_skips_splash(self) -> None:
        app = create_app(SplashConfig(duration_seconds=1.0))

        async with app.run_test(size=(80, 30)) as pilot:
            await pilot.pause()
            self.assertIsInstance(app.screen, RetroSplashScreen)
            await pilot.press("x")
            await pilot.pause()

            self.assertNotIsInstance(app.screen, RetroSplashScreen)

    async def test_tool_shortcut_only_skips_splash(self) -> None:
        tool = RecordingTool()
        services = ApplicationServices(ToolRegistry((tool,)), FakeReportWriter())
        app = RetroAuditApp(services, splash_config=SplashConfig(duration_seconds=1.0))

        async with app.run_test(size=(80, 30)) as pilot:
            await pilot.pause()
            self.assertIsInstance(app.screen, RetroSplashScreen)
            await pilot.press("f9")
            await pilot.pause()

            self.assertNotIsInstance(app.screen, RetroSplashScreen)
            self.assertEqual(tool.executions, 0)

    async def test_click_skips_splash(self) -> None:
        app = create_app(SplashConfig(duration_seconds=1.0))

        async with app.run_test(size=(80, 30)) as pilot:
            await pilot.pause()
            await pilot.click("#splash_window")
            await pilot.pause()

            self.assertNotIsInstance(app.screen, RetroSplashScreen)

    async def test_splash_closes_automatically(self) -> None:
        app = create_app(SplashConfig(duration_seconds=0.05, frame_interval_seconds=0.01))

        async with app.run_test(size=(80, 30)) as pilot:
            await pilot.pause(0.12)

            self.assertNotIsInstance(app.screen, RetroSplashScreen)

    async def test_reduced_motion_is_static_and_brief(self) -> None:
        app = create_app(
            SplashConfig(duration_seconds=2.5, frame_interval_seconds=0.01, reduced_motion=True)
        )

        async with app.run_test(size=(80, 30)) as pilot:
            await pilot.pause(0.05)

            self.assertIsInstance(app.screen, RetroSplashScreen)
            self.assertEqual(app.screen.frame_index, 0)
            progress = str(app.screen.query_one("#splash_progress", Static).render())
            self.assertIn("100%", progress)

    async def test_disabled_splash_can_be_replayed_from_help(self) -> None:
        app = create_app(SplashConfig.disabled())

        async with app.run_test(size=(80, 30)) as pilot:
            await pilot.pause()
            self.assertNotIsInstance(app.screen, RetroSplashScreen)
            await pilot.click("#menu_help")
            await pilot.pause()
            self.assertIsInstance(app.screen, CommanderMenu)
            await pilot.click("#menu_help_splash")
            await pilot.pause()

            self.assertIsInstance(app.screen, RetroSplashScreen)

    async def test_splash_fits_narrow_terminal(self) -> None:
        app = create_app(SplashConfig(duration_seconds=1.0))

        async with app.run_test(size=(50, 20)) as pilot:
            await pilot.pause()
            splash_window = app.screen.query_one("#splash_window")

            self.assertLessEqual(splash_window.size.width, 50)
            self.assertLessEqual(splash_window.size.height, 20)


if __name__ == "__main__":
    unittest.main()
