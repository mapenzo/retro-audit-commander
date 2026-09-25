"""Tests for the local build orchestrator."""

from __future__ import annotations

from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts.build_local import LocalBuild, build_parser, detect_platform


class PlatformDetectionTests(unittest.TestCase):
    def test_normalizes_supported_platforms(self) -> None:
        self.assertEqual(detect_platform("Linux", "x86_64").identifier, "linux-x64")
        self.assertEqual(detect_platform("Darwin", "arm64").identifier, "macos-arm64")
        self.assertEqual(detect_platform("Windows", "AMD64").identifier, "windows-x64")

    def test_rejects_unknown_platforms(self) -> None:
        with self.assertRaises(ValueError):
            detect_platform("Plan9", "x86_64")
        with self.assertRaises(ValueError):
            detect_platform("Linux", "riscv64")


class LocalBuildTests(unittest.TestCase):
    def test_parser_exposes_safe_build_options(self) -> None:
        arguments = build_parser().parse_args(["--clean", "--skip-tests", "--output", "out", "--verbose"])

        self.assertTrue(arguments.clean)
        self.assertTrue(arguments.skip_tests)
        self.assertTrue(arguments.verbose)
        self.assertEqual(arguments.output, Path("out"))

    def test_checksum_sidecar_contains_sha256_and_filename(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            file_path = Path(directory) / "artifact.zip"
            file_path.write_bytes(b"retro-audit")
            builder = LocalBuild(detect_platform("Linux", "x86_64"), Path(directory))
            builder.write_checksum(file_path)

            checksum = file_path.with_name("artifact.zip.sha256").read_text(encoding="utf-8")

        self.assertEqual(
            checksum,
            "511788653087096bb19bb3240d68c6fc6758111d74ce398ccee8a70ec743b342  artifact.zip\n",
        )

    @patch("scripts.build_local.subprocess.run")
    def test_run_executes_tests_before_packaging(self, run: object) -> None:
        with tempfile.TemporaryDirectory() as directory:
            builder = LocalBuild(
                detect_platform("Linux", "x86_64"),
                Path(directory),
                skip_tests=True,
            )
            with (
                patch.object(builder, "_archive", return_value=Path(directory) / "artifact.tar.gz"),
                patch.object(builder, "write_checksum"),
                patch.object(builder, "_sha256", return_value="checksum"),
            ):
                archive = builder.run()

        self.assertEqual(archive.name, "artifact.tar.gz")
        commands = [call.args[0] for call in run.call_args_list]  # type: ignore[union-attr]
        self.assertEqual(commands[0][:4], ["uv", "sync", "--locked", "--group"])
        self.assertNotIn(["uv", "run", "pytest", "-q"], commands)


if __name__ == "__main__":
    unittest.main()