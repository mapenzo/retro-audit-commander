"""Local text report persistence."""

from datetime import datetime, timezone
import os
from pathlib import Path
import secrets


class ReportService:
    """Persist audit output to timestamped UTF-8 text files."""

    def __init__(self, report_directory: Path | None = None) -> None:
        self.report_directory = report_directory or Path("reports")

    def save(self, content: str) -> Path:
        """Save content and return the generated report path."""
        if self.report_directory.is_symlink():
            raise OSError("El directorio de informes no puede ser un enlace simbólico.")
        self.report_directory.mkdir(mode=0o700, parents=True, exist_ok=True)
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
        report = self.report_directory / f"retro-audit-{timestamp}-{secrets.token_hex(4)}.txt"
        payload = f"RETRO AUDIT REPORT\nGenerado: {timestamp}\n\n{content}\n"
        descriptor = os.open(report, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(descriptor, "w", encoding="utf-8") as report_file:
            report_file.write(payload)
        return report
