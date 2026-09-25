"""Non-blocking retro startup splash and its configuration."""

from __future__ import annotations

import os
from dataclasses import dataclass, replace

from textual import events
from textual.app import ComposeResult
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.timer import Timer
from textual.widgets import Static

from retro_audit.metadata import AboutInfo, ApplicationMetadataFactory
from retro_audit.ui.about import AboutWindow
from retro_audit.ui.constants import SPLASH_LOGO, SPLASH_RADAR_FRAMES, SPLASH_STATUS_MESSAGES

_TRUE_VALUES = frozenset({"1", "true", "yes", "on"})


@dataclass(frozen=True)
class SplashConfig:
    """Immutable startup-animation policy."""

    enabled: bool = True
    duration_seconds: float = 2.5
    frame_interval_seconds: float = 0.12
    reduced_motion: bool = False
    application_version: str = "dev"

    def __post_init__(self) -> None:
        if self.duration_seconds <= 0:
            raise ValueError("La duración de la splash debe ser positiva.")
        if self.frame_interval_seconds <= 0:
            raise ValueError("El intervalo de animación debe ser positivo.")

    @classmethod
    def from_environment(cls, application_version: str) -> SplashConfig:
        """Build configuration from documented accessibility environment flags."""
        return cls(
            enabled=not _environment_flag("RETRO_AUDIT_SKIP_SPLASH"),
            reduced_motion=_environment_flag("RETRO_AUDIT_REDUCED_MOTION"),
            application_version=application_version,
        )

    @classmethod
    def disabled(cls) -> SplashConfig:
        """Return deterministic configuration for tests and automation."""
        return cls(enabled=False)

    def enabled_copy(self) -> SplashConfig:
        """Enable a copy for an explicit replay while preserving accessibility settings."""
        return replace(self, enabled=True)


class RetroSplashScreen(ModalScreen[None]):
    """Responsive CRT/radar splash driven exclusively by Textual timers."""

    CSS = """
    RetroSplashScreen { align: center middle; background: #000022; }
    #splash_window {
        width: 94%; max-width: 78; height: auto;
        border: double #55ffff; background: #0000aa; padding: 1 2;
    }
    #splash_logo { height: auto; color: #55ffff; content-align: center middle; text-style: bold; }
    #splash_radar { height: 6; color: #55ff55; content-align: center middle; }
    #splash_status { height: 1; color: #ffff55; content-align: center middle; }
    #splash_progress { height: 1; color: #ffffff; content-align: center middle; }
    #splash_version { height: 1; color: #55ffff; content-align: center middle; }
    #splash_hint { height: 1; color: #ffffff; content-align: center middle; }
    """

    def __init__(self, config: SplashConfig) -> None:
        super().__init__()
        self.config = config
        self.frame_index = 0
        self._closed = False
        self._animation_timer: Timer | None = None
        self._dismiss_timer: Timer | None = None

    def compose(self) -> ComposeResult:
        with Vertical(id="splash_window"):
            yield Static(SPLASH_LOGO, id="splash_logo", markup=False)
            yield Static(SPLASH_RADAR_FRAMES[0], id="splash_radar", markup=False)
            yield Static(SPLASH_STATUS_MESSAGES[0], id="splash_status", markup=False)
            yield Static(self._progress_bar(0.0), id="splash_progress", markup=False)
            yield Static(f"RETRO AUDIT COMMANDER · v{self.config.application_version}", id="splash_version", markup=False)
            yield Static("Pulsa cualquier tecla o haz clic para continuar", id="splash_hint", markup=False)

    def on_mount(self) -> None:
        if self.config.reduced_motion:
            self.query_one("#splash_radar", Static).update(SPLASH_RADAR_FRAMES[-1])
            self.query_one("#splash_status", Static).update("[OK] INTERFAZ PREPARADA · MOVIMIENTO REDUCIDO")
            self.query_one("#splash_progress", Static).update(self._progress_bar(1.0))
        else:
            self._animation_timer = self.set_interval(
                self.config.frame_interval_seconds,
                self._advance_animation,
                name="retro-splash-animation",
            )
        visible_duration = min(1.0, self.config.duration_seconds) if self.config.reduced_motion else self.config.duration_seconds
        self._dismiss_timer = self.set_timer(visible_duration, self._finish, name="retro-splash-dismiss")

    def on_key(self, event: events.Key) -> None:
        event.stop()
        self._finish()

    def on_click(self, event: events.Click) -> None:
        event.stop()
        self._finish()

    def on_unmount(self) -> None:
        self._stop_timers()

    def _advance_animation(self) -> None:
        self.frame_index += 1
        elapsed = self.frame_index * self.config.frame_interval_seconds
        progress = min(1.0, elapsed / self.config.duration_seconds)
        radar_index = self.frame_index % len(SPLASH_RADAR_FRAMES)
        status_index = min(int(progress * len(SPLASH_STATUS_MESSAGES)), len(SPLASH_STATUS_MESSAGES) - 1)
        self.query_one("#splash_radar", Static).update(SPLASH_RADAR_FRAMES[radar_index])
        self.query_one("#splash_status", Static).update(SPLASH_STATUS_MESSAGES[status_index])
        self.query_one("#splash_progress", Static).update(self._progress_bar(progress))

    def _finish(self) -> None:
        if self._closed:
            return
        self._closed = True
        self._stop_timers()
        self.dismiss()

    def _stop_timers(self) -> None:
        for timer in (self._animation_timer, self._dismiss_timer):
            if timer is not None:
                timer.stop()

    @staticmethod
    def _progress_bar(progress: float) -> str:
        width = 28
        completed = round(width * max(0.0, min(progress, 1.0)))
        return f"[{'█' * completed}{'░' * (width - completed)}] {round(progress * 100):3d}%"


class UiScreenFactory:
    """Centralize construction of configurable UI screens."""

    @staticmethod
    def create_splash_config() -> SplashConfig:
        return SplashConfig.from_environment(ApplicationMetadataFactory.application_version())

    @staticmethod
    def create_splash(config: SplashConfig) -> RetroSplashScreen:
        return RetroSplashScreen(config)

    @staticmethod
    def create_about(info: AboutInfo) -> AboutWindow:
        return AboutWindow(info)


def _environment_flag(name: str) -> bool:
    return os.getenv(name, "").strip().casefold() in _TRUE_VALUES
