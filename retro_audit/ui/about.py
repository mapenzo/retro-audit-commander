"""Detailed About window for Retro Audit Commander."""

from textual.app import ComposeResult
from textual.containers import Vertical, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import Button, Static

from retro_audit.metadata import AboutInfo
from retro_audit.ui.constants import SPLASH_LOGO


class AboutWindow(ModalScreen[None]):
    """Render trusted project, legal, runtime, and contact metadata."""

    BINDINGS = [("escape", "close", "Cerrar Acerca de")]

    CSS = """
    AboutWindow { align: center middle; background: rgba(0, 0, 0, 0.72); }
    #about_window {
        width: 92%; max-width: 88; height: 88%; min-height: 16;
        border: double #ffffff; background: #0000aa; padding: 1 2;
    }
    #about_title { height: 1; color: #ffff55; content-align: center middle; text-style: bold; }
    #about_logo { height: 3; color: #55ffff; content-align: center middle; margin-top: 1; }
    #about_scroll { height: 1fr; margin: 1 0; border: solid #55ffff; padding: 1; }
    #about_body { height: auto; color: #ffffff; }
    #about_hint { height: 1; color: #55ffff; content-align: center middle; }
    #about_close {
        width: 22; height: 3; min-width: 0; margin-top: 1;
        background: #55ffff; color: #000000;
    }
    #about_close:hover, #about_close:focus { background: #ffff55; text-style: bold; }
    """

    def __init__(self, info: AboutInfo) -> None:
        super().__init__()
        self.info = info

    def compose(self) -> ComposeResult:
        with Vertical(id="about_window"):
            yield Static("ACERCA DE", id="about_title", markup=False)
            yield Static(SPLASH_LOGO, id="about_logo", markup=False)
            with VerticalScroll(id="about_scroll"):
                yield Static(self._build_content(), id="about_body", markup=False)
            yield Static("↑/↓ desplazar · Esc cerrar", id="about_hint", markup=False)
            yield Button("CERRAR", id="about_close")

    def on_mount(self) -> None:
        self.query_one("#about_scroll", VerticalScroll).focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        event.stop()
        self.dismiss()

    def action_close(self) -> None:
        self.dismiss()

    def _build_content(self) -> str:
        return "\n".join(
            (
                f"{self.info.name} · versión {self.info.version}",
                "",
                "PROPÓSITO",
                self.info.purpose,
                "",
                "AUTORÍA Y LICENCIA",
                f"Autor: {self.info.author}",
                self.info.copyright_notice,
                f"Licencia: {self.info.license_name}",
                "",
                "USO AUTORIZADO",
                self.info.authorized_use_notice,
                "",
                "ENTORNO DE EJECUCIÓN",
                f"Python:   {self.info.python_version}",
                f"Textual:  {self.info.textual_version}",
                f"Paramiko: {self.info.paramiko_version}",
                "",
                "PROYECTO Y CONTACTO",
                f"Repositorio: {self.info.repository_url}",
                f"Contacto:    {self.info.contact_url}",
            )
        )
