"""Passive HTTP response-header and cookie-policy audit tool."""

import ssl
from email.message import Message
from typing import Mapping
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin
from urllib.request import HTTPRedirectHandler, HTTPSHandler, Request, build_opener

from retro_audit.contracts import ActivityReporter, CheckResult, ToolGuide, resolve_reporter
from retro_audit.targets import TargetParser, TargetValidationError, WebTarget

SECURITY_HEADERS = (
    "Strict-Transport-Security",
    "Content-Security-Policy",
    "X-Frame-Options",
    "X-Content-Type-Options",
    "Referrer-Policy",
    "Permissions-Policy",
)


class RedirectScopeError(Exception):
    """Raised when a redirect attempts to leave the authorized origin."""


class SameOriginRedirectHandler(HTTPRedirectHandler):
    """Allow redirects only within the original host and port, without downgrade."""

    def __init__(self, origin: WebTarget) -> None:
        super().__init__()
        self.origin = origin

    def redirect_request(self, req, fp, code, msg, headers, newurl):  # type: ignore[no-untyped-def]
        destination_url = urljoin(req.full_url, newurl)
        try:
            destination = TargetParser.parse_web(destination_url)
        except TargetValidationError as error:
            raise RedirectScopeError(str(error)) from error
        same_origin = destination.hostname == self.origin.hostname and destination.port == self.origin.port
        downgrade = self.origin.scheme == "https" and destination.scheme != "https"
        if not same_origin or downgrade:
            raise RedirectScopeError(f"Redirección fuera del alcance bloqueada: {destination.display_url}")
        return super().redirect_request(req, fp, code, msg, headers, destination.request_url)


class HttpHeaderAuditService:
    """Report standard defensive HTTP headers and cookie attributes."""

    tool_id = "headers"
    display_name = "Auditar HTTP"
    shortcut = "F2"
    guide = ToolGuide(
        purpose="Revisa cabeceras HTTP defensivas y atributos Secure, HttpOnly y SameSite de las cookies.",
        steps=(
            "Introduce una URL completa con http:// o https://.",
            "Confirma que tienes autorización sobre ese origen.",
            "Ejecuta y revisa qué cabeceras aparecen como PRESENTE o FALTANTE.",
        ),
        output="Informa del estado HTTP, seis cabeceras de seguridad y atributos ausentes en cookies.",
        safety="Envía una única petición HEAD, no reintenta HTTP 429 y bloquea redirecciones fuera del origen.",
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

    @staticmethod
    def _build_result(
        url: str,
        status: int,
        headers: Message | None,
        report: ActivityReporter,
        rate_limited: bool = False,
    ) -> CheckResult:
        rows = [f"URL      : {url}", f"ESTADO   : {status}"]
        if rate_limited:
            retry_after = headers.get("Retry-After", "no indicado") if headers else "no indicado"
            rows.extend(("", "RESULTADO PARCIAL: el servidor limitó la solicitud (HTTP 429).", f"RETRY-AFTER: {retry_after}"))
        rows.extend(("", "CABECERA                          ESTADO"))
        for header in SECURITY_HEADERS:
            state = "PRESENTE" if headers and headers.get(header) else "FALTANTE"
            rows.append(f"{header:<33} {state}")
            report(f"> {header}: {state}")

        cookies = headers.get_all("Set-Cookie", []) if headers else []
        rows.extend(("", f"COOKIES OBSERVADAS: {len(cookies)}"))
        for index, cookie in enumerate(cookies, start=1):
            attributes = cookie.lower()
            missing = [
                name
                for name, present in (
                    ("Secure", "; secure" in attributes),
                    ("HttpOnly", "; httponly" in attributes),
                    ("SameSite", "samesite=" in attributes),
                )
                if not present
            ]
            state = "OK" if not missing else f"REVISAR: falta {', '.join(missing)}"
            rows.append(f"Cookie #{index:<24} {state}")
            report(f"> Cookie #{index}: {state}")

        title = "AUDITORÍA HTTP PARCIAL (429)" if rate_limited else "AUDITORÍA HTTP COMPLETADA"
        return CheckResult(title, "\n".join(rows))

    def inspect(self, target: str, report: ActivityReporter | None = None) -> CheckResult:
        reporter = resolve_reporter(report)
        try:
            validated = TargetParser.parse_web(target)
        except TargetValidationError as error:
            reporter(f"! Objetivo no válido: {error}")
            return CheckResult("OBJETIVO NO VÁLIDO", str(error))

        reporter(f"> Preparando solicitud HEAD a {validated.display_url}")
        request = Request(
            validated.request_url,
            headers={"User-Agent": "RetroAudit/1.0 (authorized assessment)", "Accept": "*/*"},
            method="HEAD",
        )
        opener = build_opener(SameOriginRedirectHandler(validated), HTTPSHandler(context=ssl.create_default_context()))
        try:
            reporter("> Conectando y obteniendo respuesta HTTP...")
            with opener.open(request, timeout=8) as response:
                reporter(f"+ Respuesta recibida: HTTP {response.status}")
                response_target = TargetParser.parse_web(response.url)
                result = self._build_result(response_target.display_url, response.status, response.headers, reporter)
        except RedirectScopeError as error:
            reporter(f"! {error}")
            return CheckResult("REDIRECCIÓN BLOQUEADA", str(error))
        except HTTPError as error:
            if error.code != 429:
                reporter(f"! Error HTTP {error.code}: {error.reason}")
                return CheckResult("ERROR HTTP", f"No se pudo consultar {validated.display_url}\nHTTP {error.code}: {error.reason}")
            retry_after = error.headers.get("Retry-After", "no indicado") if error.headers else "no indicado"
            reporter(f"! Límite de solicitudes detectado (HTTP 429). Retry-After: {retry_after}")
            result = self._build_result(validated.display_url, error.code, error.headers, reporter, rate_limited=True)
        except (URLError, TimeoutError, ValueError, ssl.SSLError) as error:
            reporter(f"! Error de conexión: {error}")
            return CheckResult("ERROR HTTP", f"No se pudo consultar {validated.display_url}\n{error}")
        reporter("+ Auditoría de cabeceras finalizada.")
        return result
