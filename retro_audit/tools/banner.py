"""Bounded, protocol-aware service banner collection."""

from __future__ import annotations

import re
import socket
import ssl
from dataclasses import dataclass
from typing import Mapping

from retro_audit.contracts import ActivityReporter, CheckResult, ToolGuide, resolve_reporter
from retro_audit.targets import TargetParser, TargetValidationError

MAX_BANNER_BYTES = 1024
MAX_BANNER_CHARACTERS = 240
DEFAULT_TIMEOUT_SECONDS = 0.8


@dataclass(frozen=True)
class BannerProbe:
    """A bounded protocol probe for one well-known TCP service."""

    port: int
    service: str
    payload: bytes | None = None
    use_tls: bool = False


DEFAULT_BANNER_PROBES = (
    BannerProbe(21, "FTP"),
    BannerProbe(22, "SSH"),
    BannerProbe(25, "SMTP"),
    BannerProbe(80, "HTTP", b"HEAD / HTTP/1.0\r\nConnection: close\r\n\r\n"),
    BannerProbe(110, "POP3"),
    BannerProbe(143, "IMAP"),
    BannerProbe(443, "HTTPS", b"HEAD / HTTP/1.0\r\nConnection: close\r\n\r\n", use_tls=True),
    BannerProbe(3306, "MySQL"),
    BannerProbe(8080, "HTTP-ALT", b"HEAD / HTTP/1.0\r\nConnection: close\r\n\r\n"),
)


class BannerGrabService:
    """Collect short service greetings without authentication or exploitation."""

    tool_id = "banner"
    display_name = "Banner Grabbing"
    shortcut = "F4"
    guide = ToolGuide(
        purpose="Recoge saludos breves de servicios comunes para identificar software expuesto.",
        steps=(
            "Introduce un host, una IP o una URL perteneciente al alcance autorizado.",
            "Marca Autorización confirmada.",
            "Ejecuta y revisa únicamente los servicios que hayan devuelto un banner.",
        ),
        output="Lista puerto, servicio esperado y hasta 240 caracteres sanitizados de cada respuesta.",
        safety="Consulta perfiles fijos, lee como máximo 1 KiB y no intenta autenticarse ni explotar servicios.",
    )
    requires_target = True
    requires_authorization = True
    input_fields = ()

    def __init__(
        self,
        probes: tuple[BannerProbe, ...] = DEFAULT_BANNER_PROBES,
        timeout: float = DEFAULT_TIMEOUT_SECONDS,
        max_bytes: int = MAX_BANNER_BYTES,
    ) -> None:
        if timeout <= 0 or max_bytes <= 0:
            raise ValueError("Los límites de banner deben ser positivos.")
        if not probes:
            raise ValueError("Se requiere al menos un perfil de banner.")
        self.probes = probes
        self.timeout = timeout
        self.max_bytes = min(max_bytes, MAX_BANNER_BYTES)

    def execute(
        self,
        target: str | None,
        report: ActivityReporter | None = None,
        _options: Mapping[str, str] | None = None,
    ) -> CheckResult:
        reporter = resolve_reporter(report)
        if target is None:
            return CheckResult("OBJETIVO NO VÁLIDO", "Esta herramienta requiere un objetivo.")
        try:
            hostname = self._parse_hostname(target)
        except TargetValidationError as error:
            reporter(f"! Objetivo no válido: {error}")
            return CheckResult("OBJETIVO NO VÁLIDO", str(error))

        reporter(f"> Resolviendo objetivo para Banner Grabbing: {hostname}")
        findings: list[tuple[BannerProbe, str]] = []
        for index, probe in enumerate(self.probes, start=1):
            reporter(f"> [{index:02}/{len(self.probes):02}] Consultando {probe.service} en TCP/{probe.port}...")
            banner = self._collect(hostname, probe)
            if banner is None:
                continue
            findings.append((probe, banner))
            reporter(f"+ TCP/{probe.port} respondió: {banner}")

        rows = [f"OBJETIVO : {hostname}", "", "PUERTO  SERVICIO    BANNER"]
        if findings:
            rows.extend(f"{probe.port:<7} {probe.service:<11} {banner}" for probe, banner in findings)
        else:
            rows.append("Sin banners disponibles en los puertos examinados.")
        rows.extend(("", f"Banners obtenidos: {len(findings)} de {len(self.probes)} perfiles"))
        reporter("+ Banner Grabbing finalizado.")
        return CheckResult("BANNER GRABBING COMPLETADO", "\n".join(rows))

    @staticmethod
    def _parse_hostname(target: str) -> str:
        if "://" in target:
            return TargetParser.parse_web(target).hostname
        return TargetParser.parse_host(target)

    def _collect(self, hostname: str, probe: BannerProbe) -> str | None:
        try:
            with socket.create_connection((hostname, probe.port), timeout=self.timeout) as connection:
                connection.settimeout(self.timeout)
                stream: socket.socket | ssl.SSLSocket = connection
                if probe.use_tls:
                    context = ssl.create_default_context()
                    stream = context.wrap_socket(connection, server_hostname=hostname)
                if probe.payload:
                    stream.sendall(probe.payload)
                response = stream.recv(self.max_bytes)
                if probe.use_tls:
                    stream.close()
        except (OSError, TimeoutError, ssl.SSLError):
            return None
        return self._sanitize(response)

    @staticmethod
    def _sanitize(response: bytes) -> str:
        """Render untrusted network bytes safely in a terminal."""
        decoded = response.decode("utf-8", errors="replace")
        printable = "".join(character if character.isprintable() else " " for character in decoded)
        compact = re.sub(r"\s+", " ", printable).strip()
        return compact[:MAX_BANNER_CHARACTERS] or "conexión aceptada; banner vacío"
