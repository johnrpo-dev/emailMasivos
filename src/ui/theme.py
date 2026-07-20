# pyrefly: ignore [missing-import]
"""Tema visual clínico de SEMS Pro.

Fuente única de verdad de colores, tipografías, espaciados y radios de la UI.
Todos los tokens de color son tuplas (modo claro, modo oscuro) compatibles con
CustomTkinter. La paleta usa un teal sanitario como color de marca y neutros
azul-pizarra fríos; los pares texto/superficie cumplen contraste WCAG AA o superior.
"""
import os
import sys
import customtkinter as ctk

# ============================================================
# Apariencia por defecto
# ============================================================
# Modo claro por defecto: entorno de laboratorio clínico (el usuario puede
# alternar a oscuro con el conmutador del sidebar).
DEFAULT_APPEARANCE = "light"

# ============================================================
# Superficies
# ============================================================
APP_BG         = ("#f7fafb", "#0b1120")   # fondo general de ventana
SURFACE        = ("#ffffff", "#101a2c")   # cards
SURFACE_ALT    = ("#f8fafc", "#0a1120")   # inputs, cajas internas, consola
SIDEBAR_BG     = ("#eef4f6", "#0e1626")
SIDEBAR_ACTIVE = ("#dcebe9", "#12324a")   # ítem de navegación activo
BORDER         = ("#dde6ec", "#1f2d45")
BORDER_STRONG  = ("#c3d2dc", "#2c3d5c")

# ============================================================
# Texto
# ============================================================
TEXT           = ("#0f2534", "#e8f0f7")
TEXT_SECONDARY = ("#46606f", "#9db1c4")
TEXT_MUTED     = ("#5f7787", "#7d90a8")   # solo captions/placeholders

# ============================================================
# Marca / primario (teal clínico)
# ============================================================
PRIMARY           = ("#0f766e", "#2dd4bf")   # acento como texto/detalle
PRIMARY_HOVER     = ("#115e59", "#14b8a6")
BTN_PRIMARY_FG    = ("#0f766e", "#14b8a6")   # relleno de botón primario
BTN_PRIMARY_HOVER = ("#0d5f58", "#0d9488")
ON_PRIMARY        = ("#ffffff", "#04201d")   # texto sobre botón primario
PRIMARY_SOFT      = ("#e4f4f2", "#0f2a2e")   # fondos suaves de marca

# ============================================================
# Estados (color de texto / fondo suave / borde)
# ============================================================
SUCCESS        = ("#15803d", "#4ade80")
SUCCESS_BG     = ("#e7f6ee", "#0d2b1c")
SUCCESS_BORDER = ("#b5e3c8", "#1e5637")

DANGER         = ("#b91c1c", "#f87171")
DANGER_BG      = ("#fdecec", "#331a1e")
DANGER_BORDER  = ("#f3c1c1", "#7a2e2e")

WARNING        = ("#a16207", "#facc15")
WARNING_BG     = ("#fdf6e3", "#2b2108")
WARNING_BORDER = ("#ecd9a0", "#6d5410")

INFO           = ("#0369a1", "#7dd3fc")
INFO_BG        = ("#e8f4fc", "#0c2438")
INFO_BORDER    = ("#b3dcf5", "#1c4d70")

# ============================================================
# Botones secundario y de peligro
# ============================================================
BTN_SECONDARY_FG    = ("#e9eff4", "#1c2a42")
BTN_SECONDARY_HOVER = ("#dbe5ec", "#26375a")

BTN_DANGER_FG    = ("#b91c1c", "#dc2626")
BTN_DANGER_HOVER = ("#991b1b", "#b91c1c")

# Botón de advertencia (reintentos): ámbar sobrio, no amarillo brillante,
# para no competir con la jerarquía del botón primario.
BTN_WARNING_FG    = ("#a16207", "#b45309")
BTN_WARNING_HOVER = ("#854d0e", "#92400e")

BTN_DISABLED_FG = ("#c8d4dc", "#22304a")   # estado deshabilitado de cualquier botón

# ============================================================
# Otros
# ============================================================
PROGRESS_FG   = BTN_PRIMARY_FG
PROGRESS_BG   = ("#dde6ec", "#1f2d45")

# Consola de logs: estilo terminal, oscura en ambos modos para máxima legibilidad
CONSOLE_BG     = ("#0f2534", "#040810")
CONSOLE_TEXT   = ("#d3e4ef", "#b8cddd")
CONSOLE_BORDER = ("#0f2534", "#1f2d45")

# ============================================================
# Espaciados, radios y dimensiones
# ============================================================
SP_XS, SP_SM, SP_MD, SP_LG, SP_XL = 4, 8, 12, 20, 28
RAD_SM, RAD_MD, RAD_LG = 8, 12, 16
INPUT_H = 36
BTN_H = 44
BTN_SM_H = 32

# Icono de la aplicación. En el exe congelado con PyInstaller los recursos
# viven bajo sys._MEIPASS; en desarrollo, en la raíz del repo (relativa a este archivo).
if getattr(sys, "frozen", False):
    _BASE_DIR = getattr(sys, "_MEIPASS", os.path.dirname(sys.executable))
else:
    _BASE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")
ICON_PATH = os.path.normpath(os.path.join(_BASE_DIR, "img", "iconoSems.ico"))

# ============================================================
# Tipografía (fábrica cacheada)
# ============================================================
FONT_FAMILY = "Segoe UI"
FONT_MONO = "Consolas"

_FONT_SPECS = {
    "display":     dict(size=26, weight="bold"),    # héroe de modales
    "h1":          dict(size=22, weight="bold"),    # título de vista
    "h2":          dict(size=15, weight="bold"),    # título de card/sección
    "kpi":         dict(size=26, weight="bold"),    # números de contadores
    "body_strong": dict(size=13, weight="bold"),    # labels de formulario, botones
    "body":        dict(size=13),                   # texto de cuerpo
    "caption":     dict(size=11),                   # metadatos, hints
    "badge":       dict(size=11, weight="bold"),    # badges/chips
    "status":      dict(size=13, slant="italic"),   # línea de estado
    "mono":        dict(family=FONT_MONO, size=12), # consola de logs
}

_font_cache = {}


def font(role: str) -> ctk.CTkFont:
    """Devuelve la CTkFont del rol tipográfico dado, cacheada por rol.

    Requiere un root de Tk activo (CTkFont queda ligado al root vigente al
    crearse); ver reset_font_cache() para el cambio de root.
    """
    if role not in _font_cache:
        spec = dict(_FONT_SPECS[role])
        family = spec.pop("family", FONT_FAMILY)
        _font_cache[role] = ctk.CTkFont(family=family, **spec)
    return _font_cache[role]


def reset_font_cache():
    """Vacía el caché de fuentes.

    Obligatorio al cambiar de root Tk (p. ej. tras cerrar ActivationModal y
    antes de construir App): las fuentes cacheadas del root destruido
    provocarían TclError si se reutilizan.
    """
    _font_cache.clear()
