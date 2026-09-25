"""Floating screens for the Commander-inspired interface."""

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Label, Static

from retro_audit.contracts import AuditTool, ToolField, ToolGuide


class CommanderMenu(ModalScreen[str | None]):
    """A mouse-accessible floating menu."""

    BINDINGS = [("escape", "cancel", "Cerrar menú")]

    CSS = """
    CommanderMenu { align: center middle; background: rgba(0, 0, 0, 0.65); }
    #menu_window { width: 36; height: auto; border: double #ffffff; background: #0000aa; padding: 1 2; }
    #menu_title { color: #ffff55; content-align: center middle; height: 1; }
    #menu_window Button { width: 1fr; height: 1; min-width: 0; margin: 0; border: none; background: #0000aa; color: #ffffff; content-align: left middle; }
    #menu_window Button:hover { background: #55ffff; color: #000000; }
    """

    def __init__(self, title: str, entries: tuple[tuple[str, str], ...]) -> None:
        super().__init__()
        self.title = title
        self.entries = entries

    def compose(self) -> ComposeResult:
        with Vertical(id="menu_window"):
            yield Static(self.title, id="menu_title", markup=False)
            for action, label in self.entries:
                yield Button(label, id=action)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        event.stop()
        self.dismiss(event.button.id)

    def action_cancel(self) -> None:
        self.dismiss(None)


class CommanderInfoWindow(ModalScreen[str | None]):
    """A scrollable operating guide for every registered tool."""

    BINDINGS = [("escape", "close", "Cerrar ayuda")]

    CSS = """
    CommanderInfoWindow { align: center middle; background: rgba(0, 0, 0, 0.65); }
    #info_window { width: 92%; max-width: 100; height: 90%; border: double #ffffff; background: #0000aa; padding: 1 2; }
    #info_title { color: #ffff55; content-align: center middle; height: 1; }
    #info_scroll { height: 1fr; margin: 1 0; border: solid #55ffff; padding: 1; }
    #info_body { color: #ffffff; height: auto; }
    #info_hint { color: #55ffff; height: 1; content-align: center middle; }
    #info_actions { height: 3; align-horizontal: center; margin-top: 1; }
    #info_actions Button { width: 24; height: 3; min-width: 0; margin: 0 1; }
    #close_info { background: #ffffff; color: #000000; }
    #info_actions Button:hover, #info_actions Button:focus { background: #ffff55; text-style: bold; }
    """

    def __init__(self, tools: tuple[AuditTool, ...]) -> None:
        super().__init__()
        self.tools = tools

    def compose(self) -> ComposeResult:
        with Vertical(id="info_window"):
            yield Static("GUÍA DE HERRAMIENTAS · RETRO AUDIT", id="info_title", markup=False)
            with VerticalScroll(id="info_scroll"):
                yield Static(self._build_guide(), id="info_body", markup=False)
            yield Static("↑/↓ desplazar · Esc cerrar", id="info_hint", markup=False)
            with Horizontal(id="info_actions"):
                yield Button("CERRAR", id="close_info")

    def on_mount(self) -> None:
        self.query_one("#info_scroll", VerticalScroll).focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        event.stop()
        self.dismiss(None)

    def action_close(self) -> None:
        self.dismiss(None)

    def _build_guide(self) -> str:
        sections = [
            "INICIO RÁPIDO",
            "1. Para herramientas de red, escribe el objetivo y marca Autorización confirmada.",
            "2. Abre Auditoría y selecciona una herramienta, o usa su tecla F si el terminal la admite.",
            "3. Completa el formulario si aparece y pulsa EJECUTAR.",
            "4. Revisa la ventana de resultado; el panel izquierdo conservará la última salida.",
            "",
            "HERRAMIENTAS",
        ]
        for tool in self.tools:
            guide = getattr(tool, "guide", None)
            sections.extend(("", f"{tool.shortcut} · {tool.display_name.upper()}"))
            if guide is None:
                sections.append("No hay instrucciones adicionales disponibles para esta extensión.")
                continue
            sections.extend((f"QUÉ HACE: {guide.purpose}", "CÓMO USAR:"))
            sections.extend(f"  {index}. {step}" for index, step in enumerate(guide.steps, start=1))
            sections.extend((f"RESULTADO: {guide.output}", f"SEGURIDAD: {guide.safety}"))
        return "\n".join(sections)


