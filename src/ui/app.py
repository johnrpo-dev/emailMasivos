# pyrefly: ignore [missing-import]
import customtkinter as ctk
from tkinter import filedialog, messagebox
import os
import re
import threading
import subprocess
import secrets
import hmac
import hashlib
import tempfile
import glob
import atexit
from src.core.data_manager import DataManager
from src.config.config_manager import ConfigManager
from src.utils.logger import logger
from src.core.workflow_orchestrator import WorkflowOrchestrator


class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("SEMS Pro - Envíos Masivos")
        self.geometry("850x680")
        self.resizable(False, False)
        
        # Inicializar historial efímero en memoria RAM (Zero-Footprint)
        self.session_batches = []
        self._hmac_key = secrets.token_bytes(32)
        
        # Tema Global Premium
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        
        # Seguridad: Contador de reintentos para prevenir abuso de SMTP
        self._retry_count = 0
        self.MAX_RETRIES = 2
        
        # Variables de estado (Envío)
        default_pdf_dir = os.path.join(os.getcwd(), "data", "input")
        self.csv_path = ctk.StringVar()
        self.pdf_dir = ctk.StringVar(value=default_pdf_dir)
        
        # Variables de Configuración
        self.config_user = ctk.StringVar()
        self.config_pass = ctk.StringVar()
        self.config_subject = ctk.StringVar()
        
        # Proveedores SMTP preconfigurados
        self.smtp_providers = {
            "Gmail": {"host": "smtp.gmail.com", "port": 587},
            "Outlook / Hotmail": {"host": "smtp.office365.com", "port": 587},
            "Yahoo": {"host": "smtp.mail.yahoo.com", "port": 587},
            "Zoho": {"host": "smtp.zoho.com", "port": 587},
            "iCloud": {"host": "smtp.mail.me.com", "port": 587},
        }
        self.config_provider = ctk.StringVar(value="Gmail")
        
        # Tipografías base
        self.font_title = ctk.CTkFont(family="Segoe UI", size=26, weight="bold")
        self.font_label = ctk.CTkFont(family="Segoe UI", size=14, weight="bold")
        self.font_text = ctk.CTkFont(family="Segoe UI", size=13)
        self.font_status = ctk.CTkFont(family="Segoe UI", size=14, slant="italic")
        
        # Cargar config
        self.load_settings()
        self.setup_ui()
        
        # Seguridad: Manejar cierre de ventana para limpiar archivos temporales
        self.protocol("WM_DELETE_WINDOW", self._on_closing)
        atexit.register(self._emergency_cleanup_temp_files)
        
    def load_settings(self):
        config = ConfigManager.get_config()
        self.config_user.set(config.get("smtp_user", ""))
        self.config_pass.set(config.get("smtp_password", ""))
        self.config_subject.set(config.get("email_subject", ""))
        self.initial_body = config.get("email_body", "")
        
        # Detectar proveedor guardado por su host
        saved_host = config.get("smtp_host", "smtp.gmail.com")
        matched = False
        for name, data in self.smtp_providers.items():
            if data["host"] == saved_host:
                self.config_provider.set(name)
                matched = True
                break
        if not matched:
            self.config_provider.set("Gmail")

    def setup_ui(self):
        # Configurar grid principal (Sidebar + Content)
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        
        # Color de fondo de la ventana principal
        self.configure(fg_color=("#f8fafc", "#080c14"))
        
        # === SIDEBAR ===
        self.sidebar_frame = ctk.CTkFrame(self, width=230, corner_radius=0, fg_color=("#f1f5f9", "#0d111c"), border_width=0)
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(5, weight=1) # Empujar hacia arriba
        
        # Logo modernizado y premium
        lbl_logo = ctk.CTkLabel(
            self.sidebar_frame, 
            text="SEMS PRO", 
            font=ctk.CTkFont(family="Segoe UI", size=24, weight="bold"),
            text_color=("#4f46e5", "#818cf8")
        )
        lbl_logo.grid(row=0, column=0, padx=20, pady=(30, 5))
        
        lbl_logo_sub = ctk.CTkLabel(
            self.sidebar_frame, 
            text="ENVÍOS INTELIGENTES", 
            font=ctk.CTkFont(family="Segoe UI", size=9, weight="bold"),
            text_color=("#94a3b8", "#475569")
        )
        lbl_logo_sub.grid(row=0, column=0, padx=20, pady=(0, 30))
        
        self.btn_nav_home = ctk.CTkButton(
            self.sidebar_frame, text="🚀 Envío Masivo", font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
            fg_color="transparent", text_color=("#475569", "#94a3b8"), hover_color=("#cbd5e1", "#1e293b"),
            anchor="w", height=42, corner_radius=10, border_spacing=10, command=self.show_home
        )
        self.btn_nav_home.grid(row=1, column=0, padx=15, pady=6, sticky="ew")
        
        self.btn_nav_config = ctk.CTkButton(
            self.sidebar_frame, text="⚙️ Configuración", font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
            fg_color="transparent", text_color=("#475569", "#94a3b8"), hover_color=("#cbd5e1", "#1e293b"),
            anchor="w", height=42, corner_radius=10, border_spacing=10, command=self.show_config
        )
        self.btn_nav_config.grid(row=2, column=0, padx=15, pady=6, sticky="ew")
        
        self.btn_nav_history = ctk.CTkButton(
            self.sidebar_frame, text="📜 Historial", font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
            fg_color="transparent", text_color=("#475569", "#94a3b8"), hover_color=("#cbd5e1", "#1e293b"),
            anchor="w", height=42, corner_radius=10, border_spacing=10, command=self.show_history
        )
        self.btn_nav_history.grid(row=3, column=0, padx=15, pady=6, sticky="ew")
        
        # === CONTENIDO PRINCIPAL ===
        self.main_container = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.main_container.grid(row=0, column=1, sticky="nsew", padx=25, pady=25)
        self.main_container.grid_rowconfigure(0, weight=1)
        self.main_container.grid_columnconfigure(0, weight=1)
        
        # Crear frames de las vistas
        self.home_frame = ctk.CTkFrame(self.main_container, fg_color="transparent")
        self.config_frame = ctk.CTkFrame(self.main_container, fg_color="transparent")
        self.history_frame = ctk.CTkFrame(self.main_container, fg_color="transparent")
        
        self.setup_home_view()
        self.setup_config_view()
        self.setup_history_view()
        
        # Iniciar en Home
        self.show_home()
 
    def show_home(self):
        self.config_frame.grid_forget()
        self.history_frame.grid_forget()
        self.home_frame.grid(row=0, column=0, sticky="nsew")
        self.btn_nav_home.configure(fg_color=("#e2e8f0", "#1e293b"), text_color=("#4f46e5", "#818cf8"))
        self.btn_nav_config.configure(fg_color="transparent", text_color=("#475569", "#94a3b8"))
        self.btn_nav_history.configure(fg_color="transparent", text_color=("#475569", "#94a3b8"))
 
    def show_config(self):
        self.home_frame.grid_forget()
        self.history_frame.grid_forget()
        self.config_frame.grid(row=0, column=0, sticky="nsew")
        self.btn_nav_config.configure(fg_color=("#e2e8f0", "#1e293b"), text_color=("#4f46e5", "#818cf8"))
        self.btn_nav_home.configure(fg_color="transparent", text_color=("#475569", "#94a3b8"))
        self.btn_nav_history.configure(fg_color="transparent", text_color=("#475569", "#94a3b8"))
 
    def show_history(self):
        self.home_frame.grid_forget()
        self.config_frame.grid_forget()
        self.history_frame.grid(row=0, column=0, sticky="nsew")
        self.btn_nav_history.configure(fg_color=("#e2e8f0", "#1e293b"), text_color=("#4f46e5", "#818cf8"))
        self.btn_nav_home.configure(fg_color="transparent", text_color=("#475569", "#94a3b8"))
        self.btn_nav_config.configure(fg_color="transparent", text_color=("#475569", "#94a3b8"))
        self.load_history_batches()
        
    def setup_home_view(self):
        # Header
        lbl_title = ctk.CTkLabel(self.home_frame, text="Panel de Control", font=self.font_title, text_color=("#0f172a", "#f8fafc"))
        lbl_title.pack(anchor="w", pady=(0, 2))
        
        lbl_subtitle = ctk.CTkLabel(self.home_frame, text="Configure y ejecute envíos masivos de forma segura e instantánea", font=ctk.CTkFont(family="Segoe UI", size=13), text_color=("#64748b", "#94a3b8"))
        lbl_subtitle.pack(anchor="w", pady=(0, 20))
        
        # Card 1: Archivos (Diseño Slate Premium con bordes)
        card_archivos = ctk.CTkFrame(self.home_frame, corner_radius=16, fg_color=("#ffffff", "#0e1322"), border_width=1, border_color=("#e2e8f0", "#1e293b"))
        card_archivos.pack(fill="x", pady=(0, 20), ipady=5)
        card_archivos.grid_columnconfigure(1, weight=1)
        
        ctk.CTkLabel(card_archivos, text="📂 Archivo de Datos (CSV):", font=self.font_label, text_color=("#334155", "#cbd5e1")).grid(row=0, column=0, padx=20, pady=(20,10), sticky="w")
        ctk.CTkEntry(card_archivos, textvariable=self.csv_path, font=self.font_text, height=36, fg_color=("#f8fafc", "#070a13"), border_color=("#cbd5e1", "#1e293b")).grid(row=0, column=1, padx=(0, 10), pady=(20,10), sticky="ew")
        ctk.CTkButton(card_archivos, text="Examinar", font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"), width=100, height=36, fg_color=("#4f46e5", "#6366f1"), hover_color=("#4338ca", "#4f46e5"), command=self.browse_csv).grid(row=0, column=2, padx=20, pady=(20,10))
        
        ctk.CTkLabel(card_archivos, text="📄 Directorio de PDFs:", font=self.font_label, text_color=("#334155", "#cbd5e1")).grid(row=1, column=0, padx=20, pady=(10,20), sticky="w")
        ctk.CTkEntry(card_archivos, textvariable=self.pdf_dir, font=self.font_text, height=36, fg_color=("#f8fafc", "#070a13"), border_color=("#cbd5e1", "#1e293b")).grid(row=1, column=1, padx=(0, 10), pady=(10,20), sticky="ew")
        ctk.CTkButton(card_archivos, text="Examinar", font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"), width=100, height=36, fg_color=("#4f46e5", "#6366f1"), hover_color=("#4338ca", "#4f46e5"), command=self.browse_pdf_dir).grid(row=1, column=2, padx=20, pady=(10,20))
        
        # Card 2: Status & Progreso (Fina y elegante)
        card_status = ctk.CTkFrame(self.home_frame, corner_radius=16, fg_color=("#ffffff", "#0e1322"), border_width=1, border_color=("#e2e8f0", "#1e293b"))
        card_status.pack(fill="x", pady=(0, 20), ipady=5)
        
        self.progress_bar = ctk.CTkProgressBar(card_status, height=12, progress_color=("#10b981", "#34d399"), fg_color=("#cbd5e1", "#1e293b"))
        self.progress_bar.pack(fill="x", padx=25, pady=(20, 10))
        self.progress_bar.set(0)
        
        self.lbl_status = ctk.CTkLabel(card_status, text="Listo para iniciar...", font=self.font_status, text_color=("#64748b", "#94a3b8"))
        self.lbl_status.pack(pady=(0, 12))
        
        # Frame para botones de acción (Iniciar y Vista Previa)
        btn_frame = ctk.CTkFrame(self.home_frame, fg_color="transparent")
        btn_frame.pack(pady=(0, 20), fill="x")
        btn_frame.grid_columnconfigure(0, weight=1)
        btn_frame.grid_columnconfigure(1, weight=1)
        
        # Botón Vista Previa
        self.btn_preview = ctk.CTkButton(
            btn_frame, text="🔍 VISTA PREVIA", font=ctk.CTkFont(family="Segoe UI", size=15, weight="bold"),
            fg_color=("#3b82f6", "#2563eb"), hover_color=("#2563eb", "#1d4ed8"), text_color_disabled="#ffffff", height=48, corner_radius=12,
            command=self.show_preview
        )
        self.btn_preview.grid(row=0, column=0, padx=(0, 10), sticky="ew")
        
        # Botón Iniciar
        self.btn_start = ctk.CTkButton(
            btn_frame, text="▶ INICIAR PROCESO", font=ctk.CTkFont(family="Segoe UI", size=15, weight="bold"),
            fg_color=("#10b981", "#059669"), hover_color=("#059669", "#047857"), text_color_disabled="#ffffff", height=48, corner_radius=12,
            command=self.start_process
        )
        self.btn_start.grid(row=0, column=1, padx=(10, 0), sticky="ew")
        
        # === PANEL DE MONITOREO EN TIEMPO REAL (Uso del Espacio Vacío) ===
        self.card_monitor = ctk.CTkFrame(self.home_frame, corner_radius=16, fg_color=("#ffffff", "#0e1322"), border_width=1, border_color=("#e2e8f0", "#1e293b"))
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

    def add_console_log(self, text):
        def _update():
            try:
                self.txt_console.configure(state="normal")
                self.txt_console.insert("end", f">>> {text}\n")
                self.txt_console.see("end")
                self.txt_console.configure(state="disabled")
            except Exception as e:
                logger.debug(f"Error actualizando consola UI: {e}")
        self.after(0, _update)

    def update_monitor_stats(self, total=None, success=None, failed=None):
        def _update():
            try:
                if total is not None:
                    self.lbl_mon_total_val.configure(text=str(total))
                if success is not None:
                    self.lbl_mon_success_val.configure(text=str(success))
                if failed is not None:
                    self.lbl_mon_failed_val.configure(text=str(failed))
            except Exception as e:
                logger.debug(f"Error actualizando monitor UI: {e}")
        self.after(0, _update)


    def setup_config_view(self):
        lbl_title = ctk.CTkLabel(self.config_frame, text="Ajustes de Servidor SMTP", font=self.font_title, text_color=("#0f172a", "#f8fafc"))
        lbl_title.pack(anchor="w", pady=(0, 2))
        
        lbl_subtitle = ctk.CTkLabel(self.config_frame, text="Configure las credenciales SMTP de su proveedor y la plantilla de correo", font=ctk.CTkFont(family="Segoe UI", size=13), text_color=("#64748b", "#94a3b8"))
        lbl_subtitle.pack(anchor="w", pady=(0, 20))
        
        # Card Credenciales
        card_creds = ctk.CTkFrame(self.config_frame, corner_radius=16, fg_color=("#ffffff", "#0e1322"), border_width=1, border_color=("#e2e8f0", "#1e293b"))
        card_creds.pack(fill="x", pady=(0, 20), ipady=5)
        card_creds.grid_columnconfigure(1, weight=1)
        
        ctk.CTkLabel(card_creds, text="Correo Remitente:", font=self.font_label, text_color=("#334155", "#cbd5e1")).grid(row=0, column=0, padx=20, pady=(20, 10), sticky="w")
        ctk.CTkEntry(card_creds, textvariable=self.config_user, font=self.font_text, height=36, fg_color=("#f8fafc", "#070a13"), border_color=("#cbd5e1", "#1e293b"), placeholder_text="ej. ventas@empresa.com").grid(row=0, column=1, padx=20, pady=(20, 10), sticky="ew")
        
        ctk.CTkLabel(card_creds, text="Código de App:", font=self.font_label, text_color=("#334155", "#cbd5e1")).grid(row=1, column=0, padx=20, pady=(0, 10), sticky="w")
        ctk.CTkEntry(card_creds, textvariable=self.config_pass, show="*", font=self.font_text, height=36, fg_color=("#f8fafc", "#070a13"), border_color=("#cbd5e1", "#1e293b"), placeholder_text="Contraseña de 16 caracteres").grid(row=1, column=1, padx=20, pady=(0, 10), sticky="ew")
        
        ctk.CTkLabel(card_creds, text="Proveedor de Correo:", font=self.font_label, text_color=("#334155", "#cbd5e1")).grid(row=2, column=0, padx=20, pady=(0, 20), sticky="w")
        provider_menu = ctk.CTkOptionMenu(card_creds, variable=self.config_provider, values=list(self.smtp_providers.keys()), font=self.font_text, height=36, fg_color=("#4f46e5", "#6366f1"), button_color=("#4338ca", "#4f46e5"), button_hover_color=("#3730a3", "#4338ca"))
        provider_menu.grid(row=2, column=1, padx=20, pady=(0, 20), sticky="w")

        # Card Plantilla
        card_tpl = ctk.CTkFrame(self.config_frame, corner_radius=16, fg_color=("#ffffff", "#0e1322"), border_width=1, border_color=("#e2e8f0", "#1e293b"))
        card_tpl.pack(fill="both", expand=True, pady=(0, 20))
        card_tpl.grid_columnconfigure(1, weight=1)
        card_tpl.grid_rowconfigure(1, weight=1)
        
        ctk.CTkLabel(card_tpl, text="Asunto del Correo:", font=self.font_label, text_color=("#334155", "#cbd5e1")).grid(row=0, column=0, padx=20, pady=(20, 10), sticky="w")
        ctk.CTkEntry(card_tpl, textvariable=self.config_subject, font=self.font_text, height=36, fg_color=("#f8fafc", "#070a13"), border_color=("#cbd5e1", "#1e293b")).grid(row=0, column=1, padx=20, pady=(20, 10), sticky="ew")
        
        ctk.CTkLabel(card_tpl, text="Cuerpo del Correo:", font=self.font_label, text_color=("#334155", "#cbd5e1")).grid(row=1, column=0, padx=20, pady=(0, 20), sticky="nw")
        self.txt_body = ctk.CTkTextbox(card_tpl, font=self.font_text, fg_color=("#f8fafc", "#070a13"), border_color=("#cbd5e1", "#1e293b"), border_width=1, corner_radius=10)
        self.txt_body.grid(row=1, column=1, padx=20, pady=(0, 20), sticky="nsew")
        self.txt_body.insert("0.0", self.initial_body)
        
        btn_save = ctk.CTkButton(self.config_frame, text="💾 Guardar Configuración", font=ctk.CTkFont(family="Segoe UI", size=15, weight="bold"), fg_color=("#4f46e5", "#6366f1"), hover_color=("#4338ca", "#4f46e5"), height=48, corner_radius=12, command=self.save_settings)
        btn_save.pack(pady=0, fill="x")

    def browse_csv(self):
        filename = filedialog.askopenfilename(filetypes=[("CSV files", "*.csv")])
        if filename: self.csv_path.set(filename)
            
    def browse_pdf_dir(self):
        directory = filedialog.askdirectory()
        if directory: self.pdf_dir.set(directory)

    def save_settings(self):
        body = self.txt_body.get("0.0", "end").strip()
        provider = self.smtp_providers.get(self.config_provider.get(), {"host": "smtp.gmail.com", "port": 587})
        success = ConfigManager.save_config(
            self.config_user.get(), self.config_pass.get(),
            provider["host"], str(provider["port"]),
            self.config_subject.get(), body
        )
        if success:
            messagebox.showinfo("Éxito", "Configuración guardada correctamente.")
        else:
            messagebox.showerror("Error", "No se pudo guardar la configuración.")

    def start_process(self):
        # Seguridad: Reiniciar el contador de reintentos al iniciar un nuevo lote de envíos
        self._retry_count = 0
        
        if not self.csv_path.get() or not self.pdf_dir.get():
            messagebox.showwarning("Atención", "Selecciona el CSV y la carpeta de PDFs.")
            return
            
        config = ConfigManager.get_config()
        if not config.get("smtp_user") or not config.get("smtp_password"):
            messagebox.showwarning("Atención", "Ve a la pestaña de Configuración e ingresa tus credenciales SMTP primero.")
            return

        self.btn_start.configure(state="disabled", fg_color="#4b5563")
        self.btn_preview.configure(state="disabled", fg_color="#4b5563")
        self.progress_bar.set(0)
        self.lbl_status.configure(text="Procesando...")
        
        self._execute_workflow()
        
    def _execute_workflow(self, records_to_process=None):
        orchestrator = WorkflowOrchestrator()
        
        def on_batch_added(batch_record):
            def _add():
                batch_record["id"] = len(self.session_batches) + 1
                self.session_batches.append(batch_record)
            self.after(0, _add)

        def on_log(text):
            self.add_console_log(text)

        def on_progress(text, progress=None):
            self.after(0, lambda: self.update_ui_status(text, progress))

        def on_stats_update(total=None, success=None, failed=None):
            self.update_monitor_stats(total=total, success=success, failed=failed)

        def on_complete(errores, total, records_fallidos, email_corrections):
            def _complete():
                try:
                    exitosos_total = total - len(errores)
                    self.update_ui_status("¡Proceso masivo completado!", 1.0)
                    self.add_console_log(f"✓ COMPLETADO: {exitosos_total} exitosos, {len(errores)} fallidos.")
                    
                    if self.state() == "iconic":
                        self.show_desktop_notification(
                            "Envío Masivo Terminado",
                            f"El proceso ha finalizado. Éxitos: {exitosos_total}, Errores: {len(errores)}"
                        )
                    
                    if errores:
                        self.show_results_modal(errores, total, records_fallidos, email_corrections)
                    else:
                        messagebox.showinfo("Completado", "El proceso ha finalizado con éxito sin errores.")
                finally:
                    self.btn_start.configure(state="normal", fg_color=("#10b981", "#059669"))
                    self.btn_preview.configure(state="normal", fg_color=("#3b82f6", "#2563eb"))
            self.after(0, _complete)

        orchestrator.start(
            csv_path=self.csv_path.get(),
            pdf_dir=self.pdf_dir.get(),
            hmac_key=self._hmac_key,
            on_batch_added=on_batch_added,
            on_log=on_log,
            on_progress=on_progress,
            on_stats_update=on_stats_update,
            on_complete=on_complete,
            records_to_process=records_to_process
        )

    def update_ui_status(self, text, progress=None):
        self.lbl_status.configure(text=text)
        if progress is not None:
            self.progress_bar.set(progress)

    def show_desktop_notification(self, title, message):
        """Muestra una notificación de escritorio en Windows usando PowerShell nativo.
        
        Seguridad: Se sanitizan los parámetros para prevenir inyección de código PowerShell.
        Se eliminan caracteres peligrosos y se limita la longitud del texto.
        """
        try:
            # Seguridad (SEC-002): Lista blanca estricta de caracteres para prevenir command injection en PowerShell.
            # Se excluyen de forma garantizada comillas simples, dobles, backslashes y caracteres de escape.
            safe_title = re.sub(r"[^a-zA-Z0-9 .,!#@:_\-]", "", title)[:100]
            safe_message = re.sub(r"[^a-zA-Z0-9 .,!#@:_\-/]", "", message)[:250]
            
            ps_code = (
                '[void][System.Reflection.Assembly]::LoadWithPartialName("System.Windows.Forms");'
                '$n=New-Object System.Windows.Forms.NotifyIcon;'
                '$n.Icon=[System.Drawing.SystemIcons]::Information;'
                '$n.BalloonTipIcon="Info";'
                f'$n.BalloonTipText="{safe_message}";'
                f'$n.BalloonTipTitle="{safe_title}";'
                '$n.Visible=$True;'
                '$n.ShowBalloonTip(5000)'
            )
            subprocess.run(
                ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps_code],
                capture_output=True,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW,
                timeout=10  # Prevenir hang indefinido
            )
        except Exception as e:
            logger.warning(f"No se pudo mostrar la notificación de Windows: {str(e)}")

    def show_preview(self):
        if not self.csv_path.get():
            messagebox.showwarning("Atención", "Selecciona primero el archivo CSV de datos.")
            return
            
        try:
            records = DataManager.load_csv(self.csv_path.get())
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo cargar el CSV: {str(e)}")
            return
            
        if not records:
            messagebox.showwarning("Atención", "El archivo CSV está vacío.")
            return
            
        # Tomamos el primer registro como prueba
        record = records[0]
        email = str(record.get("email", "")).strip()
        id_archivo = str(record.get("id_archivo", "")).strip()
        id_servicio = str(record.get("id_servicio", "")).strip()
        cedula = str(record.get("cedula", "")).strip()
        
        # Generar vista de asunto y cuerpo
        config = ConfigManager.get_config()
        subject_template = config.get("email_subject", "")
        body_template = config.get("email_body", "")
        
        subject = subject_template.replace("{id_servicio}", id_servicio)
        body = body_template
        
        # Mostrar el modal de vista previa
        modal = ctk.CTkToplevel(self)
        modal.title("Vista Previa de Correo")
        modal.geometry("600x580")
        modal.resizable(False, False)
        modal.transient(self)
        modal.grab_set()
        modal.configure(fg_color=("#f8fafc", "#080c14"))
        
        lbl_title = ctk.CTkLabel(modal, text="Vista Previa de Correo", font=ctk.CTkFont(family="Segoe UI", size=20, weight="bold"), text_color=("#0f172a", "#f8fafc"))
        lbl_title.pack(pady=(20, 10))
        
        # Contenedor de datos
        details_frame = ctk.CTkFrame(modal, corner_radius=16, fg_color=("#ffffff", "#0e1322"), border_width=1, border_color=("#e2e8f0", "#1e293b"))
        details_frame.pack(fill="x", padx=30, pady=10, ipady=5)
        details_frame.grid_columnconfigure(1, weight=1)
        
        ctk.CTkLabel(details_frame, text="Remitente:", font=self.font_label, text_color=("#334155", "#cbd5e1")).grid(row=0, column=0, padx=20, pady=8, sticky="w")
        ctk.CTkLabel(details_frame, text=self.config_user.get(), font=self.font_text, text_color=("#64748b", "#94a3b8")).grid(row=0, column=1, padx=20, pady=8, sticky="w")
        
        ctk.CTkLabel(details_frame, text="Destinatario:", font=self.font_label, text_color=("#334155", "#cbd5e1")).grid(row=1, column=0, padx=20, pady=8, sticky="w")
        ctk.CTkLabel(details_frame, text=email, font=self.font_text, text_color=("#4f46e5", "#818cf8")).grid(row=1, column=1, padx=20, pady=8, sticky="w")
        
        ctk.CTkLabel(details_frame, text="Adjunto:", font=self.font_label, text_color=("#334155", "#cbd5e1")).grid(row=2, column=0, padx=20, pady=8, sticky="w")
        ctk.CTkLabel(details_frame, text=f"{id_archivo} (Protegido con contraseña)", font=self.font_text, text_color=("#64748b", "#94a3b8")).grid(row=2, column=1, padx=20, pady=8, sticky="w")
        
        ctk.CTkLabel(details_frame, text="Asunto:", font=self.font_label, text_color=("#334155", "#cbd5e1")).grid(row=3, column=0, padx=20, pady=8, sticky="w")
        ctk.CTkLabel(details_frame, text=subject, font=self.font_text, text_color=("#0f172a", "#f8fafc")).grid(row=3, column=1, padx=20, pady=8, sticky="w")
        
        # Contenedor del Cuerpo
        body_frame = ctk.CTkFrame(modal, corner_radius=16, fg_color=("#ffffff", "#0e1322"), border_width=1, border_color=("#e2e8f0", "#1e293b"))
        body_frame.pack(fill="both", expand=True, padx=30, pady=(10, 20))
        
        ctk.CTkLabel(body_frame, text="Cuerpo del Correo:", font=self.font_label, text_color=("#334155", "#cbd5e1")).pack(anchor="w", padx=20, pady=(15, 5))
        
        txt_body = ctk.CTkTextbox(body_frame, font=self.font_text, corner_radius=10, fg_color=("#f8fafc", "#070a13"), border_color=("#cbd5e1", "#1e293b"), border_width=1)
        txt_body.pack(fill="both", expand=True, padx=20, pady=(0, 20))
        txt_body.insert("0.0", body)
        txt_body.configure(state="disabled")

    def show_results_modal(self, errores, total, records_fallidos, email_corrections=None):
        if email_corrections is None:
            email_corrections = {}
        
        modal = ctk.CTkToplevel(self)
        modal.title("Reporte de Envíos")
        modal.geometry("620x580")
        modal.resizable(False, False)
        
        modal.transient(self)
        modal.grab_set()
        modal.configure(fg_color=("#f8fafc", "#080c14"))
        
        # Evitar TclError al cerrar el modal con la X mientras un widget tiene foco
        def safe_close_modal():
            try:
                self.focus_set()
                modal.destroy()
            except Exception:
                pass
        
        modal.protocol("WM_DELETE_WINDOW", safe_close_modal)

        lbl_title = ctk.CTkLabel(modal, text="Atención Requerida", font=ctk.CTkFont(family="Segoe UI", size=24, weight="bold"), text_color=("#d97706", "#fbbf24"))
        lbl_title.pack(pady=(25, 10))

        exitosos = total - len(errores)
        
        # Tarjeta de Resumen
        card_summary = ctk.CTkFrame(modal, corner_radius=16, fg_color=("#ffffff", "#0e1322"), border_width=1, border_color=("#e2e8f0", "#1e293b"))
        card_summary.pack(fill="x", padx=30, pady=(10, 15), ipady=10)
        
        lbl_total = ctk.CTkLabel(card_summary, text=f"Total: {total}", font=self.font_label, text_color=("#475569", "#cbd5e1"))
        lbl_total.pack(side="left", expand=True)
        lbl_success = ctk.CTkLabel(card_summary, text=f"Éxitos: {exitosos}", font=self.font_label, text_color=("#10b981", "#34d399"))
        lbl_success.pack(side="left", expand=True)
        lbl_err = ctk.CTkLabel(card_summary, text=f"Errores: {len(errores)}", font=self.font_label, text_color=("#ef4444", "#f87171"))
        lbl_err.pack(side="left", expand=True)

        # Si hay correcciones disponibles, mostrar un aviso
        if email_corrections:
            card_fix = ctk.CTkFrame(modal, corner_radius=12, fg_color=("#fef3c7", "#291505"), border_width=1, border_color=("#f59e0b", "#d97706"))
            card_fix.pack(fill="x", padx=30, pady=(0, 10), ipady=5)
            fix_count = len(email_corrections)
            lbl_fix = ctk.CTkLabel(
                card_fix, 
                text=f"Se detectaron {fix_count} correo(s) con errores corregibles automáticamente.",
                font=self.font_text, text_color=("#92400e", "#fde047")
            )
            lbl_fix.pack(padx=15, pady=8)

        # Textbox con los errores
        txt_errors = ctk.CTkTextbox(modal, width=560, height=200, font=self.font_text, corner_radius=12, fg_color=("#f8fafc", "#070a13"), text_color=("#334155", "#cbd5e1"), border_width=1, border_color=("#e2e8f0", "#1e293b"))
        txt_errors.pack(pady=10, padx=30)
        
        report_text = "--- REPORTE DE ERRORES ---\n\n"
        report_text += "\n".join(errores)
        
        txt_errors.insert("0.0", report_text)
        txt_errors.configure(state="disabled") # Solo lectura

        def copy_to_clipboard():
            self.clipboard_clear()
            self.clipboard_append(report_text)
            messagebox.showinfo("Copiado", "El reporte ha sido copiado al portapapeles.", parent=modal)

        def correct_and_retry():
            """Aplica las correcciones sugeridas a los emails y reintenta el envio."""
            corrected_records = []
            remaining_records = []
            
            for record in records_fallidos:
                email_original = str(record.get("email", "")).strip()
                if email_original in email_corrections:
                    # Crear copia del record con email corregido
                    corrected = dict(record)
                    corrected["email"] = email_corrections[email_original]
                    corrected_records.append(corrected)
                    logger.info(f"Email corregido: {email_original} -> {email_corrections[email_original]}")
                else:
                    remaining_records.append(record)
            
            if not corrected_records:
                messagebox.showinfo("Info", "No hay correcciones para aplicar.", parent=modal)
                return
            
            # Deshabilitar botones
            btn_correct.configure(state="disabled", text="Corrigiendo...", fg_color="#4b5563")
            btn_copy.configure(state="disabled")
            if records_fallidos:
                btn_retry.configure(state="disabled")
            lbl_title.configure(text="Aplicando correcciones...", text_color="gray")
            
            all_records_to_retry = corrected_records + remaining_records
            
            self.btn_start.configure(state="disabled", fg_color="#4b5563")
            self.progress_bar.set(0)
            self.lbl_status.configure(text=f"Reenviando {len(all_records_to_retry)} registro(s)...")
            
            self._execute_workflow(all_records_to_retry)
            safe_close_modal()

        def retry_failed():
            # Seguridad: Limitar reintentos para prevenir abuso de SMTP y bloqueo de cuenta
            self._retry_count += 1
            if self._retry_count > self.MAX_RETRIES:
                messagebox.showwarning(
                    "Límite Alcanzado",
                    f"Se han alcanzado {self.MAX_RETRIES} reintentos máximos por seguridad.\n"
                    f"Verifique manualmente los correos restantes antes de reiniciar.",
                    parent=modal
                )
                return
            
            # Deshabilitar botones mientras reintenta
            btn_retry.configure(state="disabled", text="Reintentando...", fg_color="#4b5563")
            btn_copy.configure(state="disabled")
            if email_corrections:
                btn_correct.configure(state="disabled")
            lbl_title.configure(text="Reintentando envios...", text_color="gray")
            
            self.btn_start.configure(state="disabled", fg_color="#4b5563")
            self.progress_bar.set(0)
            self.lbl_status.configure(text=f"Reintentando {len(records_fallidos)} envios fallidos... (Intento {self._retry_count}/{self.MAX_RETRIES})")
            
            self._execute_workflow(records_fallidos)
            safe_close_modal()

        # Botones en la parte inferior
        btn_frame = ctk.CTkFrame(modal, fg_color="transparent")
        btn_frame.pack(pady=(15, 10), fill="x", padx=30)
        
        btn_copy = ctk.CTkButton(btn_frame, text="Copiar Reporte", command=copy_to_clipboard, width=140, height=45, corner_radius=12, fg_color=("#4b5563", "#374151"), hover_color=("#374151", "#1f2937"))
        btn_copy.pack(side="left", padx=5, expand=True)

        if email_corrections:
            btn_correct = ctk.CTkButton(
                btn_frame, text="Corregir y Reintentar", command=correct_and_retry,
                width=180, height=45, corner_radius=12,
                font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
                fg_color=("#10b981", "#059669"), hover_color=("#059669", "#047857"), text_color="white"
            )
            btn_correct.pack(side="left", padx=5, expand=True)

        if records_fallidos:
            btn_retry = ctk.CTkButton(btn_frame, text="Reintentar Fallidos", command=retry_failed, width=160, height=45, corner_radius=12, font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"), fg_color=("#f59e0b", "#d97706"), hover_color=("#d97706", "#b45309"), text_color="white")
            btn_retry.pack(side="right", padx=5, expand=True)

    def setup_history_view(self):
        """Inicializa la estructura visual de la vista de Historial de Auditoría."""
        # Header
        lbl_title = ctk.CTkLabel(self.history_frame, text="Historial de Auditoría", font=self.font_title, text_color=("#0f172a", "#f8fafc"))
        lbl_title.pack(anchor="w", pady=(0, 2))
        
        lbl_subtitle = ctk.CTkLabel(self.history_frame, text="Consulte el registro histórico y la trazabilidad de todos los envíos masivos realizados", font=ctk.CTkFont(family="Segoe UI", size=13), text_color=("#64748b", "#94a3b8"))
        lbl_subtitle.pack(anchor="w", pady=(0, 20))
        
        # Card del buscador (Buscador superior con diseño Slate/Obsidian)
        search_card = ctk.CTkFrame(self.history_frame, corner_radius=16, fg_color=("#ffffff", "#0e1322"), border_width=1, border_color=("#e2e8f0", "#1e293b"))
        search_card.pack(fill="x", pady=(0, 20), ipady=5)
        search_card.grid_columnconfigure(0, weight=1)
        
        self.search_query = ctk.StringVar()
        self.search_entry = ctk.CTkEntry(
            search_card, textvariable=self.search_query, font=self.font_text, height=36,
            fg_color=("#f8fafc", "#070a13"), border_color=("#cbd5e1", "#1e293b"),
            placeholder_text="Buscar en todos los envíos por email, cédula, ID de servicio o archivo..."
        )
        self.search_entry.grid(row=0, column=0, padx=(20, 10), pady=15, sticky="ew")
        
        btn_search = ctk.CTkButton(
            search_card, text="🔍 Buscar", font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"), width=100, height=36,
            fg_color=("#3b82f6", "#2563eb"), hover_color=("#2563eb", "#1d4ed8"), command=self.perform_history_search
        )
        btn_search.grid(row=0, column=1, padx=5, pady=15)
        
        btn_clear_search = ctk.CTkButton(
            search_card, text="Limpiar", font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"), width=80, height=36,
            fg_color=("#4b5563", "#374151"), hover_color=("#374151", "#1f2937"), command=self.clear_history_search
        )
        btn_clear_search.grid(row=0, column=2, padx=(5, 20), pady=15)
        
        # Contenedor dinámico (Scrollable Frame) para los resultados o lotes con estética premium
        self.history_content_frame = ctk.CTkScrollableFrame(self.history_frame, corner_radius=16, fg_color=("#ffffff", "#0e1322"), border_width=1, border_color=("#e2e8f0", "#1e293b"))
        self.history_content_frame.pack(fill="both", expand=True)

    def load_history_batches(self):
        """Carga y muestra el listado de todos los lotes de envío con diseño premium."""
        # Limpiar el frame de contenido
        for widget in self.history_content_frame.winfo_children():
            widget.destroy()
        
        self.search_query.set("") # Limpiar texto de búsqueda
        
        lotes = list(reversed(self.session_batches))
        if not lotes:
            lbl_empty = ctk.CTkLabel(
                self.history_content_frame, 
                text="No hay registros de envíos en el historial todavía.", 
                font=self.font_status, text_color=("#64748b", "#94a3b8")
            )
            lbl_empty.pack(pady=50)
            return
            
        lbl_subtitle = ctk.CTkLabel(
            self.history_content_frame, 
            text="📋 Lotes Recientes de Envíos Masivos (Esta Sesión)", 
            font=ctk.CTkFont(family="Segoe UI", size=15, weight="bold"),
            text_color=("#0f172a", "#f8fafc")
        )
        lbl_subtitle.pack(anchor="w", padx=20, pady=(15, 10))
        
        for lote in lotes:
            # Crear una tarjeta para cada lote con estética Obsidian Slate
            lote_card = ctk.CTkFrame(self.history_content_frame, corner_radius=12, fg_color=("#f8fafc", "#070a13"), border_width=1, border_color=("#e2e8f0", "#1e293b"))
            lote_card.pack(fill="x", padx=15, pady=8, ipady=5)
            lote_card.grid_columnconfigure(0, weight=1)
            
            # Texto descriptivo (Lote #, Fecha, Archivo)
            lote_id = lote['id']
            fecha = lote['fecha']
            csv_nombre = lote['csv_nombre']
            total = lote['total_registros']
            exitos = lote['exitosos']
            fallos = lote['fallidos']
            
            info_text = f"Lote #{lote_id} — {fecha}\nCSV: {csv_nombre}"
            lbl_info = ctk.CTkLabel(lote_card, text=info_text, font=self.font_text, justify="left", anchor="w", text_color=("#334155", "#cbd5e1"))
            lbl_info.grid(row=0, column=0, padx=20, pady=10, sticky="w")
            
            # Contadores
            stat_frame = ctk.CTkFrame(lote_card, fg_color="transparent")
            stat_frame.grid(row=0, column=1, padx=10, pady=10)
            
            ctk.CTkLabel(stat_frame, text=f"Total: {total}", font=self.font_text, text_color=("#475569", "#94a3b8")).pack(side="left", padx=10)
            ctk.CTkLabel(stat_frame, text=f"Éxitos: {exitos}", font=self.font_label, text_color=("#10b981", "#34d399")).pack(side="left", padx=10)
            ctk.CTkLabel(stat_frame, text=f"Fallos: {fallos}", font=self.font_label, text_color=("#ef4444", "#f87171")).pack(side="left", padx=10)
            
            # Botón Ver Detalle del lote
            btn_details = ctk.CTkButton(
                lote_card, text="Ver Detalle", font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"), width=100, height=32,
                fg_color=("#4f46e5", "#6366f1"), hover_color=("#4338ca", "#4f46e5"),
                command=lambda lid=lote_id, ldata=lote: self.show_lote_details_modal(lid, ldata)
            )
            btn_details.grid(row=0, column=2, padx=20, pady=10)

    def show_lote_details_modal(self, lote_id, lote_data):
        """Abre un modal premium con la lista detallada de envíos en el lote."""
        modal = ctk.CTkToplevel(self)
        modal.title(f"Detalle de Envío - Lote #{lote_id}")
        modal.geometry("750x580")
        modal.resizable(False, False)
        modal.transient(self)
        modal.grab_set()
        modal.configure(fg_color=("#f8fafc", "#080c14"))
        
        lbl_title = ctk.CTkLabel(modal, text=f"Detalle del Lote #{lote_id}", font=ctk.CTkFont(family="Segoe UI", size=20, weight="bold"), text_color=("#0f172a", "#f8fafc"))
        lbl_title.pack(pady=(20, 5))
        
        # Tarjeta de datos del lote con estética premium
        info_frame = ctk.CTkFrame(modal, corner_radius=16, fg_color=("#ffffff", "#0e1322"), border_width=1, border_color=("#e2e8f0", "#1e293b"))
        info_frame.pack(fill="x", padx=30, pady=10, ipady=5)
        
        info_str = f"Archivo: {lote_data['csv_nombre']}   |   Fecha: {lote_data['fecha']}"
        ctk.CTkLabel(info_frame, text=info_str, font=self.font_text, text_color=("#334155", "#cbd5e1")).pack(pady=5)
        
        stats_str = f"Total Registros: {lote_data['total_registros']}   -   Exitosos: {lote_data['exitosos']}   -   Fallidos: {lote_data['fallidos']}"
        ctk.CTkLabel(
            info_frame, text=stats_str, font=self.font_label, 
            text_color=("#4f46e5", "#818cf8")
        ).pack(pady=(0, 5))
        
        # Scrollable Frame con los envíos del lote
        envios_scroll = ctk.CTkScrollableFrame(modal, corner_radius=16, fg_color=("#ffffff", "#0e1322"), border_width=1, border_color=("#e2e8f0", "#1e293b"))
        envios_scroll.pack(fill="both", expand=True, padx=30, pady=10)
        
        envios = lote_data.get('envios', [])
        if not envios:
            ctk.CTkLabel(envios_scroll, text="No hay registros individuales para este lote.", font=self.font_status, text_color=("#64748b", "#94a3b8")).pack(pady=40)
        else:
            for ev in envios:
                row_frame = ctk.CTkFrame(envios_scroll, corner_radius=12, fg_color=("#f8fafc", "#070a13"), border_width=1, border_color=("#e2e8f0", "#1e293b"))
                row_frame.pack(fill="x", pady=4, padx=5, ipady=3)
                row_frame.grid_columnconfigure(0, weight=1)
                
                # Datos de registro
                email = ev['email']
                cedula = ev['cedula']
                id_archivo = ev['id_archivo']
                id_servicio = ev['id_servicio']
                estado = ev['estado']
                detalles = ev['detalles']
                
                desc = f"Email: {email}\nID: {cedula} | Servicio: {id_servicio} | Archivo: {id_archivo}"
                lbl_desc = ctk.CTkLabel(row_frame, text=desc, font=self.font_text, justify="left", anchor="w", text_color=("#334155", "#cbd5e1"))
                lbl_desc.grid(row=0, column=0, padx=15, pady=8, sticky="w")
                
                # Etiqueta Estado estilizada
                if estado == "exito":
                    lbl_est = ctk.CTkLabel(row_frame, text="EXITOSO", font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"), text_color="white", fg_color="#10b981", corner_radius=6, width=90, height=26)
                else:
                    lbl_est = ctk.CTkLabel(row_frame, text="FALLIDO", font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"), text_color="white", fg_color="#ef4444", corner_radius=6, width=90, height=26)
                lbl_est.grid(row=0, column=1, padx=15, pady=8, sticky="e")
                
                # Detalles del error
                if detalles:
                    lbl_det = ctk.CTkLabel(row_frame, text=f"Detalle: {detalles}", font=ctk.CTkFont(family="Segoe UI", size=11, slant="italic"), text_color=("#ef4444", "#f87171"), justify="left", anchor="w")
                    lbl_det.grid(row=1, column=0, columnspan=2, padx=15, pady=(0, 8), sticky="w")
                    
        # Botón para cerrar modal
        btn_close = ctk.CTkButton(modal, text="Cerrar", font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"), width=140, height=42, fg_color=("#4b5563", "#374151"), hover_color=("#374151", "#1f2937"), command=modal.destroy)
        btn_close.pack(pady=15)

    def perform_history_search(self):
        """Ejecuta la búsqueda global del historial y despliega las tarjetas con estilo premium."""
        query = self.search_query.get().strip()
        if not query:
            self.load_history_batches()
            return
            
        # Limpiar el frame de contenido
        for widget in self.history_content_frame.winfo_children():
            widget.destroy()
            
        query_strip = query.strip()
        query_lower = query_strip.lower()
        
        # Calcular HMAC-SHA256 para búsqueda exacta segura de PII
        query_email_hash = hmac.new(self._hmac_key, query_lower.encode(), hashlib.sha256).hexdigest()
        query_cedula_hash = hmac.new(self._hmac_key, query_strip.encode(), hashlib.sha256).hexdigest()
        
        results = []
        for lote in self.session_batches:
            for ev in lote.get("envios", []):
                is_match = False
                
                # Búsqueda exacta por hash para mantener privacidad sin almacenar texto plano
                if query_email_hash == ev.get("email_hash"):
                    is_match = True
                elif query_cedula_hash == ev.get("cedula_hash"):
                    is_match = True
                # Búsqueda por coincidencia parcial para campos no sensibles o enmascarados
                elif (query_lower in ev.get("email", "").lower() or 
                      query_lower in ev.get("id_archivo", "").lower() or 
                      query_lower in ev.get("id_servicio", "").lower() or
                      query_lower in ev.get("cedula", "").lower()):
                    is_match = True
                    
                if is_match:
                    res_entry = dict(ev)
                    res_entry["fecha"] = lote["fecha"]
                    res_entry["csv_nombre"] = lote["csv_nombre"]
                    results.append(res_entry)
        results = list(reversed(results))[:200]
        
        lbl_subtitle = ctk.CTkLabel(
            self.history_content_frame, 
            text=f"🔍 Resultados de búsqueda para: '{query}' ({len(results)} encontrados)", 
            font=ctk.CTkFont(family="Segoe UI", size=16, weight="bold"),
            text_color=("#0f172a", "#f8fafc")
        )
        lbl_subtitle.pack(anchor="w", padx=20, pady=(15, 10))
        
        if not results:
            lbl_empty = ctk.CTkLabel(
                self.history_content_frame, 
                text="No se encontraron coincidencias en los envíos de historial.", 
                font=self.font_status, text_color=("#64748b", "#94a3b8")
            )
            lbl_empty.pack(pady=50)
            return
            
        for ev in results:
            row_frame = ctk.CTkFrame(self.history_content_frame, corner_radius=12, fg_color=("#f8fafc", "#070a13"), border_width=1, border_color=("#e2e8f0", "#1e293b"))
            row_frame.pack(fill="x", padx=15, pady=6, ipady=5)
            row_frame.grid_columnconfigure(0, weight=1)
            
            email = ev['email']
            cedula = ev['cedula']
            id_archivo = ev['id_archivo']
            id_servicio = ev['id_servicio']
            estado = ev['estado']
            detalles = ev['detalles']
            fecha = ev['fecha']
            csv_nombre = ev.get('csv_nombre', 'N/A')
            
            desc = f"Fecha: {fecha} | Lote CSV: {csv_nombre}\nDestinatario: {email}\nID: {cedula} | Servicio: {id_servicio} | Archivo: {id_archivo}"
            lbl_desc = ctk.CTkLabel(row_frame, text=desc, font=self.font_text, justify="left", anchor="w", text_color=("#334155", "#cbd5e1"))
            lbl_desc.grid(row=0, column=0, padx=20, pady=10, sticky="w")
            
            # Etiqueta Estado
            if estado == "exito":
                lbl_est = ctk.CTkLabel(row_frame, text="ÉXITO", font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"), text_color="white", fg_color="#10b981", corner_radius=6, width=90, height=26)
            else:
                lbl_est = ctk.CTkLabel(row_frame, text="FALLIDO", font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"), text_color="white", fg_color="#ef4444", corner_radius=6, width=90, height=26)
            lbl_est.grid(row=0, column=1, padx=20, pady=10, sticky="e")
            
            if detalles:
                lbl_det = ctk.CTkLabel(row_frame, text=f"Detalle: {detalles}", font=ctk.CTkFont(family="Segoe UI", size=11, slant="italic"), text_color=("#ef4444", "#f87171"), justify="left", anchor="w")
                lbl_det.grid(row=1, column=0, columnspan=2, padx=20, pady=(0, 10), sticky="w")

    def clear_history_search(self):
        """Limpia el cuadro de búsqueda y vuelve a cargar los lotes del historial."""
        self.load_history_batches()

    def _emergency_cleanup_temp_files(self):
        """Limpieza de emergencia: sobreescribe y elimina temporales sems_*.pdf del directorio temporal."""
        try:
            temp_dir = tempfile.gettempdir()
            for temp_file in glob.glob(os.path.join(temp_dir, "sems_*.pdf")):
                try:
                    size = os.path.getsize(temp_file)
                    if size > 0:
                        with open(temp_file, "r+b") as f:
                            f.seek(0)
                            f.write(os.urandom(size))
                    os.remove(temp_file)
                except Exception:
                    try:
                        os.remove(temp_file)
                    except Exception:
                        pass
        except Exception:
            pass

    def _on_closing(self):
        """Manejador de cierre seguro: limpia temporales antes de destruir la ventana."""
        self._emergency_cleanup_temp_files()
        self.destroy()
