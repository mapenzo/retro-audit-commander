"""Bounded TCP connectivity audit tool."""

import socket
from typing import Mapping

from retro_audit.contracts import ActivityReporter, CheckResult, ToolGuide, resolve_reporter
from retro_audit.targets import TargetParser, TargetValidationError

COMMON_PORTS = (21, 22, 25, 53, 80, 110, 143, 443, 445, 3306, 3389, 8080)


class NetworkAuditService:
    """Perform non-invasive TCP connectivity checks with a short timeout."""

    tool_id = "scan"
    display_name = "Escanear puertos"
    shortcut = "F1"
    guide = ToolGuide(
        purpose="Comprueba si una lista fija de puertos TCP comunes está accesible en un host o una IP.",
        steps=(
            "Escribe un nombre de host o una dirección IP en OBJETIVO AUTORIZADO.",
            "Marca Autorización confirmada para ese objetivo.",
            "Ejecuta la herramienta y espera a que termine la lista de comprobaciones.",
        ),
        output="Muestra la IP resuelta y el estado abierto o cerrado/filtrado de cada puerto examinado.",
        safety="No descubre todos los puertos: sólo comprueba la lista fija de puertos comunes con timeout corto.",
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
        return self.scan_common_ports(target, report)

    def scan_common_ports(self, target: str, report: ActivityReporter | None = None) -> CheckResult:
        reporter = resolve_reporter(report)
        try:
            hostname = TargetParser.parse_host(target)
        except TargetValidationError as error:
            reporter(f"! Objetivo no válido: {error}")
            return CheckResult("OBJETIVO NO VÁLIDO", str(error))

        reporter(f"> Resolviendo {hostname}...")
        try:
            ip_address = socket.gethostbyname(hostname)
        except socket.gaierror:
            reporter("! No fue posible resolver el objetivo.")
            return CheckResult("ERROR", f"No se pudo resolver el host: {hostname}")

        reporter(f"+ Objetivo resuelto: {ip_address}")
        rows = [f"OBJETIVO : {hostname} ({ip_address})", "", "PUERTO  ESTADO"]
        open_ports: list[int] = []
        total_ports = len(COMMON_PORTS)
        for index, port in enumerate(COMMON_PORTS, start=1):
            reporter(f"> [{index:02}/{total_ports:02}] Comprobando TCP/{port}...")
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as connection:
                connection.settimeout(0.75)
                is_open = connection.connect_ex((ip_address, port)) == 0
            state = "ABIERTO" if is_open else "cerrado/filtrado"
            rows.append(f"{port:<7} {state}")
            if is_open:
                open_ports.append(port)
                reporter(f"+ TCP/{port} está abierto")

        rows.extend(("", f"Puertos abiertos: {len(open_ports)} de {total_ports}"))
        reporter("+ Escaneo finalizado.")
        return CheckResult("ESCANEO TCP COMPLETADO", "\n".join(rows))
