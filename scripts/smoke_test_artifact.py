"""Verify a PyInstaller artifact can resolve its version without opening the TUI."""

from __future__ import annotations

import argparse
from pathlib import Path
import subprocess
import sys


def _executable_in(directory: Path) -> Path:
    name = "retro-audit.exe" if sys.platform == "win32" else "retro-audit"
    executable = directory / name
    if not executable.is_file():
        raise FileNotFoundError(f"No se encontró el ejecutable empaquetado: {executable}")
    return executable


def main() -> None:
    """Run the packaged executable's non-interactive version check."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("artifact_directory", type=Path)
    arguments = parser.parse_args()
    executable = _executable_in(arguments.artifact_directory)
    result = subprocess.run(
        [str(executable), "--version"],
        check=False,
        capture_output=True,
        encoding="utf-8",
        timeout=30,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr or "La comprobación del ejecutable falló sin detalles.")
    if not result.stdout.startswith("retro-audit "):
        raise RuntimeError(f"Salida de versión inesperada: {result.stdout!r}")


if __name__ == "__main__":
    main()