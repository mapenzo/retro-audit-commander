"""Console entry point behavior tests."""

from __future__ import annotations

from contextlib import redirect_stdout
from io import StringIO
import unittest
from unittest.mock import MagicMock, patch

from retro_audit.__main__ import main


class ConsoleEntrypointTests(unittest.TestCase):
    def test_starts_application_with_factory_services(self) -> None:
        services = MagicMock()
        application = MagicMock()
        with (
            patch("retro_audit.__main__.AuditServiceFactory.create_services", return_value=services),
            patch("retro_audit.__main__.RetroAuditApp", return_value=application) as app_type,
        ):
            main([])

        app_type.assert_called_once_with(services)
        application.run.assert_called_once_with()

    def test_version_option_exits_without_starting_application(self) -> None:
        output = StringIO()
        with (
            patch("retro_audit.__main__.ApplicationMetadataFactory.application_version", return_value="9.8.7"),
            patch("retro_audit.__main__.RetroAuditApp") as app_type,
            redirect_stdout(output),
            self.assertRaises(SystemExit) as exit_error,
        ):
            main(["--version"])

        self.assertEqual(exit_error.exception.code, 0)
        self.assertEqual(output.getvalue(), "retro-audit 9.8.7\n")
        app_type.assert_not_called()