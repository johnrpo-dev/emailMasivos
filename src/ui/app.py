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
from src.ui.views.home_view import HomeView
from src.ui.views.config_view import ConfigView
from src.ui.views.history_view import HistoryView
from src.ui.modals.preview_modal import PreviewModal
from src.ui.controllers.workflow_controller import WorkflowController

class App(ctk.CTk):
    """Clase ventana principal coordinadora de navegación y estados globales de la sesión."""
    def __init__(self):
        super().__init__()

        self.title("SEMS Pro - Envíos Masivos")
        # Reducimos la altura por defecto a 690px para pantallas de 15" y permitimos redimensionar libremente
        self.geometry("850x690")
        self.resizable(True, True)
        
        # Inicializar historial efímero en memoria RAM (Zero-Footprint por diseño)
        self.session_batches = []
        self._hmac_key = secrets.token_bytes(32)
        
        # Tema Global Premium
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        
        # Variables de estado (Envío)
        default_pdf_dir = os.path.join(os.getcwd(), "data", "input")
        self.csv_path = ctk.StringVar()
        self.pdf_dir = ctk.StringVar(value=default_pdf_dir)
        
        # Variables de Configuración
        self._real_smtp_user = ""
        self.config_user = ctk.StringVar()
        self.config_pass = ctk.StringVar()
        self.config_subject = ctk.StringVar()
        self.config_sender_name = ctk.StringVar(value="SEMS Pro")
        self.config_delay = ctk.StringVar(value="2")
        self.config_logo_path = ctk.StringVar()
        
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
        
        # Inicializar controladores de UI
        self.workflow_controller = WorkflowController(self)

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
        self.config_sender_name.set(config.get("sender_name", "SEMS Pro"))
        self.config_delay.set(str(config.get("send_delay", 2)))
        self.config_logo_path.set(config.get("logo_path", ""))
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
        self.workflow_controller.start_process()
        
    def compute_search_hash(self, value: str) -> str:
        """Calcula el hash seguro HMAC-SHA256 para búsquedas de PII en el historial."""
        import hmac
        import hashlib
        return hmac.new(self._hmac_key, value.encode(), hashlib.sha256).hexdigest()
            
    def show_desktop_notification(self, title, message):
        """Muestra una notificación de escritorio en Windows usando PowerShell nativo."""
        if sys.platform != "win32":
            return
        try:
            # Eliminamos la limpieza agresiva con regex porque pasamos datos por variables de entorno,
            # aislando los datos de PowerShell y anulando el riesgo de inyección (SEC-002).
            # Mantenemos un límite de longitud sensato.
            safe_title = title[:100]
            safe_message = message[:250]
            
            ps_code = (
                '[void][System.Reflection.Assembly]::LoadWithPartialName("System.Windows.Forms");'
                '$n=New-Object System.Windows.Forms.NotifyIcon;'
                '$n.Icon=[System.Drawing.SystemIcons]::Information;'
                '$n.BalloonTipIcon="Info";'
                '$n.BalloonTipText=$env:SEMS_NOTIF_MSG;'
                '$n.BalloonTipTitle=$env:SEMS_NOTIF_TITLE;'
                '$n.Visible=$True;'
                '$n.ShowBalloonTip(5000)'
            )
            
            ps_env = os.environ.copy()
            ps_env["SEMS_NOTIF_TITLE"] = safe_title
            ps_env["SEMS_NOTIF_MSG"] = safe_message
            
            subprocess.run(
                ["powershell", "-NoProfile", "-Command", ps_code],
                capture_output=True,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW,
                timeout=10,
                env=ps_env
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
            # Limpiar de ambas carpetas: la del sistema y la privada del espacio de trabajo
            temp_dirs = [tempfile.gettempdir(), os.path.join(os.getcwd(), "data", "temp")]
            for t_dir in temp_dirs:
                if not os.path.exists(t_dir):
                    continue
                for temp_file in glob.glob(os.path.join(t_dir, "sems_*.pdf")):
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
