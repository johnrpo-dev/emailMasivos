# pyrefly: ignore [missing-import]
"""Diálogos modales temáticos de SEMS Pro.

Reemplazan a tkinter.messagebox con ventanas coherentes con el tema clínico
(claro/oscuro). Todos son modales: bloquean con grab_set() y retornan al
cerrarse. Si el padre era a su vez un modal con grab, éste se restaura.
"""
import customtkinter as ctk
from src.ui import theme
from src.ui.components import (
    PrimaryButton, SecondaryButton, DangerButton,
    apply_window_icon, center_window, state_colors,
)

# Símbolo del icono circular por tipo de diálogo
_ICONS = {
    "info": "i",
    "success": "✓",
    "warning": "!",
    "danger": "✕",
    "question": "?",
}


class _ThemedDialog(ctk.CTkToplevel):
    """Base de diálogo modal con icono circular, mensaje y botonera."""

    def __init__(self, parent, title: str, message: str, kind: str = "info",
                 buttons=None):
        super().__init__(parent)
        self.result = None
        self._prev_grab = None
        try:
            self._prev_grab = parent.grab_current()
        except Exception:
            pass

        self.title(title)
        self.resizable(False, False)
        self.configure(fg_color=theme.APP_BG)
        self.transient(parent)
        apply_window_icon(self)

        color, bg, border = state_colors(kind if kind != "question" else "info")

        # Icono circular del tipo de mensaje
        icon_frame = ctk.CTkFrame(
            self, width=56, height=56, corner_radius=28,
            fg_color=bg, border_width=2, border_color=border
        )
        icon_frame.pack(pady=(theme.SP_XL, theme.SP_SM))
        icon_frame.pack_propagate(False)
        ctk.CTkLabel(
            icon_frame, text=_ICONS.get(kind, "i"),
            font=ctk.CTkFont(family=theme.FONT_FAMILY, size=26, weight="bold"),
            text_color=color
        ).place(relx=0.5, rely=0.5, anchor="center")

        ctk.CTkLabel(
            self, text=title, font=theme.font("h2"), text_color=theme.TEXT
        ).pack(pady=(0, theme.SP_SM), padx=theme.SP_XL)

        ctk.CTkLabel(
            self, text=message, font=theme.font("body"),
            text_color=theme.TEXT_SECONDARY, wraplength=380, justify="center"
        ).pack(pady=(0, theme.SP_LG), padx=theme.SP_XL)

        # Botonera: lista de tuplas (texto, valor_resultado, clase_de_boton)
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(pady=(0, theme.SP_XL), padx=theme.SP_XL)

        for text, value, btn_cls in buttons:
            btn = btn_cls(
                btn_frame, text=text, width=130, height=theme.BTN_SM_H + 6,
                command=lambda v=value: self._finish(v)
            )
            btn.pack(side="left", padx=theme.SP_XS + 2)

        self.protocol("WM_DELETE_WINDOW", lambda: self._finish(None))
        self.bind("<Escape>", lambda e: self._finish(None))

        # Dimensionar según contenido y centrar
        self.update_idletasks()
        req_w = max(self.winfo_reqwidth() + 40, 420)
        req_h = self.winfo_reqheight() + 20
        center_window(self, req_w, req_h)

        self.grab_set()
        self.focus_set()
        self.wait_window()

    def _finish(self, value):
        self.result = value
        try:
            self.grab_release()
        except Exception:
            pass
        self.destroy()
        # Restaurar el grab del modal padre, si existía
        if self._prev_grab is not None:
            try:
                if self._prev_grab.winfo_exists():
                    self._prev_grab.grab_set()
            except Exception:
                pass


def show_info(parent, title: str, message: str) -> None:
    """Muestra un mensaje informativo modal."""
    _ThemedDialog(parent, title, message, kind="info",
                  buttons=[("Aceptar", True, PrimaryButton)])


def show_success(parent, title: str, message: str) -> None:
    """Muestra un mensaje de éxito modal."""
    _ThemedDialog(parent, title, message, kind="success",
                  buttons=[("Aceptar", True, PrimaryButton)])


def show_warning(parent, title: str, message: str) -> None:
    """Muestra una advertencia modal."""
    _ThemedDialog(parent, title, message, kind="warning",
                  buttons=[("Aceptar", True, PrimaryButton)])


def show_error(parent, title: str, message: str) -> None:
    """Muestra un error modal."""
    _ThemedDialog(parent, title, message, kind="danger",
                  buttons=[("Aceptar", True, PrimaryButton)])


def ask_yes_no(parent, title: str, message: str, danger: bool = False) -> bool:
    """Pregunta modal Sí/No. Devuelve True solo si el usuario confirma."""
    yes_cls = DangerButton if danger else PrimaryButton
    dlg = _ThemedDialog(parent, title, message, kind="question",
                        buttons=[("Cancelar", False, SecondaryButton),
                                 ("Sí, continuar", True, yes_cls)])
    return bool(dlg.result)
