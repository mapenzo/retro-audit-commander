"""Application service construction."""

from retro_audit.contracts import ApplicationServices
from retro_audit.registry import ToolRegistry
from retro_audit.reporting import ReportService
from retro_audit.tools import (
    BannerGrabService,
    BannerProbe,
    BruteForceLogAuditService,
    HttpHeaderAuditService,
    LockoutSimulationService,
    NetworkAuditService,
    PasswordStrengthAuditService,
    SshConfigurationAuditService,
    SshCredentialVerificationService,
    TlsAuditService,
)


class AuditServiceFactory:
    """Centralize service creation and dependency assembly."""

    @staticmethod
    def create_network_service() -> NetworkAuditService:
        return NetworkAuditService()

    @staticmethod
    def create_http_service() -> HttpHeaderAuditService:
        return HttpHeaderAuditService()

    @staticmethod
    def create_tls_service() -> TlsAuditService:
        return TlsAuditService()

    @staticmethod
    def create_banner_service(probes: tuple[BannerProbe, ...] | None = None) -> BannerGrabService:
        return BannerGrabService() if probes is None else BannerGrabService(probes=probes)

    @staticmethod
    def create_ssh_credential_service() -> SshCredentialVerificationService:
        return SshCredentialVerificationService()

    @staticmethod
    def create_password_strength_service() -> PasswordStrengthAuditService:
        return PasswordStrengthAuditService()

    @staticmethod
    def create_lockout_simulation_service() -> LockoutSimulationService:
        return LockoutSimulationService()

    @staticmethod
    def create_ssh_configuration_service() -> SshConfigurationAuditService:
        return SshConfigurationAuditService()

    @staticmethod
    def create_brute_force_log_service() -> BruteForceLogAuditService:
        return BruteForceLogAuditService()

    @staticmethod
    def create_report_service() -> ReportService:
        return ReportService()

    @classmethod
    def create_tool_registry(cls) -> ToolRegistry:
        return ToolRegistry(
            (
                cls.create_network_service(),
                cls.create_http_service(),
                cls.create_tls_service(),
                cls.create_banner_service(),
                cls.create_ssh_credential_service(),
                cls.create_password_strength_service(),
                cls.create_lockout_simulation_service(),
                cls.create_ssh_configuration_service(),
                cls.create_brute_force_log_service(),
            )
        )

    @classmethod
    def create_services(cls) -> ApplicationServices:
        return ApplicationServices(
            tools=cls.create_tool_registry(),
            reports=cls.create_report_service(),
        )
