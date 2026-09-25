"""Build a local, platform-specific Retro Audit distribution."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import hashlib
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
from typing import Sequence


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUTPUT = PROJECT_ROOT / "release"
SPEC_FILE = PROJECT_ROOT / "packaging" / "retro_audit.spec"


@dataclass(frozen=True)
class PlatformInfo:
    """Normalized platform details used in artifact names and paths."""

    operating_system: str
    architecture: str

    @property
    def identifier(self) -> str:
        return f"{self.operating_system}-{self.architecture}"


def detect_platform(system: str | None = None, machine: str | None = None) -> PlatformInfo:
    """Return a supported, normalized platform identifier."""
    system_name = (system or platform.system()).lower()
    machine_name = (machine or platform.machine()).lower()
    operating_systems = {"linux": "linux", "darwin": "macos", "windows": "windows"}
    architectures = {
        "amd64": "x64",
        "x86_64": "x64",
        "aarch64": "arm64",
        "arm64": "arm64",
    }
    try:
        normalized_os = operating_systems[system_name]
        normalized_architecture = architectures[machine_name]
    except KeyError as error:
        raise ValueError(f"Plataforma no soportada: {system_name}/{machine_name}") from error
    return PlatformInfo(normalized_os, normalized_architecture)


class LocalBuild:
    """Orchestrate the reproducible local build using the current uv project."""

    def __init__(
        self,
        platform_info: PlatformInfo,
        output_directory: Path = DEFAULT_OUTPUT,
        *,
        clean: bool = False,
        skip_tests: bool = False,
        verbose: bool = False,
    ) -> None:
        self.platform_info = platform_info
        self.output_directory = output_directory.resolve()
        self.clean = clean
        self.skip_tests = skip_tests
        self.verbose = verbose
        self.artifact_name = f"retro-audit-{platform_info.identifier}"
        self.build_root = PROJECT_ROOT / "build" / "local" / platform_info.identifier
        self.dist_directory = self.build_root / "dist"

    def run(self) -> Path:
        """Run all build stages and return the generated archive."""
        if self.clean:
            self._remove(self.build_root)
            self._remove(self.output_directory / self.artifact_name)
        self.output_directory.mkdir(parents=True, exist_ok=True)
        self._run_uv("sync", "--locked", "--group", "dev")
        if not self.skip_tests:
            self._run_uv("run", "pytest", "-q")
        self._run_uv("build", "--wheel", "--out-dir", str(self.build_root / "wheels"))
        self._run_uv(
            "run",
            "pyinstaller",
            "--noconfirm",
            "--clean",
            "--distpath",
            str(self.dist_directory),
            "--workpath",
            str(self.build_root / "work"),
            SPEC_FILE.name,
            cwd=SPEC_FILE.parent,
        )
        packaged_directory = self.dist_directory / "retro-audit"
        self._run_uv(
            "run",
            "python",
            str(PROJECT_ROOT / "scripts" / "smoke_test_artifact.py"),
            str(packaged_directory),
        )
        sbom = self.output_directory / f"{self.artifact_name}.cdx.json"
        self._run_uv(
            "run",
            "cyclonedx-py",
            "environment",
            "--of",
            "JSON",
            "--output-reproducible",
            "-o",
            str(sbom),
        )
        archive = self._archive(packaged_directory)
        self.write_checksum(archive)
        self.write_checksum(sbom)
        print(f"Artefacto: {archive}")
        print(f"SBOM:      {sbom}")
        print(f"SHA-256:   {self._sha256(archive)}")
        return archive

    def _run_uv(self, *arguments: str, cwd: Path = PROJECT_ROOT) -> None:
        command = ["uv", *arguments]
        print(f"+ {' '.join(command)}")
        subprocess.run(command, cwd=cwd, check=True)

    def _archive(self, packaged_directory: Path) -> Path:
        archive_base = self.output_directory / self.artifact_name
        extension = ".zip" if self.platform_info.operating_system == "windows" else ".tar.gz"
        archive = archive_base.with_suffix(extension)
        self._remove(archive)
        if extension == ".zip":
            shutil.make_archive(str(archive_base), "zip", packaged_directory.parent, packaged_directory.name)
        else:
            shutil.make_archive(str(archive_base), "gztar", packaged_directory.parent, packaged_directory.name)
        return archive

    def write_checksum(self, file_path: Path) -> None:
        checksum_path = file_path.with_name(f"{file_path.name}.sha256")
        checksum_path.write_text(f"{self._sha256(file_path)}  {file_path.name}\n", encoding="utf-8")

    @staticmethod
    def _sha256(file_path: Path) -> str:
        digest = hashlib.sha256()
        with file_path.open("rb") as stream:
            for block in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(block)
        return digest.hexdigest()

    @staticmethod
    def _remove(path: Path) -> None:
        if path.is_dir() and not path.is_symlink():
            shutil.rmtree(path)
        elif path.exists() or path.is_symlink():
            path.unlink()


def build_parser() -> argparse.ArgumentParser:
    """Create the command-line parser for local builds."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--clean", action="store_true", help="Eliminar el build local anterior.")
    parser.add_argument("--skip-tests", action="store_true", help="Omitir pytest conscientemente.")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT, help="Directorio de salida.")
    parser.add_argument("--verbose", action="store_true", help="Conservar para compatibilidad futura.")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Parse options and execute the local build."""
    arguments = build_parser().parse_args(argv)
    if arguments.verbose:
        os.environ["PYTHONUNBUFFERED"] = "1"
    try:
        LocalBuild(
            detect_platform(),
            arguments.output,
            clean=arguments.clean,
            skip_tests=arguments.skip_tests,
            verbose=arguments.verbose,
        ).run()
    except (OSError, subprocess.CalledProcessError, ValueError) as error:
        print(f"Error de compilación local: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())