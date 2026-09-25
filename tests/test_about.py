"""Project metadata and About-window behavior tests."""

from __future__ import annotations

from importlib.metadata import version
from pathlib import Path
import unittest

from textual.widgets import Static

from retro_audit.contracts import ApplicationServices
from retro_audit.metadata import (
    APPLICATION_CONTACT,
    APPLICATION_COPYRIGHT,
    APPLICATION_REPOSITORY,
    AboutInfo,
    ApplicationMetadataFactory,
)
from retro_audit.registry import ToolRegistry
from retro_audit.ui import AboutWindow, CommanderMenu, RetroAuditApp, SplashConfig, UiScreenFactory


class FakeReportWriter:
    def save(self, _content: str) -> Path:
        return Path("fake-report.txt")


def create_app(info: AboutInfo) -> RetroAuditApp:
    services = ApplicationServices(ToolRegistry(()), FakeReportWriter())
    return RetroAuditApp(services, splash_config=SplashConfig.disabled(), about_info=info)


class ApplicationMetadataTests(unittest.TestCase):
    def test_factory_uses_canonical_project_and_runtime_metadata(self) -> None:
        info = ApplicationMetadataFactory.create_about_info()

        self.assertEqual(info.version, "0.1.0")
        self.assertEqual(info.copyright_notice, APPLICATION_COPYRIGHT)
        self.assertEqual(info.repository_url, APPLICATION_REPOSITORY)
        self.assertEqual(info.contact_url, APPLICATION_CONTACT)
        self.assertEqual(info.textual_version, version("textual"))
        self.assertEqual(info.paramiko_version, version("paramiko"))
        self.assertEqual(info.version, UiScreenFactory.create_splash_config().application_version)

    def test_ui_factory_injects_immutable_metadata(self) -> None:
        info = ApplicationMetadataFactory.create_about_info()

        screen = UiScreenFactory.create_about(info)

        self.assertIs(screen.info, info)
        with self.assertRaises((AttributeError, TypeError)):
            info.name = "changed"  # type: ignore[misc]


class AboutWindowTests(unittest.IsolatedAsyncioTestCase):
    async def test_help_menu_opens_detailed_about_and_escape_closes_it(self) -> None:
        info = ApplicationMetadataFactory.create_about_info()
        app = create_app(info)

        async with app.run_test(size=(100, 34)) as pilot:
            await pilot.click("#menu_help")
            await pilot.pause()

            self.assertIsInstance(app.screen, CommanderMenu)
            self.assertIsNotNone(app.screen.query_one("#menu_help_guide"))
            self.assertIsNotNone(app.screen.query_one("#menu_help_splash"))
            self.assertIsNotNone(app.screen.query_one("#menu_help_about"))

            await pilot.click("#menu_help_about")
            await pilot.pause()

            self.assertIsInstance(app.screen, AboutWindow)
            content = str(app.screen.query_one("#about_body", Static).render())
            for expected in (
                info.name,
                info.version,
                info.purpose,
                info.author,
                info.copyright_notice,
                info.license_name,
                info.authorized_use_notice,
                info.python_version,
                info.textual_version,
                info.paramiko_version,
                info.repository_url,
                info.contact_url,
            ):
                with self.subTest(expected=expected):
                    self.assertIn(expected, content)

            await pilot.press("escape")
            await pilot.pause()
            self.assertNotIsInstance(app.screen, AboutWindow)

    async def test_about_window_fits_narrow_terminal(self) -> None:
        app = create_app(ApplicationMetadataFactory.create_about_info())

        async with app.run_test(size=(50, 20)) as pilot:
            app.push_screen(UiScreenFactory.create_about(app.about_info))
            await pilot.pause()
            about_window = app.screen.query_one("#about_window")

            self.assertLessEqual(about_window.size.width, 50)
            self.assertLessEqual(about_window.size.height, 20)


if __name__ == "__main__":
    unittest.main()