class ToolOptionsWindow(ModalScreen[dict[str, str] | None]):
    """Build a safe data-entry dialog from presentation-neutral tool metadata."""

    BINDINGS = [
        ("escape", "cancel", "Cancelar"),
        ("ctrl+enter", "submit", "Ejecutar"),
    ]

    CSS = """
    ToolOptionsWindow { align: center middle; background: rgba(0, 0, 0, 0.70); }
    #options_window { width: 68; height: auto; max-height: 36; border: double #ffffff; background: #0000aa; padding: 1 2; }
    #options_title { color: #ffff55; content-align: center middle; height: 1; }
    #options_help { color: #55ffff; height: auto; margin: 1 0; }
    #options_fields { height: auto; }
    .field_label { color: #ffffff; height: 1; }
    .tool_field { height: 3; border: tall #ffffff; background: #0000aa; color: #ffffff; margin-bottom: 1; }
    .tool_field:focus { border: tall #55ffff; }
    #options_error { color: #ff5555; height: 1; content-align: center middle; }
    #options_actions { height: 3; align-horizontal: center; margin-top: 1; }
    #options_actions Button { width: 22; min-width: 0; height: 3; margin: 0 1; }
    #options_submit { background: #55ffff; color: #000000; }
    #options_submit:hover, #options_submit:focus { background: #ffff55; color: #000000; text-style: bold; }
    #options_cancel { background: #ffffff; color: #000000; }
    #options_cancel:hover, #options_cancel:focus { background: #ff5555; color: #ffffff; }
    """

    def __init__(self, title: str, fields: tuple[ToolField, ...], guide: ToolGuide | None = None) -> None:
        super().__init__()
        self.title = title
        self.fields = fields
        self.guide = guide
        self._submitted = False

    def compose(self) -> ComposeResult:
        with Vertical(id="options_window"):
            yield Static(self.title.upper(), id="options_title", markup=False)
            yield Static(
                self._contextual_help(),
                id="options_help",
                markup=False,
            )
            with Vertical(id="options_fields"):
                for field in self.fields:
                    required = " *" if field.required else ""
                    yield Label(f"{field.label}{required}", classes="field_label")
                    yield Input(
                        value=field.default,
                        placeholder=field.placeholder,
                        password=field.secret,
                        id=f"tool_field_{field.key}",
                        classes="tool_field",
                    )
            yield Static("", id="options_error", markup=False)
            with Horizontal(id="options_actions"):
                yield Button("EJECUTAR", id="options_submit")
                yield Button("CANCELAR", id="options_cancel")

    def on_mount(self) -> None:
        self.query_one(".tool_field", Input).focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        event.stop()
        if event.button.id == "options_cancel":
            self.dismiss(None)
            return
        self._submit()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        event.stop()
        self._submit()

    def action_submit(self) -> None:
        self._submit()

    def action_cancel(self) -> None:
        self.dismiss(None)

    def _submit(self) -> None:
        if self._submitted:
            return
        values = {
            field.key: self.query_one(f"#tool_field_{field.key}", Input).value
            for field in self.fields
        }
        missing = [field.label for field in self.fields if field.required and not values[field.key].strip()]
        if missing:
            self.query_one("#options_error", Static).update(f"Campos obligatorios: {', '.join(missing)}")
            return
        self._submitted = True
        self.dismiss(values)

    def _contextual_help(self) -> str:
        if self.guide is None:
            return (
                "Completa los campos y pulsa EJECUTAR. El resultado se abrirá en una ventana.\n"
                "Los campos marcados con * son obligatorios; los secretos no se guardan."
            )
        steps = "\n".join(f"{index}. {step}" for index, step in enumerate(self.guide.steps, start=1))
        return f"QUÉ HACE: {self.guide.purpose}\n\nCÓMO USAR:\n{steps}"


class AuditResultWindow(ModalScreen[None]):
    """Show a completed audit prominently instead of relying on a background panel."""

    BINDINGS = [
        ("escape", "close", "Cerrar"),
        ("enter", "close", "Cerrar"),
    ]

    CSS = """
    AuditResultWindow { align: center middle; background: rgba(0, 0, 0, 0.72); }
    #audit_result_window { width: 90%; max-width: 76; height: 80%; min-height: 14; border: double #ffffff; background: #0000aa; padding: 1 2; }
    #audit_result_title { color: #ffff55; content-align: center middle; height: 1; text-style: bold; }
    #audit_result_scroll { height: 1fr; margin: 1 0; border: solid #55ffff; padding: 1; }
    #audit_result_body { color: #ffffff; height: auto; }
    #audit_result_hint { color: #55ffff; height: 1; content-align: center middle; }
    #audit_result_close { width: 22; height: 3; min-width: 0; margin: 1 0 0 0; align-horizontal: center; background: #55ffff; color: #000000; }
    #audit_result_close:hover, #audit_result_close:focus { background: #ffff55; color: #000000; text-style: bold; }
    """

    def __init__(self, title: str, body: str) -> None:
        super().__init__()
        self.result_title = title
        self.result_body = body

    def compose(self) -> ComposeResult:
        with Vertical(id="audit_result_window"):
            yield Static(self.result_title, id="audit_result_title", markup=False)
            with VerticalScroll(id="audit_result_scroll"):
                yield Static(self.result_body, id="audit_result_body", markup=False)
            yield Static("Resultado completado · Enter/Esc para cerrar", id="audit_result_hint", markup=False)
            yield Button("CERRAR RESULTADO", id="audit_result_close")

    def on_mount(self) -> None:
        self.query_one("#audit_result_close", Button).focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        event.stop()
        self.dismiss()

    def action_close(self) -> None:
        self.dismiss()
