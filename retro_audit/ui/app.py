"""Commander-inspired Textual presentation layer."""

from textual import work
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Button, Checkbox, Footer, Input, RichLog, Static

from retro_audit.contracts import ApplicationServices, AuditTool, CheckResult
from retro_audit.metadata import AboutInfo, ApplicationMetadataFactory
from retro_audit.ui.constants import APP_CSS, ASCII_RADAR_FRAMES, MENU_ENTRIES
from retro_audit.ui.screens import AuditResultWindow, CommanderInfoWindow, CommanderMenu, ToolOptionsWindow
from retro_audit.ui.splash import RetroSplashScreen, SplashConfig, UiScreenFactory


class RetroAuditApp(App[None]):
    """Orchestrate the UI while delegating all audit work to injected services."""

    CSS = APP_CSS
    BINDINGS = [
        ("r", "save_report", "Guardar reporte"),
        ("ctrl+c", "quit", "Salir"),
    ]

    def __init__(
        self,
        services: ApplicationServices,
        splash_config: SplashConfig | None = None,
        screen_factory: UiScreenFactory | None = None,
        about_info: AboutInfo | None = None,
    ) -> None:
        super().__init__()
        self.services = services
        self.splash_config = splash_config or UiScreenFactory.create_splash_config()
        self.screen_factory = screen_factory or UiScreenFactory()
        self.about_info = about_info or ApplicationMetadataFactory.create_about_info()
        self.latest_result = "Sin resultados todavía."
        self.audit_running = False
        self.animation_index = 0
        self.active_tool = ""
        self.authorized_target: str | None = None

    @property
    def command_catalog(self) -> str:
        """Build the visible command catalog from the injected registry."""
        commands = [f"{tool.shortcut:<3} {tool.display_name}" for tool in self.services.tools.all()]
        commands.extend(("R   Guardar informe", "", "Usa AUDITORÍA para abrir acciones con ratón."))
        return "\n".join(commands)

    def compose(self) -> ComposeResult:
        yield Static("RETRO AUDIT COMMANDER · Defensive Web Baseline", id="titlebar", markup=False)
        with Horizontal(id="menu_bar"):
            yield Button("Archivo", id="menu_file")
            yield Button("Auditoría", id="menu_audit")
            yield Button("Ventana", id="menu_window")
            yield Button("Ayuda", id="menu_help")
        with Horizontal(id="workspace"):
            with Vertical(id="left_panel", classes="commander_panel"):
                yield Static("RESULTADOS", classes="panel_title")
                yield Static(self.latest_result, id="result", markup=False)
            with Vertical(id="right_panel", classes="commander_panel"):
                yield Static("OBJETIVO Y COMANDOS", classes="panel_title")
                yield Static("OBJETIVO AUTORIZADO", id="target_label")
                yield Input(placeholder="Host, IP o URL (ej.: localhost)", id="target")
                yield Checkbox("Autorización confirmada", id="authorized")
                yield Static("SCOPE: defensivo / bajo impacto", id="scope")
                yield Static(self.command_catalog, id="catalog", markup=False)
        yield Static("[ ] EN ESPERA: selecciona una herramienta.", id="activity_status", markup=False)
        yield RichLog(id="activity", wrap=True, highlight=False, markup=False)
        yield Footer()

    def on_mount(self) -> None:
        for tool in self.services.tools.all():
            self.bind(
                tool.shortcut.lower(),
                f"run_tool('{tool.tool_id}')",
                description=tool.display_name,
                key_display=tool.shortcut,
            )
        self.set_interval(0.14, self.advance_ascii_animation)
        if self.splash_config.enabled:
            self.show_splash()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "menu_help":
            entries = (
                ("menu_help_guide", "Guía de uso"),
                ("menu_help_splash", "Repetir inicio"),
                ("menu_help_about", "Acerca de"),
            )
            self.push_screen(CommanderMenu("AYUDA", entries), self.handle_help_action)
        elif event.button.id == "menu_audit":
            entries = tuple(
                (f"menu_tool_{tool.tool_id}", f"{tool.shortcut}  {tool.display_name}")
                for tool in self.services.tools.all()
            )
            self.push_screen(CommanderMenu("AUDITORÍA", entries), self.handle_menu_action)
        elif event.button.id in MENU_ENTRIES:
            title, entries = MENU_ENTRIES[event.button.id]
            self.push_screen(CommanderMenu(title, entries), self.handle_menu_action)

    def handle_menu_action(self, action: str | None) -> None:
        actions = {
            "menu_save": self.action_save_report,
            "menu_clear": self.clear_panels,
            "menu_quit": self.exit,
        }
        if action and action.startswith("menu_tool_"):
            self.start_audit(action.removeprefix("menu_tool_"))
            return
        handler = actions.get(action)
        if handler:
            handler()

    def handle_help_action(self, action: str | None) -> None:
        if action == "menu_help_guide":
            self.push_screen(CommanderInfoWindow(self.services.tools.all()))
        elif action == "menu_help_splash":
            self.show_splash(force=True)
        elif action == "menu_help_about":
            self.push_screen(self.screen_factory.create_about(self.about_info))

    def show_splash(self, force: bool = False) -> None:
        """Show startup animation unless disabled, or replay it explicitly."""
        if not force and not self.splash_config.enabled:
            return
        if isinstance(self.screen, RetroSplashScreen):
            return
        config = self.splash_config.enabled_copy() if force else self.splash_config
        self.push_screen(self.screen_factory.create_splash(config))

    def clear_panels(self) -> None:
        if self.audit_running:
            self.notify("Espera a que termine la auditoría activa.", severity="warning")
            return
        self.query_one("#activity", RichLog).clear()
        self.latest_result = "Sin resultados todavía."
        self.query_one("#result", Static).update(self.latest_result)
        self.query_one("#catalog", Static).update(self.command_catalog)
        self.query_one("#activity_status", Static).update("[ ] PANELES LIMPIOS")

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id != "target":
            return
        self.authorized_target = None
        authorization = self.query_one("#authorized", Checkbox)
        if authorization.value:
            authorization.value = False

    def on_checkbox_changed(self, event: Checkbox.Changed) -> None:
        if event.checkbox.id != "authorized":
            return
        self.authorized_target = self.query_one("#target", Input).value.strip() if event.value else None

    def action_run_tool(self, tool_id: str) -> None:
        self.start_audit(tool_id)

    def start_audit(self, tool_id: str) -> None:
        if self.audit_running:
            self.notify("Ya hay una auditoría en ejecución.", severity="warning")
            return
        tool = self.services.tools.get(tool_id)
        if tool is None:
            self.notify("Herramienta no registrada.", severity="error")
            return
        target = self.query_one("#target", Input).value.strip()
        requires_target = getattr(tool, "requires_target", True)
        requires_authorization = getattr(tool, "requires_authorization", True)
        if requires_target and not target:
            self.notify("Introduce un host, IP o URL.", severity="warning")
            return
        authorized = self.query_one("#authorized", Checkbox).value
        if requires_authorization and (not authorized or self.authorized_target != target):
            self.notify("Confirma la autorización para el objetivo actual.", severity="error")
            return

        fields = getattr(tool, "input_fields", ())
        normalized_target = target if requires_target else None
        if fields:
            self.push_screen(
                ToolOptionsWindow(tool.display_name, fields, getattr(tool, "guide", None)),
                lambda options: self._launch_tool(tool, normalized_target, options),
            )
            return
        self._launch_tool(tool, normalized_target, {})

    def _launch_tool(
        self,
        tool: AuditTool,
        target: str | None,
        options: dict[str, str] | None,
    ) -> None:
        if options is None:
            return
        if self.audit_running:
            options.clear()
            self.notify("Ya hay una auditoría en ejecución.", severity="warning")
            return
        if getattr(tool, "requires_authorization", True) and self.authorized_target != target:
            options.clear()
            self.notify("La autorización cambió; operación cancelada.", severity="error")
            return
        self.begin_audit(tool.display_name.upper())
        self.run_audit(tool, target, options)

    @work(thread=True, exclusive=True, group="audit")
    def run_audit(self, tool: AuditTool, target: str | None, options: dict[str, str]) -> None:
        try:
            if options:
                result = tool.execute(target, self.report_activity_from_thread, options)
            else:
                result = tool.execute(target, self.report_activity_from_thread)
        except Exception as error:  # pylint: disable=broad-exception-caught
            self.report_activity_from_thread(f"! Fallo interno controlado: {type(error).__name__}")
            result = CheckResult("ERROR INTERNO", "La herramienta terminó de forma inesperada.")
        finally:
            options.clear()
        self.call_from_thread(self.show_result, result)

    def begin_audit(self, tool_name: str) -> None:
        self.audit_running = True
        self.animation_index = 0
        self.active_tool = tool_name
        self.query_one("#activity", RichLog).clear()
        self.query_one("#catalog", Static).update(ASCII_RADAR_FRAMES[0])
        self.append_activity(f"== INICIANDO {tool_name} ==")
        self.set_controls_disabled(True)

    def report_activity_from_thread(self, message: str) -> None:
        self.call_from_thread(self.append_activity, message)

    def append_activity(self, message: str) -> None:
        self.query_one("#activity", RichLog).write(message)

    def advance_ascii_animation(self) -> None:
        if not self.audit_running:
            return
        spinner_frames = ("[|]", "[/]", "[-]", "[\\\\]")
        frame_index = self.animation_index % len(ASCII_RADAR_FRAMES)
        self.animation_index += 1
        self.query_one("#catalog", Static).update(ASCII_RADAR_FRAMES[frame_index])
        self.query_one("#activity_status", Static).update(
            f"{spinner_frames[frame_index]} EJECUTANDO {self.active_tool}: procesando eventos..."
        )

    def set_controls_disabled(self, disabled: bool) -> None:
        for button in self.query(Button):
            button.disabled = disabled
        self.query_one("#target", Input).disabled = disabled
        self.query_one("#authorized", Checkbox).disabled = disabled

    def show_result(self, result: CheckResult) -> None:
        self.audit_running = False
        self.active_tool = ""
        self.query_one("#activity_status", Static).update("[OK] PROCESO FINALIZADO")
        self.query_one("#catalog", Static).update(self.command_catalog)
        self.set_controls_disabled(False)
        self.latest_result = f"[{result.title}]\n\n{result.body}"
        self.query_one("#result", Static).update(self.latest_result)
        self.push_screen(AuditResultWindow(result.title, result.body))
        self.notify(result.title)

    def action_save_report(self) -> None:
        if self.latest_result == "Sin resultados todavía.":
            self.notify("No hay resultados para guardar.", severity="warning")
            return
        try:
            report = self.services.reports.save(self.latest_result)
        except OSError:
            self.notify("No se pudo guardar el informe de forma segura.", severity="error")
            return
        self.notify(f"Reporte guardado: {report}")
