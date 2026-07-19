# pyrefly: ignore [missing-import]
import customtkinter as ctk
from tkinter import filedialog
import os
import sys
import subprocess
import secrets
import tempfile
import glob
import atexit
from src.config.config_manager import ConfigManager
from src.utils.logger import logger, mask_email
from src.ui import theme, dialogs
from src.ui.components import GhostNavButton, apply_window_icon
from src.ui.views.home_view import HomeView
from src.ui.views.config_view import ConfigView
from src.ui.views.history_view import HistoryView
from src.ui.modals.preview_modal import PreviewModal
from src.ui.controllers.workflow_controller import WorkflowController

class App(ctk.CTk):
    """Clase ventana principal coordinadora de navegación y estados globales de la sesión."""
    def __init__(self):
        super().__init__()

        # Las fuentes cacheadas del root anterior (ActivationModal) quedarían
        # ligadas a un Tk destruido: limpiar antes de crear cualquier CTkFont.
        theme.reset_font_cache()

        self.title("SEMS Pro - Envíos Masivos")
        # Reducimos la altura por defecto a 690px para pantallas de 15" y permitimos redimensionar libremente
        self.geometry("850x690")
        self.resizable(True, True)
        self.minsize(820, 620)
        apply_window_icon(self)

        # Inicializar historial efímero en memoria RAM (Zero-Footprint por diseño)
        self.session_batches = []
        self._hmac_key = secrets.token_bytes(32)

        # Tema clínico global
        ctk.set_appearance_mode(theme.DEFAULT_APPEARANCE)
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
        self.config_pdf_prefix = ctk.StringVar()
        self.config_pdf_suffix = ctk.StringVar()
        
        # Proveedores SMTP preconfigurados
        self.smtp_providers = {
            "Gmail": {"host": "smtp.gmail.com", "port": 587},
            "Outlook / Hotmail": {"host": "smtp.office365.com", "port": 587},
            "Yahoo": {"host": "smtp.mail.yahoo.com", "port": 587},
            "Zoho": {"host": "smtp.zoho.com", "port": 587},
            "iCloud": {"host": "smtp.mail.me.com", "port": 587},
        }
        self.config_provider = ctk.StringVar(value="Gmail")
        
        # Tipografías base (alias de compatibilidad hacia el tema central)
        self.font_title = theme.font("h1")
        self.font_label = theme.font("body_strong")
        self.font_text = theme.font("body")
        self.font_status = theme.font("status")
        
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
        
        if config.get("smtp_password", ""):
            self.config_pass.set("••••••••")
        else:
            self.config_pass.set("")
            
        self.config_subject.set(config.get("email_subject", ""))
        self.config_sender_name.set(config.get("sender_name", "SEMS Pro"))
        self.config_delay.set(str(config.get("send_delay", 2)))
        self.config_logo_path.set(config.get("logo_path", ""))
        self.config_pdf_prefix.set(config.get("pdf_password_prefix", ""))
        self.config_pdf_suffix.set(config.get("pdf_password_suffix", ""))
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
        self.configure(fg_color=theme.APP_BG)

        # === SIDEBAR ===
        self.sidebar_frame = ctk.CTkFrame(self, width=230, corner_radius=0, fg_color=theme.SIDEBAR_BG, border_width=0)
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(5, weight=1) # Empujar hacia arriba

        lbl_logo = ctk.CTkLabel(
            self.sidebar_frame, text="SEMS PRO",
            font=ctk.CTkFont(family=theme.FONT_FAMILY, size=24, weight="bold"),
            text_color=theme.PRIMARY
        )
        lbl_logo.grid(row=0, column=0, padx=20, pady=(30, 0))

        lbl_logo_sub = ctk.CTkLabel(
            self.sidebar_frame, text="ENVÍOS INTELIGENTES",
            font=ctk.CTkFont(family=theme.FONT_FAMILY, size=9, weight="bold"),
            text_color=theme.TEXT_MUTED
        )
        lbl_logo_sub.grid(row=1, column=0, padx=20, pady=(0, 30))

        self.btn_nav_home = GhostNavButton(self.sidebar_frame, text="Envío Masivo", command=self.show_home)
        self.btn_nav_home.grid(row=2, column=0, padx=15, pady=6, sticky="ew")

        self.btn_nav_config = GhostNavButton(self.sidebar_frame, text="Configuración", command=self.show_config)
        self.btn_nav_config.grid(row=3, column=0, padx=15, pady=6, sticky="ew")

        self.btn_nav_history = GhostNavButton(self.sidebar_frame, text="Historial", command=self.show_history)
        self.btn_nav_history.grid(row=4, column=0, padx=15, pady=6, sticky="ew")

        self._nav_buttons = {
            "home": self.btn_nav_home,
            "config": self.btn_nav_config,
            "history": self.btn_nav_history,
        }

        # Conmutador de apariencia claro/oscuro al pie del sidebar
        self.appearance_switch = ctk.CTkSwitch(
            self.sidebar_frame, text="Modo oscuro",
            font=theme.font("caption"), text_color=theme.TEXT_SECONDARY,
            progress_color=theme.BTN_PRIMARY_FG,
            command=self._toggle_appearance
        )
        self.appearance_switch.grid(row=6, column=0, padx=20, pady=(0, 25), sticky="w")
        if theme.DEFAULT_APPEARANCE == "dark":
            self.appearance_switch.select()

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

    def _toggle_appearance(self):
        ctk.set_appearance_mode("dark" if self.appearance_switch.get() else "light")

    def _set_active_nav(self, active_name):
        """Marca como activo el botón de navegación indicado y desactiva el resto."""
        for name, btn in self._nav_buttons.items():
            btn.set_active(name == active_name)

    def show_home(self):
        self.config_panel.grid_forget()
        self.history_panel.grid_forget()
        self.home_panel.grid(row=0, column=0, sticky="nsew")
        self._set_active_nav("home")

    def show_config(self):
        self.home_panel.grid_forget()
        self.history_panel.grid_forget()
        self.config_panel.grid(row=0, column=0, sticky="nsew")
        self._set_active_nav("config")

    def show_history(self):
        self.home_panel.grid_forget()
        self.config_panel.grid_forget()
        self.history_panel.grid(row=0, column=0, sticky="nsew")
        self._set_active_nav("history")
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
            dialogs.show_warning(self, "Atención", "Selecciona primero el archivo CSV de datos.")
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
            system_temp = tempfile.gettempdir()
            # Buscar archivos sems_*.pdf directamente en el temp del sistema
            temp_dirs = [system_temp]
            # Cobertura de la ubicación legada data/temp del directorio de trabajo (M-02):
            # versiones anteriores escribían los temporales cifrados allí y dejaban residuos.
            legacy_temp = os.path.join(os.getcwd(), "data", "temp")
            if os.path.isdir(legacy_temp):
                temp_dirs.append(legacy_temp)
            # También buscar en subdirectorios sems_batch_* creados por mkdtemp
            for entry in os.listdir(system_temp):
                if entry.startswith("sems_batch_"):
                    candidate = os.path.join(system_temp, entry)
                    if os.path.isdir(candidate):
                        temp_dirs.append(candidate)
            
            for t_dir in temp_dirs:
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
            
            # Limpiar los directorios sems_batch_* vacíos
            for entry in os.listdir(system_temp):
                if entry.startswith("sems_batch_"):
                    candidate = os.path.join(system_temp, entry)
                    try:
                        if os.path.isdir(candidate) and not os.listdir(candidate):
                            os.rmdir(candidate)
                    except Exception:
                        pass
        except Exception:
            pass
