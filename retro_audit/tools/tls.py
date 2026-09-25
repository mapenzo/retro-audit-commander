"""TLS certificate and negotiated-parameter audit tool."""

import socket
import ssl
from typing import Mapping

from retro_audit.contracts import ActivityReporter, CheckResult, ToolGuide, resolve_reporter
from retro_audit.targets import TargetParser, TargetValidationError


class TlsAuditService:
    """Inspect the certificate and negotiated TLS parameters of an HTTPS endpoint."""

    tool_id = "tls"
    display_name = "Auditar TLS"
    shortcut = "F3"
    guide = ToolGuide(
        purpose="Valida el certificado y muestra los parámetros negociados por un endpoint HTTPS.",
        steps=(
            "Introduce una URL https://; puedes incluir un puerto HTTPS no estándar.",
            "Confirma la autorización para el objetivo actual.",
            "Ejecuta y comprueba protocolo, cifrado, caducidad y validación del certificado.",
        ),
        output="Muestra host, versión TLS, cifrado, fecha de caducidad y presencia de emisor.",
        safety="Sólo realiza el handshake TLS y usa el almacén de confianza local; no omite errores de certificado.",
    )
    requires_target = True
    requires_authorization = True
    input_fields = ()

    def execute(
        self,
        target: str | None,
        report: ActivityReporter | None = None,
        _options: Mapping[str, str] | None = None,
    ) -> CheckResult:
        if target is None:
            return CheckResult("OBJETIVO NO VÁLIDO", "Esta herramienta requiere un objetivo.")
        return self.inspect(target, report)

    def inspect(self, target: str, report: ActivityReporter | None = None) -> CheckResult:
        reporter = resolve_reporter(report)
        try:
            validated = TargetParser.parse_web(target, require_https=True)
        except TargetValidationError as error:
            reporter(f"! Objetivo no válido: {error}")
            return CheckResult("OBJETIVO NO VÁLIDO", str(error))

        host = validated.hostname
        port = validated.port

        reporter(f"> Abriendo handshake TLS con {host}:{port}...")
        try:
            context = ssl.create_default_context()
            with socket.create_connection((host, port), timeout=8) as connection:
                with context.wrap_socket(connection, server_hostname=host) as secure_connection:
                    certificate = secure_connection.getpeercert()
                    cipher = secure_connection.cipher()
                    protocol = secure_connection.version() or "no disponible"
        except ssl.SSLCertVerificationError as error:
            reporter(f"! Certificado TLS no válido: {error.verify_message}")
            return CheckResult("RIESGO TLS", f"HOST     : {host}:{port}\nCERTIFICADO: no verificable\nDETALLE  : {error.verify_message}")
        except (OSError, ValueError, ssl.SSLError) as error:
            reporter(f"! No se pudo negociar TLS: {error}")
            return CheckResult("ERROR TLS", f"No se pudo comprobar TLS en {host}:{port}\n{error}")

        cipher_name = cipher[0] if cipher else "no disponible"
        rows = [
            f"HOST       : {host}:{port}",
            f"PROTOCOLO  : {protocol}",
            f"CIFRADO    : {cipher_name}",
            f"CADUCA     : {certificate.get('notAfter', 'no disponible')}",
            f"EMISOR     : {'presente' if certificate.get('issuer') else 'no disponible'}",
        ]
        reporter(f"+ TLS negociado: {protocol} / {cipher_name}")
        reporter("+ Certificado verificado por el almacén de confianza local.")
        return CheckResult("AUDITORÍA TLS COMPLETADA", "\n".join(rows))
