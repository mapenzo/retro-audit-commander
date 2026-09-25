"""Presentation constants for the Commander-inspired UI."""

SPLASH_LOGO = "\n".join(
    (
        "+======================================================+",
        "|              R E T R O   A U D I T                 |",
        "+--------------- C O M M A N D E R ------------------+",
    )
)

SPLASH_RADAR_FRAMES = (
    "      |      \n   .--+--.   \n  /   |   \\  \n |    *----> \n  \\       /  \n   '-----'   ",
    "          /  \n   .-----/   \n  /    /  \\  \n |    *    | \n  \\  /    /  \n   '-----'   ",
    "             \n   .-------.  \n  /         \\ \n <-----*     |\n  \\         / \n   '-------'  ",
    "  \\          \n   \\-----.   \n  / \\       \\  \n |    *      | \n  \\    \\    /  \n   '-----'   ",
)

SPLASH_STATUS_MESSAGES = (
    "[·] INICIALIZANDO CONSOLA DEFENSIVA",
    "[·] PREPARANDO REGISTRO DE HERRAMIENTAS",
    "[·] CARGANDO INTERFAZ COMMANDER",
    "[OK] SISTEMA PREPARADO",
)

ASCII_RADAR_FRAMES = (
    "     |\n  .--+--.\n /   |   \\\n|    *---->\n \\       /\n  '-----'",
    "       /\n  .---/-.\n /   /   \\\n|   *     |\n \\ /     /\n  '-----'",
    "\n  .-----.\n /       \\\n<----*    |\n \\       /\n  '-----'",
    "  \\n  .-\\---.\n /   \\   \\\n|     *   |\n \\     \\ /\n  '-----'",
)

MENU_ENTRIES = {
    "menu_file": ("ARCHIVO", (("menu_save", "Guardar informe"), ("menu_quit", "Salir"))),
    "menu_window": ("VENTANA", (("menu_clear", "Limpiar paneles"),)),
}

APP_CSS = """
Screen { background: #0000aa; color: #ffffff; }
Footer { background: #0000aa; color: #ffff55; }
#titlebar { height: 1; background: #55ffff; color: #000000; content-align: center middle; }
#menu_bar { height: 1; background: #ffffff; }
#menu_bar Button { width: auto; min-width: 0; height: 1; margin: 0; border: none; background: #ffffff; color: #000000; padding: 0 2; }
#menu_bar Button:hover { background: #0000aa; color: #ffffff; }
#workspace { height: 1fr; min-height: 16; margin: 1 1 0 1; }
.commander_panel { width: 1fr; height: 1fr; border: double #ffffff; background: #0000aa; padding: 0 1; }
#left_panel { margin-right: 1; }
#right_panel { margin-left: 1; }
.panel_title { height: 1; background: #ffffff; color: #0000aa; content-align: center middle; }
#result { height: 1fr; color: #ffffff; padding: 1 0; }
#target_label { color: #ffff55; height: 1; margin-top: 1; }
Input { height: 3; border: tall #ffffff; background: #0000aa; color: #ffffff; }
Input:focus { border: tall #55ffff; }
Checkbox { height: 3; width: 1fr; color: #ffff55; background: #0000aa; margin-top: 1; padding: 0 1; }
Checkbox:focus { background: #55ffff; color: #000000; }
#scope { color: #55ffff; height: 1; }
#catalog { color: #ffffff; margin-top: 1; }
#activity_status { color: #ffff55; height: 1; margin: 1 2 0 2; }
#activity { border: double #ffffff; background: #0000aa; color: #ffffff; height: 9; margin: 0 1; }
"""
