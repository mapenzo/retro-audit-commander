"""Console entry point for Retro Audit Commander."""

from __future__ import annotations

import argparse
from collections.abc import Sequence

from retro_audit.factory import AuditServiceFactory
from retro_audit.metadata import ApplicationMetadataFactory
from retro_audit.ui import RetroAuditApp


def main(argv: Sequence[str] | None = None) -> None:
    """Validate command-line options and start the terminal application."""
    parser = argparse.ArgumentParser(
        prog="retro-audit",
        description="TUI para comprobaciones de seguridad autorizadas y de bajo impacto.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {ApplicationMetadataFactory.application_version()}",
    )
    parser.parse_args(argv)
    RetroAuditApp(AuditServiceFactory.create_services()).run()


if __name__ == "__main__":
    main()