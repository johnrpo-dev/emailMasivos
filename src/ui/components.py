# pyrefly: ignore [missing-import]
"""Componentes visuales reutilizables de SEMS Pro.

Widgets con el estilo clínico del tema aplicado por defecto; cualquier kwarg
explícito del llamador tiene prioridad sobre los valores del tema.
"""
import os
import customtkinter as ctk
from src.ui import theme

# Mapa de tokens por tipo de estado (texto, fondo, borde)
_KIND_COLORS = {
    "success": (theme.SUCCESS, theme.SUCCESS_BG, theme.SUCCESS_BORDER),
    "danger":  (theme.DANGER, theme.DANGER_BG, theme.DANGER_BORDER),
    "warning": (theme.WARNING, theme.WARNING_BG, theme.WARNING_BORDER),
    "info":    (theme.INFO, theme.INFO_BG, theme.INFO_BORDER),
}


def state_colors(kind: str):
    """Devuelve la terna (texto, fondo, borde) del estado dado."""
    return _KIND_COLORS.get(kind, _KIND_COLORS["info"])


class Card(ctk.CTkFrame):
    """Tarjeta estándar: superficie clara, borde fino y esquinas amplias."""
    def __init__(self, master, **kwargs):
        defaults = dict(
            corner_radius=theme.RAD_LG,
            fg_color=theme.SURFACE,
            border_width=1,
            border_color=theme.BORDER,
        )
        defaults.update(kwargs)
        super().__init__(master, **defaults)


