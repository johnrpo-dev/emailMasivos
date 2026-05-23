import customtkinter as ctk

class HomeView(ctk.CTkFrame):
    """Componente modular para la vista principal de Control y Monitoreo."""
    def __init__(self, parent, controller):
        super().__init__(parent, fg_color="transparent")
        self.controller = controller
        
        # Tipografías del controller
        self.font_title = controller.font_title
        self.font_label = controller.font_label
        self.font_text = controller.font_text
        self.font_status = controller.font_status
        
        self.setup_layout()
        
    def setup_layout(self):
        # Header
        lbl_title = ctk.CTkLabel(self, text="Panel de Control", font=self.font_title, text_color=("#0f172a", "#f8fafc"))
        lbl_title.pack(anchor="w", pady=(0, 2))
        
        lbl_subtitle = ctk.CTkLabel(self, text="Configure y ejecute envíos masivos de forma segura e instantánea", font=ctk.CTkFont(family="Segoe UI", size=13), text_color=("#64748b", "#94a3b8"))
        lbl_subtitle.pack(anchor="w", pady=(0, 20))
        
        # Card 1: Archivos (Diseño Slate Premium con bordes)
        card_archivos = ctk.CTkFrame(self, corner_radius=16, fg_color=("#ffffff", "#0e1322"), border_width=1, border_color=("#e2e8f0", "#1e293b"))
        card_archivos.pack(fill="x", pady=(0, 20), ipady=5)
        card_archivos.grid_columnconfigure(1, weight=1)
        
        ctk.CTkLabel(card_archivos, text="📂 Archivo de Datos (CSV):", font=self.font_label, text_color=("#334155", "#cbd5e1")).grid(row=0, column=0, padx=20, pady=(20,10), sticky="w")
        ctk.CTkEntry(card_archivos, textvariable=self.controller.csv_path, font=self.font_text, height=36, fg_color=("#f8fafc", "#070a13"), border_color=("#cbd5e1", "#1e293b")).grid(row=0, column=1, padx=(0, 10), pady=(20,10), sticky="ew")
        ctk.CTkButton(card_archivos, text="Examinar", font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"), width=100, height=36, fg_color=("#4f46e5", "#6366f1"), hover_color=("#4338ca", "#4f46e5"), command=self.controller.browse_csv).grid(row=0, column=2, padx=20, pady=(20,10))
        
        ctk.CTkLabel(card_archivos, text="📄 Directorio de PDFs:", font=self.font_label, text_color=("#334155", "#cbd5e1")).grid(row=1, column=0, padx=20, pady=(10,20), sticky="w")
        ctk.CTkEntry(card_archivos, textvariable=self.controller.pdf_dir, font=self.font_text, height=36, fg_color=("#f8fafc", "#070a13"), border_color=("#cbd5e1", "#1e293b")).grid(row=1, column=1, padx=(0, 10), pady=(10,20), sticky="ew")
        ctk.CTkButton(card_archivos, text="Examinar", font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"), width=100, height=36, fg_color=("#4f46e5", "#6366f1"), hover_color=("#4338ca", "#4f46e5"), command=self.controller.browse_pdf_dir).grid(row=1, column=2, padx=20, pady=(10,20))
        
        # Card 2: Status & Progreso (Fina y elegante)
        card_status = ctk.CTkFrame(self, corner_radius=16, fg_color=("#ffffff", "#0e1322"), border_width=1, border_color=("#e2e8f0", "#1e293b"))
        card_status.pack(fill="x", pady=(0, 20), ipady=5)
        
        self.progress_bar = ctk.CTkProgressBar(card_status, height=12, progress_color=("#10b981", "#34d399"), fg_color=("#cbd5e1", "#1e293b"))
        self.progress_bar.pack(fill="x", padx=25, pady=(20, 10))
        self.progress_bar.set(0)
        
        self.lbl_status = ctk.CTkLabel(card_status, text="Listo para iniciar...", font=self.font_status, text_color=("#64748b", "#94a3b8"))
        self.lbl_status.pack(pady=(0, 12))
        
        # Frame para botones de acción (Iniciar y Vista Previa)
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(pady=(0, 20), fill="x")
        btn_frame.grid_columnconfigure(0, weight=1)
        btn_frame.grid_columnconfigure(1, weight=1)
        
        # Botón Vista Previa
        self.btn_preview = ctk.CTkButton(
            btn_frame, text="🔍 VISTA PREVIA", font=ctk.CTkFont(family="Segoe UI", size=15, weight="bold"),
            fg_color=("#3b82f6", "#2563eb"), hover_color=("#2563eb", "#1d4ed8"), text_color_disabled="#ffffff", height=48, corner_radius=12,
            command=self.controller.show_preview
        )
        self.btn_preview.grid(row=0, column=0, padx=(0, 10), sticky="ew")
        
        # Botón Iniciar
        self.btn_start = ctk.CTkButton(
            btn_frame, text="▶ INICIAR PROCESO", font=ctk.CTkFont(family="Segoe UI", size=15, weight="bold"),
            fg_color=("#10b981", "#059669"), hover_color=("#059669", "#047857"), text_color_disabled="#ffffff", height=48, corner_radius=12,
            command=self.controller.start_process
        )
        self.btn_start.grid(row=0, column=1, padx=(10, 0), sticky="ew")
        
        # === PANEL DE MONITOREO EN TIEMPO REAL ===
        self.card_monitor = ctk.CTkFrame(self, corner_radius=16, fg_color=("#ffffff", "#0e1322"), border_width=1, border_color=("#e2e8f0", "#1e293b"))
        self.card_monitor.pack(fill="both", expand=True, pady=(0, 10))
        
        # Sub-título del monitor
        lbl_mon_title = ctk.CTkLabel(self.card_monitor, text="📊 Monitor de Operación en Tiempo Real", font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"), text_color=("#334155", "#cbd5e1"))
        lbl_mon_title.pack(anchor="w", padx=20, pady=(15, 10))
        
        # Grid de Contadores (Total, Exitosos, Fallidos)
        stats_grid = ctk.CTkFrame(self.card_monitor, fg_color="transparent")
        stats_grid.pack(fill="x", padx=15, pady=(0, 10))
        stats_grid.grid_columnconfigure((0, 1, 2), weight=1)
        
        # Caja 1: Total
        box_total = ctk.CTkFrame(stats_grid, corner_radius=10, fg_color=("#f1f5f9", "#070a13"), border_width=1, border_color=("#e2e8f0", "#1e293b"))
        box_total.grid(row=0, column=0, padx=5, pady=5, sticky="nsew")
        ctk.CTkLabel(box_total, text="Total Registros", font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"), text_color=("#475569", "#94a3b8")).pack(pady=(8, 2))
        self.lbl_mon_total_val = ctk.CTkLabel(box_total, text="0", font=ctk.CTkFont(family="Segoe UI", size=24, weight="bold"), text_color=("#4f46e5", "#818cf8"))
        self.lbl_mon_total_val.pack(pady=(0, 8))
        
        # Caja 2: Exitosos
        box_success = ctk.CTkFrame(stats_grid, corner_radius=10, fg_color=("#f1f5f9", "#070a13"), border_width=1, border_color=("#e2e8f0", "#1e293b"))
        box_success.grid(row=0, column=1, padx=5, pady=5, sticky="nsew")
        ctk.CTkLabel(box_success, text="Enviados", font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"), text_color=("#475569", "#94a3b8")).pack(pady=(8, 2))
        self.lbl_mon_success_val = ctk.CTkLabel(box_success, text="0", font=ctk.CTkFont(family="Segoe UI", size=24, weight="bold"), text_color=("#10b981", "#34d399"))
        self.lbl_mon_success_val.pack(pady=(0, 8))
        
        # Caja 3: Fallidos
        box_failed = ctk.CTkFrame(stats_grid, corner_radius=10, fg_color=("#f1f5f9", "#070a13"), border_width=1, border_color=("#e2e8f0", "#1e293b"))
        box_failed.grid(row=0, column=2, padx=5, pady=5, sticky="nsew")
        ctk.CTkLabel(box_failed, text="Fallidos", font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"), text_color=("#475569", "#94a3b8")).pack(pady=(8, 2))
        self.lbl_mon_failed_val = ctk.CTkLabel(box_failed, text="0", font=ctk.CTkFont(family="Segoe UI", size=24, weight="bold"), text_color=("#ef4444", "#f87171"))
        self.lbl_mon_failed_val.pack(pady=(0, 8))
        
        # Consola de logs en tiempo real
        self.txt_console = ctk.CTkTextbox(self.card_monitor, height=80, font=ctk.CTkFont(family="Consolas", size=11), corner_radius=10, fg_color=("#f8fafc", "#070a13"), text_color=("#334155", "#94a3b8"), border_width=1, border_color=("#e2e8f0", "#1e293b"))
        self.txt_console.pack(fill="both", expand=True, padx=20, pady=(0, 15))
        self.txt_console.insert("0.0", ">>> Sistema listo. Esperando inicio de proceso...\n")
        self.txt_console.configure(state="disabled")

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
                self.lbl_mon_total_val.configure(text=str(total))
            if success is not None:
                self.lbl_mon_success_val.configure(text=str(success))
            if failed is not None:
                self.lbl_mon_failed_val.configure(text=str(failed))
        except Exception:
            pass
