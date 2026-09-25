"""Functional tests for metadata-driven tool forms."""

import unittest
from pathlib import Path
from typing import Mapping

from textual.widgets import Button, Input, Static

from retro_audit.contracts import ActivityReporter, ApplicationServices, CheckResult, ToolField
from retro_audit.registry import ToolRegistry
from retro_audit.tools import PasswordStrengthAuditService
from retro_audit.ui import AuditResultWindow, RetroAuditApp, SplashConfig, ToolOptionsWindow


class SecretFormTool:
    tool_id = "secret-form"
    display_name = "Formulario secreto"
    shortcut = "F11"
    requires_target = False
    requires_authorization = False
    input_fields = (ToolField("secret", "Secreto", secret=True),)

    def __init__(self) -> None:
        self.received_secret = ""

    def execute(
        self,
        _target: str | None,
        _report: ActivityReporter | None = None,
        options: Mapping[str, str] | None = None,
    ) -> CheckResult:
        self.received_secret = (options or {}).get("secret", "")
        return CheckResult("OK", "Secreto procesado sin mostrarlo.")


class FakeReportWriter:
    def save(self, _content: str) -> Path:
        return Path("fake-report.txt")


class ToolOptionsUiTests(unittest.IsolatedAsyncioTestCase):
    async def test_offline_tool_opens_masked_form_without_target_or_authorization(self) -> None:
        tool = SecretFormTool()
        app = RetroAuditApp(
            ApplicationServices(ToolRegistry((tool,)), FakeReportWriter()),
            splash_config=SplashConfig.disabled(),
        )

        async with app.run_test(size=(120, 40)) as pilot:
            await pilot.press("f11")
            await pilot.pause()
            self.assertIsInstance(app.screen, ToolOptionsWindow)
            secret_input = app.screen.query_one("#tool_field_secret", Input)
            self.assertTrue(secret_input.password)
            self.assertEqual(str(app.screen.query_one("#options_submit", Button).label), "EJECUTAR")
            self.assertEqual(str(app.screen.query_one("#options_cancel", Button).label), "CANCELAR")
            self.assertLess(app.screen.query_one("#options_window").size.height, 25)
            secret_input.value = "never-render-this"
            await pilot.click("#options_submit")
            await pilot.pause()

            self.assertEqual(tool.received_secret, "never-render-this")
            self.assertNotIn("never-render-this", app.latest_result)
            self.assertIn("[OK]", app.latest_result)
            self.assertIsInstance(app.screen, AuditResultWindow)

    async def test_password_tool_displays_result_after_click(self) -> None:
        tool = PasswordStrengthAuditService()
        app = RetroAuditApp(
            ApplicationServices(ToolRegistry((tool,)), FakeReportWriter()),
            splash_config=SplashConfig.disabled(),
        )

        async with app.run_test(size=(120, 40)) as pilot:
            await pilot.press("f6")
            await pilot.pause()
            contextual_help = str(app.screen.query_one("#options_help", Static).render())
            self.assertIn("QUÉ HACE:", contextual_help)
            self.assertIn("CÓMO USAR:", contextual_help)
            self.assertIn("sin contactar ningún servidor", contextual_help)
            app.screen.query_one("#tool_field_password", Input).value = "Usable!Passphrase2026"
            await pilot.click("#options_submit")
            await pilot.pause()

            self.assertIsInstance(app.screen, AuditResultWindow)
            result_body = str(app.screen.query_one("#audit_result_body", Static).render())
            self.assertIn("Clasificación:", result_body)
            self.assertIn("Entropía teórica estimada:", result_body)
            self.assertIn("[AUDITORÍA OFFLINE COMPLETADA]", app.latest_result)
            self.assertIn("Clasificación:", app.latest_result)
            self.assertIn("Entropía teórica estimada:", app.latest_result)
            await pilot.click("#audit_result_close")
            await pilot.pause()

            self.assertNotIsInstance(app.screen, AuditResultWindow)
            self.assertIn("[AUDITORÍA OFFLINE COMPLETADA]", str(app.query_one("#result", Static).render()))

    async def test_password_tool_displays_result_when_opened_from_audit_menu(self) -> None:
        tool = PasswordStrengthAuditService()
        app = RetroAuditApp(
            ApplicationServices(ToolRegistry((tool,)), FakeReportWriter()),
            splash_config=SplashConfig.disabled(),
        )

        async with app.run_test(size=(100, 40)) as pilot:
            await pilot.click("#menu_audit")
            await pilot.pause()
            await pilot.click("#menu_tool_password-strength")
            await pilot.pause()
            self.assertIsInstance(app.screen, ToolOptionsWindow)

            app.screen.query_one("#tool_field_password", Input).value = "Menu!Passphrase2026"
            await pilot.click("#options_submit")
            await pilot.pause()

            self.assertIsInstance(app.screen, AuditResultWindow)
            self.assertIn("[AUDITORÍA OFFLINE COMPLETADA]", app.latest_result)


if __name__ == "__main__":
    unittest.main()
