"""Single source of truth for application identity and runtime metadata."""

from __future__ import annotations

from dataclasses import dataclass
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
import platform
import tomllib

APPLICATION_NAME = "Retro Audit Commander"
APPLICATION_PURPOSE = "Interfaz TUI retro para comprobaciones de seguridad autorizadas, defensivas y de bajo impacto."
APPLICATION_AUTHOR = "Miguel Poveda (mapenzo)"
APPLICATION_COPYRIGHT = "Copyright (c) 2026 Miguel Ángel Poveda Lorenzo"
APPLICATION_LICENSE = "MIT License"
APPLICATION_REPOSITORY = "https://github.com/mapenzo/retro-audit-commander"
APPLICATION_CONTACT = "https://github.com/mapenzo"
AUTHORIZED_USE_NOTICE = (
    "Uso exclusivo en sistemas propios o dentro de un alcance expresamente autorizado. "
    "La aplicación no sustituye una evaluación profesional ni autoriza pruebas sobre terceros."
)


@dataclass(frozen=True)
class AboutInfo:
    """Immutable content rendered by the About window."""

    name: str
    version: str
    purpose: str
    author: str
    copyright_notice: str
    license_name: str
    authorized_use_notice: str
    python_version: str
    textual_version: str
    paramiko_version: str
    repository_url: str
    contact_url: str


class ApplicationMetadataFactory:
    """Build application metadata from project and runtime sources."""

    @classmethod
    def create_about_info(cls) -> AboutInfo:
        return AboutInfo(
            name=APPLICATION_NAME,
            version=cls.application_version(),
            purpose=APPLICATION_PURPOSE,
            author=APPLICATION_AUTHOR,
            copyright_notice=APPLICATION_COPYRIGHT,
            license_name=APPLICATION_LICENSE,
            authorized_use_notice=AUTHORIZED_USE_NOTICE,
            python_version=platform.python_version(),
            textual_version=cls._dependency_version("textual"),
            paramiko_version=cls._dependency_version("paramiko"),
            repository_url=APPLICATION_REPOSITORY,
            contact_url=APPLICATION_CONTACT,
        )

    @staticmethod
    def application_version() -> str:
        try:
            return version("hacking")
        except PackageNotFoundError:
            project_file = Path(__file__).parents[1] / "pyproject.toml"
            try:
                with project_file.open("rb") as stream:
                    return str(tomllib.load(stream)["project"]["version"])
            except (OSError, KeyError, TypeError, tomllib.TOMLDecodeError):
                return "dev"

    @staticmethod
    def _dependency_version(distribution: str) -> str:
        try:
            return version(distribution)
        except PackageNotFoundError:
            return "no disponible"