class SectionHeader(ctk.CTkFrame):
    """Encabezado de vista: título h1 con subtítulo opcional."""
    def __init__(self, master, title: str, subtitle: str = None, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.lbl_title = ctk.CTkLabel(
            self, text=title, font=theme.font("h1"), text_color=theme.TEXT
        )
        self.lbl_title.pack(anchor="w", pady=(0, 2))
        if subtitle:
            self.lbl_subtitle = ctk.CTkLabel(
                self, text=subtitle, font=theme.font("body"),
                text_color=theme.TEXT_SECONDARY
            )
            self.lbl_subtitle.pack(anchor="w")


class CardTitle(ctk.CTkFrame):
    """Título de sección dentro de una card: punto de acento + texto h2.

    Sustituye a los emojis de los títulos (dependían de la fuente de emoji
    del sistema y se veían inconsistentes entre equipos).
    """
    def __init__(self, master, text: str, accent=None, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        dot = ctk.CTkFrame(
            self, width=8, height=8, corner_radius=4,
            fg_color=accent or theme.PRIMARY
        )
        dot.pack(side="left", padx=(0, theme.SP_SM))
        ctk.CTkLabel(
            self, text=text, font=theme.font("h2"), text_color=theme.TEXT
        ).pack(side="left")


class StatusBadge(ctk.CTkLabel):
    """Chip de estado plano con fondo suave y texto de color semántico."""
    def __init__(self, master, text: str, kind: str = "info", **kwargs):
        color, bg, _border = state_colors(kind)
        defaults = dict(
            text=text, font=theme.font("badge"),
            fg_color=bg, text_color=color,
            corner_radius=theme.RAD_MD, height=26, padx=14,
        )
        defaults.update(kwargs)
        super().__init__(master, **defaults)

    @classmethod
    def from_estado(cls, master, estado: str) -> "StatusBadge":
        """Crea el badge estándar de un envío según su campo 'estado'."""
        if estado == "exito":
            return cls(master, "✓ Exitoso", kind="success")
        return cls(master, "✕ Fallido", kind="danger")


class StatBox(ctk.CTkFrame):
    """Contador KPI (etiqueta pequeña + número grande) para monitores y reportes."""
    _ACCENTS = {
        "primary": theme.PRIMARY,
        "success": theme.SUCCESS,
        "danger": theme.DANGER,
        "warning": theme.WARNING,
        "info": theme.INFO,
    }

    def __init__(self, master, label: str, value: str = "0", accent: str = "primary"):
        super().__init__(
            master, corner_radius=theme.RAD_MD, fg_color=theme.SURFACE_ALT,
            border_width=1, border_color=theme.BORDER
        )
        ctk.CTkLabel(
            self, text=label, font=theme.font("badge"),
            text_color=theme.TEXT_MUTED
        ).pack(pady=(theme.SP_SM, 0))
        self.lbl_value = ctk.CTkLabel(
            self, text=value, font=theme.font("kpi"),
            text_color=self._ACCENTS.get(accent, theme.PRIMARY)
        )
        self.lbl_value.pack(pady=(0, theme.SP_SM))

    def set_value(self, value):
        self.lbl_value.configure(text=str(value))


class PrimaryButton(ctk.CTkButton):
    """Botón de acción principal (teal clínico)."""
    def __init__(self, master, **kwargs):
        defaults = dict(
            font=theme.font("body_strong"),
            fg_color=theme.BTN_PRIMARY_FG, hover_color=theme.BTN_PRIMARY_HOVER,
            text_color=theme.ON_PRIMARY, text_color_disabled=theme.ON_PRIMARY,
            height=theme.BTN_H, corner_radius=theme.RAD_MD,
        )
        defaults.update(kwargs)
        super().__init__(master, **defaults)


class SecondaryButton(ctk.CTkButton):
    """Botón neutro para acciones secundarias."""
    def __init__(self, master, **kwargs):
        defaults = dict(
            font=theme.font("body_strong"),
            fg_color=theme.BTN_SECONDARY_FG, hover_color=theme.BTN_SECONDARY_HOVER,
            text_color=theme.TEXT, text_color_disabled=theme.TEXT_MUTED,
            height=theme.BTN_H, corner_radius=theme.RAD_MD,
        )
        defaults.update(kwargs)
        super().__init__(master, **defaults)


class DangerButton(ctk.CTkButton):
    """Botón para acciones destructivas o de salida."""
    def __init__(self, master, **kwargs):
        defaults = dict(
            font=theme.font("body_strong"),
            fg_color=theme.BTN_DANGER_FG, hover_color=theme.BTN_DANGER_HOVER,
            text_color="#ffffff", text_color_disabled="#ffffff",
            height=theme.BTN_H, corner_radius=theme.RAD_MD,
        )
        defaults.update(kwargs)
        super().__init__(master, **defaults)


class WarningButton(ctk.CTkButton):
    """Botón ámbar sobrio para acciones de precaución (reintentos)."""
    def __init__(self, master, **kwargs):
        defaults = dict(
            font=theme.font("body_strong"),
            fg_color=theme.BTN_WARNING_FG, hover_color=theme.BTN_WARNING_HOVER,
            text_color="#ffffff", text_color_disabled="#ffffff",
            height=theme.BTN_H, corner_radius=theme.RAD_MD,
        )
        defaults.update(kwargs)
        super().__init__(master, **defaults)


class GhostNavButton(ctk.CTkButton):
    """Botón de navegación del sidebar con estado activo/inactivo."""
    def __init__(self, master, **kwargs):
        defaults = dict(
            font=theme.font("body_strong"),
            fg_color="transparent", text_color=theme.TEXT_SECONDARY,
            hover_color=theme.SIDEBAR_ACTIVE,
            anchor="w", height=42, corner_radius=theme.RAD_MD, border_spacing=10,
        )
        defaults.update(kwargs)
        super().__init__(master, **defaults)

    def set_active(self, active: bool):
        if active:
            self.configure(fg_color=theme.SIDEBAR_ACTIVE, text_color=theme.PRIMARY)
        else:
            self.configure(fg_color="transparent", text_color=theme.TEXT_SECONDARY)


class ThemedEntry(ctk.CTkEntry):
    """Campo de entrada con la superficie y borde del tema."""
    def __init__(self, master, **kwargs):
        defaults = dict(
            font=theme.font("body"), height=theme.INPUT_H,
            fg_color=theme.SURFACE_ALT, border_color=theme.BORDER,
            text_color=theme.TEXT, placeholder_text_color=theme.TEXT_MUTED,
        )
        defaults.update(kwargs)
        super().__init__(master, **defaults)


class ThemedTextbox(ctk.CTkTextbox):
    """Caja de texto multilínea con la superficie y borde del tema."""
    def __init__(self, master, **kwargs):
        defaults = dict(
            font=theme.font("body"),
            fg_color=theme.SURFACE_ALT, border_color=theme.BORDER,
            text_color=theme.TEXT,
            border_width=1, corner_radius=theme.RAD_SM,
        )
        defaults.update(kwargs)
        super().__init__(master, **defaults)


def apply_window_icon(window):
    """Asigna el icono de la app a una ventana.

    En CTkToplevel el icono debe reaplicarse con retardo (varias veces, por
    robustez): CustomTkinter restablece su icono por defecto ~200 ms después
    de crear el toplevel.
    """
    if not os.path.exists(theme.ICON_PATH):
        return
    try:
        window.iconbitmap(theme.ICON_PATH)
        if isinstance(window, ctk.CTkToplevel):
            for delay in (250, 600, 1200):
                window.after(delay, lambda: _reapply_icon(window))
    except Exception:
        pass


def _reapply_icon(window):
    try:
        if window.winfo_exists():
            window.iconbitmap(theme.ICON_PATH)
    except Exception:
        pass


def center_window(window, width: int, height: int, min_w: int = None, min_h: int = None):
    """Centra la ventana en pantalla ajustando el tamaño al espacio disponible.

    En pantallas pequeñas o con escalado DPI alto reduce el tamaño solicitado
    para que la ventana nunca exceda el área visible.
    """
    window.update_idletasks()
    screen_w = window.winfo_screenwidth()
    screen_h = window.winfo_screenheight()
    # Margen para barra de tareas y bordes del sistema
    width = min(width, screen_w - 80)
    height = min(height, screen_h - 120)
    x = max((screen_w - width) // 2, 0)
    y = max((screen_h - height) // 2 - 20, 0)
    window.geometry(f"{width}x{height}+{x}+{y}")
    if min_w and min_h:
        window.minsize(min(min_w, width), min(min_h, height))
