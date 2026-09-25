"""Shared contracts for audit tools and presentation layers."""

from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Mapping, Protocol

ActivityReporter = Callable[[str], None]


@dataclass(frozen=True)
class CheckResult:
    """The rendered result of a bounded, authorized security check."""

    title: str
    body: str


@dataclass(frozen=True)
class ToolField:
    """Presentation-neutral input requested by a configurable audit tool."""

    key: str
    label: str
    placeholder: str = ""
    default: str = ""
    secret: bool = False
    required: bool = True


@dataclass(frozen=True)
class ToolGuide:
    """User-facing operating instructions owned by an audit tool."""

    purpose: str
    steps: tuple[str, ...]
    output: str
    safety: str


class AuditTool(Protocol):
    """Capability implemented by every independently registered audit tool."""

    tool_id: str
    display_name: str
    shortcut: str
    guide: ToolGuide
    requires_target: bool
    requires_authorization: bool
    input_fields: tuple[ToolField, ...]

    def execute(
        self,
        target: str | None,
        report: ActivityReporter | None = None,
        options: Mapping[str, str] | None = None,
    ) -> CheckResult: ...


class ReportWriter(Protocol):
    """Persistence capability required by the presentation layer."""

    def save(self, content: str) -> Path: ...


class ToolProvider(Protocol):
    """Lookup capability required by audit orchestrators."""

    def get(self, tool_id: str) -> AuditTool | None: ...

    def all(self) -> tuple[AuditTool, ...]: ...


@dataclass(frozen=True)
class ApplicationServices:
    """Protocol-based dependencies consumed by the presentation layer."""

    tools: ToolProvider
    reports: ReportWriter


def resolve_reporter(reporter: ActivityReporter | None) -> ActivityReporter:
    """Return a reporter callback, defaulting to a no-op implementation."""
    return reporter or (lambda _message: None)
