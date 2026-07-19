import customtkinter as ctk
from src.ui import theme
from src.ui.components import (
    Card, SectionHeader, CardTitle, StatBox,
    PrimaryButton, SecondaryButton, ThemedEntry, ThemedTextbox,
)

class HomeView(ctk.CTkFrame):
    """Componente modular para la vista principal de Control y Monitoreo."""
    def __init__(self, parent, controller):
        super().__init__(parent, fg_color="transparent")
        self.controller = controller
        self.setup_layout()

    def setup_layout(self):
        # Header
        SectionHeader(
            self, "Panel de Control",
            "Configure y ejecute envíos masivos de forma segura e instantánea"
        ).pack(anchor="w", fill="x", pady=(0, theme.SP_LG))

        # Card 1: Archivos de entrada
        card_archivos = Card(self)
        card_archivos.pack(fill="x", pady=(0, theme.SP_LG), ipady=5)
        card_archivos.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(card_archivos, text="Archivo de datos (CSV):", font=theme.font("body_strong"), text_color=theme.TEXT).grid(row=0, column=0, padx=20, pady=(20, 10), sticky="w")
        ThemedEntry(card_archivos, textvariable=self.controller.csv_path).grid(row=0, column=1, padx=(0, 10), pady=(20, 10), sticky="ew")
        SecondaryButton(card_archivos, text="Examinar", width=100, height=theme.INPUT_H, command=self.controller.browse_csv).grid(row=0, column=2, padx=20, pady=(20, 10))

        ctk.CTkLabel(card_archivos, text="Directorio de PDFs:", font=theme.font("body_strong"), text_color=theme.TEXT).grid(row=1, column=0, padx=20, pady=(10, 20), sticky="w")
        ThemedEntry(card_archivos, textvariable=self.controller.pdf_dir).grid(row=1, column=1, padx=(0, 10), pady=(10, 20), sticky="ew")
        SecondaryButton(card_archivos, text="Examinar", width=100, height=theme.INPUT_H, command=self.controller.browse_pdf_dir).grid(row=1, column=2, padx=20, pady=(10, 20))

        # Card 2: Estado y progreso
        card_status = Card(self)
        card_status.pack(fill="x", pady=(0, theme.SP_LG), ipady=5)

        self.progress_bar = ctk.CTkProgressBar(card_status, height=12, progress_color=theme.PROGRESS_FG, fg_color=theme.PROGRESS_BG)
        self.progress_bar.pack(fill="x", padx=25, pady=(20, 10))
        self.progress_bar.set(0)

        self.lbl_status = ctk.CTkLabel(card_status, text="Listo para iniciar...", font=theme.font("status"), text_color=theme.TEXT_SECONDARY)
        self.lbl_status.pack(pady=(0, 12))

        # Botones de acción (Vista Previa e Iniciar)
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(pady=(0, theme.SP_LG), fill="x")
        btn_frame.grid_columnconfigure(0, weight=1)
        btn_frame.grid_columnconfigure(1, weight=1)

        self.btn_preview = SecondaryButton(
            btn_frame, text="VISTA PREVIA", height=48,
            command=self.controller.show_preview
        )
        self.btn_preview.grid(row=0, column=0, padx=(0, 10), sticky="ew")

        self.btn_start = PrimaryButton(
            btn_frame, text="INICIAR PROCESO", height=48,
            command=self.controller.start_process
        )
        self.btn_start.grid(row=0, column=1, padx=(10, 0), sticky="ew")

        # === PANEL DE MONITOREO EN TIEMPO REAL ===
        self.card_monitor = Card(self)
        self.card_monitor.pack(fill="both", expand=True, pady=(0, 10))

        CardTitle(self.card_monitor, "Monitor de operación en tiempo real").pack(anchor="w", padx=20, pady=(15, 10))

        # Grid de contadores (Total, Enviados, Fallidos)
        stats_grid = ctk.CTkFrame(self.card_monitor, fg_color="transparent")
        stats_grid.pack(fill="x", padx=15, pady=(0, 10))
        stats_grid.grid_columnconfigure((0, 1, 2), weight=1)

        self.stat_total = StatBox(stats_grid, "Total Registros", accent="primary")
        self.stat_total.grid(row=0, column=0, padx=5, pady=5, sticky="nsew")

        self.stat_success = StatBox(stats_grid, "Enviados", accent="success")
        self.stat_success.grid(row=0, column=1, padx=5, pady=5, sticky="nsew")

        self.stat_failed = StatBox(stats_grid, "Fallidos", accent="danger")
        self.stat_failed.grid(row=0, column=2, padx=5, pady=5, sticky="nsew")

        # Consola de logs en tiempo real
        self.txt_console = ThemedTextbox(
            self.card_monitor, height=80, font=theme.font("mono"),
            text_color=theme.CONSOLE_TEXT, corner_radius=theme.RAD_MD
        )
        self.txt_console.pack(fill="both", expand=True, padx=20, pady=(0, 15))
        self.txt_console.insert("0.0", ">>> Sistema listo. Esperando inicio de proceso...\n")
        self.txt_console.configure(state="disabled")

    def set_busy(self, busy: bool):
        """Habilita o deshabilita los botones de acción durante un proceso.

        Centraliza los colores de estado aquí para que el controller no
        manipule estilos de widgets directamente.
        """
        if busy:
            self.btn_start.configure(state="disabled", fg_color=theme.BTN_DISABLED_FG)
            self.btn_preview.configure(state="disabled", fg_color=theme.BTN_DISABLED_FG)
        else:
            self.btn_start.configure(state="normal", fg_color=theme.BTN_PRIMARY_FG)
            self.btn_preview.configure(state="normal", fg_color=theme.BTN_SECONDARY_FG)

    def update_ui_status(self, text, progress=None):
        self.lbl_status.configure(text=text)
        if progress is not None:
            self.progress_bar.set(progress)

    def add_console_log(self, text):
        try:
            self.txt_console.configure(state="normal")
            self.txt_console.insert("end", f">>> {text}\n")
            self.txt_console.see("end")
            self.txt_console.configure(state="disabled")
        except Exception:
            pass

    def update_monitor_stats(self, total=None, success=None, failed=None):
        try:
            if total is not None:
                self.stat_total.set_value(total)
            if success is not None:
                self.stat_success.set_value(success)
            if failed is not None:
                self.stat_failed.set_value(failed)
        except Exception:
            pass
