"""Executable entry point for Retro Audit."""

from retro_audit import AuditServiceFactory, RetroAuditApp


def main() -> None:
    """Create and run the terminal application."""
    RetroAuditApp(AuditServiceFactory.create_services()).run()


if __name__ == "__main__":
    main()
