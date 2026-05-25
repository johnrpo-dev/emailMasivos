# pyrefly: ignore [missing-import]
import customtkinter as ctk
from tkinter import filedialog, messagebox
import os
import re
import sys
import subprocess
import secrets
import tempfile
import glob
import atexit
from src.config.config_manager import ConfigManager
from src.utils.logger import logger, mask_email
from src.core.workflow_orchestrator import WorkflowOrchestrator
from src.ui.views.home_view import HomeView
from src.ui.views.config_view import ConfigView
from src.ui.views.history_view import HistoryView
from src.ui.modals.preview_modal import PreviewModal
from src.ui.modals.results_modal import ResultsModal

class App(ctk.CTk):
    """Clase ventana principal coordinadora de navegación y estados globales de la sesión."""
    def __init__(self):
        super().__init__()

        self.title("SEMS Pro - Envíos Masivos")
        self.geometry("850x680")
        self.resizable(False, False)
        
        # Inicializar historial efímero en memoria RAM (Zero-Footprint por diseño)
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
        self._real_smtp_user = ""
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
        
        # Cargar configuración e inicializar UI
        self.load_settings()
        self.setup_ui()
        
        # Seguridad: Manejar cierre de ventana para limpiar archivos temporales
        self.protocol("WM_DELETE_WINDOW", self._on_closing)
        atexit.register(self._emergency_cleanup_temp_files)
        
    def load_settings(self):
        config = ConfigManager.get_config()
        self._real_smtp_user = config.get("smtp_user", "")
        self.config_user.set(mask_email(self._real_smtp_user))
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
        self.configure(fg_color=("#f8fafc", "#080c14"))
        
        # === SIDEBAR ===
        self.sidebar_frame = ctk.CTkFrame(self, width=230, corner_radius=0, fg_color=("#f1f5f9", "#0d111c"), border_width=0)
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(5, weight=1) # Empujar hacia arriba
        
        lbl_logo = ctk.CTkLabel(
            self.sidebar_frame, text="SEMS PRO", 
            font=ctk.CTkFont(family="Segoe UI", size=24, weight="bold"),
            text_color=("#4f46e5", "#818cf8")
        )
        lbl_logo.grid(row=0, column=0, padx=20, pady=(30, 5))
        
        lbl_logo_sub = ctk.CTkLabel(
            self.sidebar_frame, text="ENVÍOS INTELIGENTES", 
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
        
        # Instanciar e integrar los paneles modulares
        self.home_panel = HomeView(self.main_container, self)
        self.config_panel = ConfigView(self.main_container, self)
        self.history_panel = HistoryView(self.main_container, self)
        
        self.show_home()
        
    def show_home(self):
        self.config_panel.grid_forget()
        self.history_panel.grid_forget()
        self.home_panel.grid(row=0, column=0, sticky="nsew")
        self.btn_nav_home.configure(fg_color=("#e2e8f0", "#1e293b"), text_color=("#4f46e5", "#818cf8"))
        self.btn_nav_config.configure(fg_color="transparent", text_color=("#475569", "#94a3b8"))
        self.btn_nav_history.configure(fg_color="transparent", text_color=("#475569", "#94a3b8"))
        
    def show_config(self):
        self.home_panel.grid_forget()
        self.history_panel.grid_forget()
        self.config_panel.grid(row=0, column=0, sticky="nsew")
        self.btn_nav_config.configure(fg_color=("#e2e8f0", "#1e293b"), text_color=("#4f46e5", "#818cf8"))
        self.btn_nav_home.configure(fg_color="transparent", text_color=("#475569", "#94a3b8"))
        self.btn_nav_history.configure(fg_color="transparent", text_color=("#475569", "#94a3b8"))
        
    def show_history(self):
        self.home_panel.grid_forget()
        self.config_panel.grid_forget()
        self.history_panel.grid(row=0, column=0, sticky="nsew")
        self.btn_nav_history.configure(fg_color=("#e2e8f0", "#1e293b"), text_color=("#4f46e5", "#818cf8"))
        self.btn_nav_home.configure(fg_color="transparent", text_color=("#475569", "#94a3b8"))
        self.btn_nav_config.configure(fg_color="transparent", text_color=("#475569", "#94a3b8"))
        self.history_panel.load_history_batches()
        
    def browse_csv(self):
        filename = filedialog.askopenfilename(filetypes=[("CSV files", "*.csv")])
        if filename: 
            self.csv_path.set(filename)
            
    def browse_pdf_dir(self):
        directory = filedialog.askdirectory()
        if directory: 
            self.pdf_dir.set(directory)
            
    def show_preview(self):
        """Invoca al modal desacoplado de vista previa de datos."""
        if not self.csv_path.get():
            messagebox.showwarning("Atención", "Selecciona primero el archivo CSV de datos.")
            return
        PreviewModal(self, self.csv_path.get())
        
    def start_process(self):
        """Prepara e inicia la orquestación del proceso en segundo plano."""
        self._retry_count = 0
        if not self.csv_path.get() or not self.pdf_dir.get():
            messagebox.showwarning("Atención", "Selecciona el CSV y la carpeta de PDFs.")
            return
            
        config = ConfigManager.get_config()
        if not config.get("smtp_user") or not config.get("smtp_password"):
            messagebox.showwarning("Atención", "Ve a la pestaña de Configuración e ingresa tus credenciales SMTP primero.")
            return
            
        self.home_panel.btn_start.configure(state="disabled", fg_color="#4b5563")
        self.home_panel.btn_preview.configure(state="disabled", fg_color="#4b5563")
        self.home_panel.progress_bar.set(0)
        self.home_panel.lbl_status.configure(text="Procesando...")
        
        self._execute_workflow()
        
    def _execute_workflow(self, records_to_process=None):
        orchestrator = WorkflowOrchestrator()
        
        def on_batch_added(batch_record):
            def _add():
                batch_record["id"] = len(self.session_batches) + 1
                self.session_batches.append(batch_record)
            self.after(0, _add)

        def on_log(text):
            self.home_panel.add_console_log(text)

        def on_progress(text, progress=None):
            self.after(0, lambda: self.home_panel.update_ui_status(text, progress))

        def on_stats_update(total=None, success=None, failed=None):
            self.home_panel.update_monitor_stats(total=total, success=success, failed=failed)

        def on_complete(errores, total, records_fallidos, email_corrections):
            def _complete():
                try:
                    from src.core.license_manager import LicenseManager
                    LicenseManager.update_last_run()
                    
                    exitosos_total = total - len(errores)
                    self.home_panel.update_ui_status("¡Proceso masivo completado!", 1.0)
                    self.home_panel.add_console_log(f"✓ COMPLETADO: {exitosos_total} exitosos, {len(errores)} fallidos.")
                    
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
                    self.home_panel.btn_start.configure(state="normal", fg_color=("#10b981", "#059669"))
                    self.home_panel.btn_preview.configure(state="normal", fg_color=("#3b82f6", "#2563eb"))
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
        
    def compute_search_hash(self, value: str) -> str:
        """Calcula el hash seguro HMAC-SHA256 para búsquedas de PII en el historial."""
        import hmac
        import hashlib
        return hmac.new(self._hmac_key, value.encode(), hashlib.sha256).hexdigest()

    def show_results_modal(self, errores, total, records_fallidos, email_corrections=None):
        if email_corrections is None:
            email_corrections = {}
            
        def on_retry():
            self._retry_count += 1
            if self._retry_count > self.MAX_RETRIES:
                messagebox.showwarning(
                    "Límite Alcanzado",
                    f"Se han alcanzado {self.MAX_RETRIES} reintentos máximos por seguridad.\n"
                    f"Verifique manualmente los correos restantes antes de reiniciar."
                )
                return
                
            self.home_panel.btn_start.configure(state="disabled", fg_color="#4b5563")
            self.home_panel.progress_bar.set(0)
            self.home_panel.lbl_status.configure(
                text=f"Reintentando {len(records_fallidos)} envios fallidos... (Intento {self._retry_count}/{self.MAX_RETRIES})"
            )
            self._execute_workflow(records_fallidos)

        def on_correct_and_retry():
            corrected_records = []
            remaining_records = []
            
            for record in records_fallidos:
                email_original = str(record.get("email", "")).strip()
                if email_original in email_corrections:
                    corrected = dict(record)
                    corrected["email"] = email_corrections[email_original]
                    corrected_records.append(corrected)
                    logger.info(f"Email corregido: {email_original} -> {email_corrections[email_original]}")
                else:
                    remaining_records.append(record)
                    
            if not corrected_records:
                messagebox.showinfo("Info", "No hay correcciones para aplicar.")
                return
                
            all_records_to_retry = corrected_records + remaining_records
            
            self.home_panel.btn_start.configure(state="disabled", fg_color="#4b5563")
            self.home_panel.progress_bar.set(0)
            self.home_panel.lbl_status.configure(text=f"Reenviando {len(all_records_to_retry)} registro(s)...")
            
            self._execute_workflow(all_records_to_retry)

        ResultsModal(
            self, errores, total, records_fallidos, email_corrections,
            on_retry=on_retry, on_correct_and_retry=on_correct_and_retry
        )
            
    def show_desktop_notification(self, title, message):
        """Muestra una notificación de escritorio en Windows usando PowerShell nativo."""
        if sys.platform != "win32":
            return
        try:
            safe_title = re.sub(r"[^a-zA-Z0-9áéíóúüñÁÉÍÓÚÜÑ .,!#@:_\-]", "", title)[:100]
            safe_message = re.sub(r"[^a-zA-Z0-9áéíóúüñÁÉÍÓÚÜÑ .,!#@:_\-/]", "", message)[:250]
            
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
                ["powershell", "-NoProfile", "-Command", ps_code],
                capture_output=True,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW,
                timeout=10
            )
        except Exception as e:
            logger.warning(f"No se pudo mostrar la notificación de Windows: {str(e)}")
            
    def _on_closing(self):
        """Manejador al cerrar la ventana principal."""
        try:
            self._emergency_cleanup_temp_files()
        finally:
            self.destroy()
            
    def _emergency_cleanup_temp_files(self):
        """Limpieza de emergencia: sobreescribe y elimina temporales sems_*.pdf."""
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
                    pass
        except Exception:
            pass
