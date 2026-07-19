import customtkinter as ctk
import re
from src.ui import theme, dialogs
from src.ui.components import (
    StatBox, PrimaryButton, SecondaryButton, WarningButton,
    apply_window_icon, center_window, state_colors,
)

class ResultsModal(ctk.CTkToplevel):
    """Modal modular y visual para el Reporte de Errores y Reintentos."""
    def __init__(self, parent, errores, total, records_fallidos, email_corrections=None, on_retry=None, on_correct_and_retry=None, pdf_corrections=None):
        super().__init__(parent)

        if email_corrections is None:
            email_corrections = {}
        if pdf_corrections is None:
            pdf_corrections = {}

        self.errores = errores
        self.total = total
        self.records_fallidos = records_fallidos
        self.email_corrections = email_corrections
        self.pdf_corrections = pdf_corrections
        self.on_retry = on_retry
        self.on_correct_and_retry = on_correct_and_retry
        self._is_retrying = False

        self.title("Reporte de Envíos — SEMS Pro")
        center_window(self, 650, 680, min_w=580, min_h=560)
        self.resizable(True, True)
        self.transient(parent)
        self.grab_set()
        self.configure(fg_color=theme.APP_BG)
        apply_window_icon(self)

        self.protocol("WM_DELETE_WINDOW", self.safe_close_modal)
        self.setup_ui()

    def safe_close_modal(self):
        if self.records_fallidos and not self._is_retrying:
            confirm = dialogs.ask_yes_no(
                self,
                "Confirmar Cierre",
                "¿Estás seguro de que deseas cerrar el reporte?\n\n"
                "Los envíos fallidos de este lote solo podrán ser reintentados desde la pestaña 'Historial de Auditoría' mientras la aplicación siga abierta."
            )
            if not confirm:
                return
        try:
            self.master.focus_set()
            self.destroy()
        except Exception:
            pass

    def setup_ui(self):
        # 1. Icono circular de alerta (gráfico propio, sin depender de emojis)
        icon_container = ctk.CTkFrame(
            self, width=60, height=60, corner_radius=30,
            fg_color=theme.WARNING_BG,
            border_width=2,
            border_color=theme.WARNING_BORDER
        )
        icon_container.pack(pady=(25, 2))
        icon_container.pack_propagate(False)

        lbl_icon = ctk.CTkLabel(
            icon_container, text="!",
            font=ctk.CTkFont(family=theme.FONT_FAMILY, size=30, weight="bold"),
            text_color=theme.WARNING
        )
        lbl_icon.place(relx=0.5, rely=0.5, anchor="center")

        # Título en color de texto normal: el icono ámbar ya comunica la alerta
        # sin que todo el encabezado compita en saturación con el resto de la UI.
        self.lbl_title = ctk.CTkLabel(
            self, text="Atención Requerida",
            font=theme.font("h1"),
            text_color=theme.TEXT
        )
        self.lbl_title.pack(pady=(2, 10))

        exitosos = self.total - len(self.errores)

        # 2. Rejilla de contadores KPI
        stats_frame = ctk.CTkFrame(self, fg_color="transparent")
        stats_frame.pack(fill="x", padx=30, pady=(10, 15))
        stats_frame.grid_columnconfigure((0, 1, 2), weight=1)

        StatBox(stats_frame, "Procesados", value=str(self.total), accent="primary").grid(row=0, column=0, padx=6, sticky="nsew")
        StatBox(stats_frame, "Éxitos", value=str(exitosos), accent="success").grid(row=0, column=1, padx=6, sticky="nsew")
        StatBox(stats_frame, "Fallidos", value=str(len(self.errores)), accent="danger").grid(row=0, column=2, padx=6, sticky="nsew")

        # 3. Aviso de correcciones automáticas disponibles
        if self.email_corrections or self.pdf_corrections:
            card_fix = ctk.CTkFrame(
                self, corner_radius=theme.RAD_MD,
                fg_color=theme.WARNING_BG,
                border_width=1,
                border_color=theme.WARNING_BORDER
            )
            card_fix.pack(fill="x", padx=30, pady=(0, 15))

            fix_count = len(self.email_corrections) + len(self.pdf_corrections)
            ctk.CTkLabel(
                card_fix,
                text=f"Se detectaron {fix_count} sugerencia(s) de corrección automática.",
                font=theme.font("body_strong"),
                text_color=theme.WARNING,
                justify="center"
            ).pack(padx=20, pady=(10, 0), fill="x")
            ctk.CTkLabel(
                card_fix,
                text="Presione 'Corregir y Reintentar' para auto-repararlos e iniciar el reenvío.",
                font=theme.font("body"),
                text_color=theme.TEXT_SECONDARY,
                justify="center"
            ).pack(padx=20, pady=(0, 10), fill="x")

        # 4. Listado scrollable de errores en tarjetas
        lbl_list_title = ctk.CTkLabel(self, text="Detalle de Fallos Encontrados:", font=theme.font("h2"), text_color=theme.TEXT)
        lbl_list_title.pack(anchor="w", padx=35, pady=(0, 8))

        # 5. Barra inferior de botones: se empaqueta primero con side="bottom" para
        # reservar su altura completa; si falta espacio vertical (pantallas cortas
        # o escalado DPI alto), se encoge la lista scrollable, nunca los botones.
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(side="bottom", fill="x", padx=30, pady=(5, 20))

        self.btn_copy = SecondaryButton(
            btn_frame, text="Copiar Reporte", command=self.copy_to_clipboard,
            width=140, height=45
        )
        self.btn_copy.pack(side="left", padx=5, expand=True)

        if self.email_corrections or self.pdf_corrections:
            self.btn_correct = PrimaryButton(
                btn_frame, text="Corregir y Reintentar", command=self.handle_correct_and_retry,
                width=200, height=45
            )
            self.btn_correct.pack(side="left", padx=5, expand=True)

        if self.records_fallidos:
            self.btn_retry = WarningButton(
                btn_frame, text="Reintentar Fallidos", command=self.handle_retry,
                width=160, height=45
            )
            self.btn_retry.pack(side="right", padx=5, expand=True)

        self.scroll_frame = ctk.CTkScrollableFrame(
            self, height=210, fg_color="transparent",
            border_width=0
        )
        self.scroll_frame.pack(fill="both", expand=True, padx=25, pady=(0, 15))

        # Poblar lista de errores estructurados
        for err_str in self.errores:
            self._render_error_card(err_str)

    def _classify_error(self, detail_lower, is_suggestion):
        """Clasifica la naturaleza del fallo y devuelve (texto del badge, tipo semántico)."""
        if "no encontrado" in detail_lower or "pdf" in detail_lower:
            if is_suggestion:
                return "PDF SUGERIDO", "info"
            return "PDF FALTANTE", "warning"
        if "typo" in detail_lower or "quisiste decir" in detail_lower or is_suggestion:
            return "SUGERENCIA", "warning"
        if "servidores" in detail_lower or "dominio" in detail_lower or "dns" in detail_lower:
            return "DOMINIO INVÁLIDO", "danger"
        if "conexión" in detail_lower or "smtp" in detail_lower or "timeout" in detail_lower:
            return "ERROR SMTP", "info"
        return "FALLO", "danger"

    def _render_error_card(self, err_str):
        """Renderiza una tarjeta visual e individual para cada error."""
        card = ctk.CTkFrame(
            self.scroll_frame, corner_radius=theme.RAD_MD,
            fg_color=theme.SURFACE,
            border_width=1, border_color=theme.BORDER
        )
        card.pack(fill="x", pady=6, padx=5, ipady=6)
        card.grid_columnconfigure(0, weight=1)

        # Intentar parsear el formato "email: detalle"
        email_part = "Fallo General"
        detail_part = err_str

        if ":" in err_str:
            parts = err_str.split(":", 1)
            if "@" in parts[0]:
                email_part = parts[0].strip()
                detail_part = parts[1].strip()

        detail_lower = detail_part.lower()
        sug_match = re.search(r'\(sugerencia:\s*([^)]+)\)', detail_lower)
        is_suggestion = bool(sug_match)
        suggestion_val = sug_match.group(1).strip() if sug_match else ""

        badge_text, kind = self._classify_error(detail_lower, is_suggestion)
        # Tuplas (claro, oscuro) directas: el badge reacciona al cambio de modo en vivo
        text_color, badge_bg, badge_border = state_colors(kind)

        # 1. Header de la tarjeta (email del destinatario + badge contorneado)
        header_frame = ctk.CTkFrame(card, fg_color="transparent")
        header_frame.pack(fill="x", padx=15, pady=(8, 2))

        lbl_email = ctk.CTkLabel(
            header_frame, text=email_part,
            font=theme.font("body_strong"),
            text_color=theme.TEXT
        )
        lbl_email.pack(side="left")

        badge_frame = ctk.CTkFrame(
            header_frame, corner_radius=6,
            fg_color=badge_bg,
            border_width=1,
            border_color=badge_border
        )
        badge_frame.pack(side="right")

        lbl_badge = ctk.CTkLabel(
            badge_frame, text=badge_text,
            font=ctk.CTkFont(family=theme.FONT_FAMILY, size=9, weight="bold"),
            text_color=text_color,
            padx=10, pady=2
        )
        lbl_badge.pack()

        # 2. Contenido descriptivo del fallo
        content_frame = ctk.CTkFrame(card, fg_color="transparent")
        content_frame.pack(fill="x", padx=15, pady=(2, 6))

        clean_detail = re.sub(r'\(sugerencia:.*?\)', '', detail_part, flags=re.IGNORECASE).strip()

        if is_suggestion and suggestion_val:
            is_pdf = "pdf" in detail_lower or "no encontrado" in detail_lower
            desc_text = "El archivo PDF no fue encontrado con el nombre exacto especificado." if is_pdf else "El dominio ingresado contiene un error de ortografía común."

            lbl_desc = ctk.CTkLabel(
                content_frame,
                text=desc_text,
                font=theme.font("body"), text_color=theme.TEXT_SECONDARY,
                justify="left", anchor="w"
            )
            lbl_desc.pack(anchor="w", pady=(0, 4))

            # Pill de sugerencia encajada al contenido
            sug_frame = ctk.CTkFrame(
                content_frame, corner_radius=theme.RAD_SM,
                fg_color=theme.SUCCESS_BG,
                border_width=1, border_color=theme.SUCCESS_BORDER
            )
            sug_frame.pack(anchor="w", pady=(4, 2), padx=2)

            pill_text = f"¿Usar: {suggestion_val}?" if is_pdf else f"¿Quisiste decir: {suggestion_val}?"
            lbl_sug_text = ctk.CTkLabel(
                sug_frame,
                text=pill_text,
                font=theme.font("body_strong"),
                text_color=theme.SUCCESS,
                padx=12, pady=4
            )
            lbl_sug_text.pack()
        else:
            lbl_desc = ctk.CTkLabel(
                content_frame, text=clean_detail,
                font=theme.font("body"), text_color=theme.TEXT_SECONDARY,
                justify="left", anchor="w", wraplength=540
            )
            lbl_desc.pack(anchor="w", fill="x")

    def copy_to_clipboard(self):
        self.clipboard_clear()
        raw_report = "--- REPORTE DE ERRORES SEMS PRO ---\n\n"
        raw_report += "\n".join(self.errores)
        self.clipboard_append(raw_report)
        dialogs.show_success(self, "Copiado", "El reporte ha sido copiado al portapapeles.")

    def handle_correct_and_retry(self):
        if self.on_correct_and_retry:
            self._is_retrying = True
            self.btn_correct.configure(state="disabled", text="Corrigiendo...", fg_color=theme.BTN_DISABLED_FG)
            self.btn_copy.configure(state="disabled")
            if hasattr(self, 'btn_retry'):
                self.btn_retry.configure(state="disabled")
            self.lbl_title.configure(text="Aplicando correcciones...", text_color=theme.TEXT_MUTED)
            self.on_correct_and_retry()
            self.safe_close_modal()

    def handle_retry(self):
        if self.on_retry:
            self._is_retrying = True
            self.btn_retry.configure(state="disabled", text="Reintentando...", fg_color=theme.BTN_DISABLED_FG)
            self.btn_copy.configure(state="disabled")
            if hasattr(self, 'btn_correct'):
                self.btn_correct.configure(state="disabled")
            self.lbl_title.configure(text="Reintentando envios...", text_color=theme.TEXT_MUTED)
            self.on_retry()
            self.safe_close_modal()
