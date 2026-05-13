# pyrefly: ignore [missing-import]
import customtkinter as ctk
from tkinter import filedialog, messagebox
import os
import threading
from src.core.data_manager import DataManager
from src.core.pdf_crypto import PDFCrypto
from src.core.email_service import EmailService
from src.config.config_manager import ConfigManager
from src.utils.logger import logger, mask_email

class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("SEMS Pro - Envíos Masivos")
        self.geometry("850x650")
        self.resizable(False, False)
        
        # Tema Global Premium
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        
        # Variables de estado (Envío)
        default_pdf_dir = os.path.join(os.getcwd(), "data", "input")
        self.csv_path = ctk.StringVar()
        self.pdf_dir = ctk.StringVar(value=default_pdf_dir)
        
        # Variables de Configuración
        self.config_user = ctk.StringVar()
        self.config_pass = ctk.StringVar()
        self.config_subject = ctk.StringVar()
        
        # Tipografías base
        self.font_title = ctk.CTkFont(family="Segoe UI", size=26, weight="bold")
        self.font_label = ctk.CTkFont(family="Segoe UI", size=14, weight="bold")
        self.font_text = ctk.CTkFont(family="Segoe UI", size=13)
        self.font_status = ctk.CTkFont(family="Segoe UI", size=14, slant="italic")
        
        # Cargar config
        self.load_settings()
        self.setup_ui()
        
    def load_settings(self):
        config = ConfigManager.get_config()
        self.config_user.set(config.get("smtp_user", ""))
        self.config_pass.set(config.get("smtp_password", ""))
        self.config_subject.set(config.get("email_subject", ""))
        self.initial_body = config.get("email_body", "")

    def setup_ui(self):
        # Configurar grid principal (Sidebar + Content)
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        
        # === SIDEBAR ===
        self.sidebar_frame = ctk.CTkFrame(self, width=220, corner_radius=0, fg_color=("gray90", "gray13"))
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(4, weight=1) # Empujar hacia arriba
        
        lbl_logo = ctk.CTkLabel(self.sidebar_frame, text="SEMS Pro", font=ctk.CTkFont(size=28, weight="bold"))
        lbl_logo.grid(row=0, column=0, padx=20, pady=(30, 40))
        
        self.btn_nav_home = ctk.CTkButton(self.sidebar_frame, text="🚀 Envío Masivo", font=self.font_label, fg_color="transparent", text_color=("gray10", "gray90"), hover_color=("gray70", "gray30"), anchor="w", command=self.show_home)
        self.btn_nav_home.grid(row=1, column=0, padx=20, pady=10, sticky="ew")
        
        self.btn_nav_config = ctk.CTkButton(self.sidebar_frame, text="⚙️ Configuración", font=self.font_label, fg_color="transparent", text_color=("gray10", "gray90"), hover_color=("gray70", "gray30"), anchor="w", command=self.show_config)
        self.btn_nav_config.grid(row=2, column=0, padx=20, pady=10, sticky="ew")
        
        # === CONTENIDO PRINCIPAL ===
        self.main_container = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.main_container.grid(row=0, column=1, sticky="nsew", padx=30, pady=30)
        self.main_container.grid_rowconfigure(0, weight=1)
        self.main_container.grid_columnconfigure(0, weight=1)
        
        # Crear frames de las vistas
        self.home_frame = ctk.CTkFrame(self.main_container, fg_color="transparent")
        self.config_frame = ctk.CTkFrame(self.main_container, fg_color="transparent")
        
        self.setup_home_view()
        self.setup_config_view()
        
        # Iniciar en Home
        self.show_home()

    def show_home(self):
        self.config_frame.grid_forget()
        self.home_frame.grid(row=0, column=0, sticky="nsew")
        self.btn_nav_home.configure(fg_color=("gray75", "gray25"))
        self.btn_nav_config.configure(fg_color="transparent")

    def show_config(self):
        self.home_frame.grid_forget()
        self.config_frame.grid(row=0, column=0, sticky="nsew")
        self.btn_nav_config.configure(fg_color=("gray75", "gray25"))
        self.btn_nav_home.configure(fg_color="transparent")
        
    def setup_home_view(self):
        # Header
        lbl_title = ctk.CTkLabel(self.home_frame, text="Panel de Control", font=self.font_title)
        lbl_title.pack(anchor="w", pady=(0, 20))
        
        # Card 1: Archivos (Gris más claro para contrastar)
        card_archivos = ctk.CTkFrame(self.home_frame, corner_radius=15, fg_color=("gray85", "gray17"))
        card_archivos.pack(fill="x", pady=(0, 20), ipady=10)
        card_archivos.grid_columnconfigure(1, weight=1)
        
        ctk.CTkLabel(card_archivos, text="📂 Archivo de Datos (CSV):", font=self.font_label).grid(row=0, column=0, padx=20, pady=(25,10), sticky="w")
        ctk.CTkEntry(card_archivos, textvariable=self.csv_path, font=self.font_text, height=35).grid(row=0, column=1, padx=(0, 10), pady=(25,10), sticky="ew")
        ctk.CTkButton(card_archivos, text="Examinar", font=self.font_text, width=100, height=35, fg_color="#3b82f6", hover_color="#2563eb", command=self.browse_csv).grid(row=0, column=2, padx=20, pady=(25,10))
        
        ctk.CTkLabel(card_archivos, text="📄 Directorio de PDFs:", font=self.font_label).grid(row=1, column=0, padx=20, pady=(10,25), sticky="w")
        ctk.CTkEntry(card_archivos, textvariable=self.pdf_dir, font=self.font_text, height=35).grid(row=1, column=1, padx=(0, 10), pady=(10,25), sticky="ew")
        ctk.CTkButton(card_archivos, text="Examinar", font=self.font_text, width=100, height=35, fg_color="#3b82f6", hover_color="#2563eb", command=self.browse_pdf_dir).grid(row=1, column=2, padx=20, pady=(10,25))
        
        # Card 2: Status
        card_status = ctk.CTkFrame(self.home_frame, corner_radius=15, fg_color=("gray85", "gray17"))
        card_status.pack(fill="x", pady=(0, 20), ipady=10)
        
        self.progress_bar = ctk.CTkProgressBar(card_status, height=15, progress_color="#10b981")
        self.progress_bar.pack(fill="x", padx=30, pady=(25, 10))
        self.progress_bar.set(0)
        
        self.lbl_status = ctk.CTkLabel(card_status, text="Listo para iniciar...", font=self.font_status, text_color="gray")
        self.lbl_status.pack(pady=(0, 15))
        
        # Botón Iniciar (Destacado)
        self.btn_start = ctk.CTkButton(
            self.home_frame, text="▶ INICIAR PROCESO", font=ctk.CTkFont(family="Segoe UI", size=18, weight="bold"),
            fg_color="#10b981", hover_color="#059669", text_color_disabled="#ffffff", height=60, corner_radius=15, command=self.start_process
        )
        self.btn_start.pack(pady=10, fill="x")

    def setup_config_view(self):
        lbl_title = ctk.CTkLabel(self.config_frame, text="Ajustes de Servidor SMTP", font=self.font_title)
        lbl_title.pack(anchor="w", pady=(0, 20))
        
        # Card Credenciales
        card_creds = ctk.CTkFrame(self.config_frame, corner_radius=15, fg_color=("gray85", "gray17"))
        card_creds.pack(fill="x", pady=(0, 20), ipady=10)
        card_creds.grid_columnconfigure(1, weight=1)
        
        ctk.CTkLabel(card_creds, text="Correo Remitente:", font=self.font_label).grid(row=0, column=0, padx=20, pady=(25, 15), sticky="w")
        ctk.CTkEntry(card_creds, textvariable=self.config_user, font=self.font_text, height=35, placeholder_text="ej. ventas@empresa.com").grid(row=0, column=1, padx=20, pady=(25, 15), sticky="ew")
        
        ctk.CTkLabel(card_creds, text="Código de App (Google):", font=self.font_label).grid(row=1, column=0, padx=20, pady=(0, 25), sticky="w")
        ctk.CTkEntry(card_creds, textvariable=self.config_pass, show="*", font=self.font_text, height=35, placeholder_text="Contraseña de 16 caracteres").grid(row=1, column=1, padx=20, pady=(0, 25), sticky="ew")

        # Card Plantilla
        card_tpl = ctk.CTkFrame(self.config_frame, corner_radius=15, fg_color=("gray85", "gray17"))
        card_tpl.pack(fill="both", expand=True, pady=(0, 20))
        card_tpl.grid_columnconfigure(1, weight=1)
        
        ctk.CTkLabel(card_tpl, text="Asunto:", font=self.font_label).grid(row=0, column=0, padx=20, pady=(25, 15), sticky="w")
        ctk.CTkEntry(card_tpl, textvariable=self.config_subject, font=self.font_text, height=35).grid(row=0, column=1, padx=20, pady=(25, 15), sticky="ew")
        
        ctk.CTkLabel(card_tpl, text="Cuerpo:", font=self.font_label).grid(row=1, column=0, padx=20, pady=(0, 25), sticky="nw")
        self.txt_body = ctk.CTkTextbox(card_tpl, font=self.font_text)
        self.txt_body.grid(row=1, column=1, padx=20, pady=(0, 25), sticky="nsew")
        self.txt_body.insert("0.0", self.initial_body)
        
        btn_save = ctk.CTkButton(self.config_frame, text="💾 Guardar Configuración", font=self.font_label, height=50, corner_radius=15, command=self.save_settings)
        btn_save.pack(pady=0, fill="x")

    def browse_csv(self):
        filename = filedialog.askopenfilename(filetypes=[("CSV files", "*.csv")])
        if filename: self.csv_path.set(filename)
            
    def browse_pdf_dir(self):
        directory = filedialog.askdirectory()
        if directory: self.pdf_dir.set(directory)

    def save_settings(self):
        body = self.txt_body.get("0.0", "end").strip()
        success = ConfigManager.save_config(
            self.config_user.get(), self.config_pass.get(), self.config_subject.get(), body
        )
        if success:
            messagebox.showinfo("Éxito", "Configuración guardada correctamente.")
        else:
            messagebox.showerror("Error", "No se pudo guardar la configuración.")

    def start_process(self):
        if not self.csv_path.get() or not self.pdf_dir.get():
            messagebox.showwarning("Atención", "Selecciona el CSV y la carpeta de PDFs.")
            return
            
        config = ConfigManager.get_config()
        if not config.get("smtp_user") or not config.get("smtp_password"):
            messagebox.showwarning("Atención", "Ve a la pestaña de Configuración e ingresa tus credenciales SMTP primero.")
            return

        self.btn_start.configure(state="disabled", fg_color="#4b5563")
        self.progress_bar.set(0)
        self.lbl_status.configure(text="Procesando...")
        
        threading.Thread(target=self.run_workflow, daemon=True).start()
        
    def update_ui_status(self, text, progress=None):
        self.lbl_status.configure(text=text)
        if progress is not None:
            self.progress_bar.set(progress)

    def run_workflow(self, records_to_process=None):
        try:
            if records_to_process is None:
                records = DataManager.load_csv(self.csv_path.get())
            else:
                records = records_to_process
            
            total = len(records)
            
            # Refrescar config antes de enviar
            config = ConfigManager.get_config()
            subject_template = config.get("email_subject", "")
            
            errores = []
            records_fallidos = []
            
            email_service = EmailService()
            self.after(0, self.update_ui_status, "Conectando al servidor SMTP...")
            email_service.connect()
            
            for i, record in enumerate(records):
                email = str(record.get("email", "")).strip()
                id_archivo = str(record.get("id_archivo", "")).strip()
                id_servicio = str(record.get("id_servicio", "")).strip()
                
                # Nueva lógica: La contraseña será la cédula
                cedula = str(record.get("cedula", "")).strip()
                
                # Validar existencia de datos mínimos
                if not email or not id_archivo or not cedula:
                    logger.error(f"Fila {i+1} omitida: Faltan datos (email, id_archivo o cedula).")
                    continue
                
                dynamic_password = cedula
                
                if not id_archivo.lower().endswith(".pdf"): id_archivo += ".pdf"
                
                input_pdf = os.path.join(self.pdf_dir.get(), id_archivo)
                if not os.path.exists(input_pdf):
                    logger.error(f"Falta el archivo PDF: {input_pdf} (Destino: {mask_email(email)})")
                    errores.append(f"{email}: PDF no encontrado ({id_archivo})")
                    records_fallidos.append(record)
                    self.after(0, self.update_ui_status, f"Procesando {i+1} de {total}: {email} (Omitido: Sin PDF)", (i + 1) / total)
                    continue
                
                temp_pdf = os.path.join(self.pdf_dir.get(), f"temp_{id_archivo}")
                
                self.after(0, self.update_ui_status, f"Procesando {i+1} de {total}: {email}")
                
                try:
                    # Encriptación con la clave dinámica y única
                    PDFCrypto.encrypt_pdf(input_pdf, temp_pdf, dynamic_password)
                    
                    # Formatear el asunto
                    subject = subject_template.format(id_servicio=id_servicio)
                    
                    email_service.send_email_with_attachment(email, subject, temp_pdf, filename_override=id_archivo)
                    logger.info(f"Éxito: {mask_email(email)}")
                except Exception as e:
                    logger.error(f"Fallo con {mask_email(email)}: {str(e)}")
                    errores.append(f"{email}: Error ({str(e)})")
                    records_fallidos.append(record)
                finally:
                    PDFCrypto.secure_cleanup(temp_pdf)
                    
                self.after(0, self.update_ui_status, f"Procesando {i+1} de {total}: {email}", (i + 1) / total)
                
            email_service.disconnect()
                
            self.after(0, self.update_ui_status, "¡Proceso masivo completado!")
            
            if errores:
                self.after(0, lambda: self.show_results_modal(errores, total, records_fallidos))
            else:
                self.after(0, lambda: messagebox.showinfo("Completado", "El proceso ha finalizado con éxito sin errores."))
            
        except Exception as e:
            self.after(0, self.update_ui_status, "Error crítico en el proceso.")
            self.after(0, lambda e=e: messagebox.showerror("Error", f"Ocurrió un error: {str(e)}"))
            
        finally:
            self.after(0, lambda: self.btn_start.configure(state="normal", fg_color="#10b981"))

    def show_results_modal(self, errores, total, records_fallidos):
        modal = ctk.CTkToplevel(self)
        modal.title("Reporte de Envíos")
        modal.geometry("600x520")
        modal.resizable(False, False)
        
        modal.transient(self)
        modal.grab_set()

        lbl_title = ctk.CTkLabel(modal, text="⚠️ Atención Requerida", font=ctk.CTkFont(size=24, weight="bold"), text_color="#f59e0b")
        lbl_title.pack(pady=(25, 10))

        exitosos = total - len(errores)
        
        # Tarjeta de Resumen
        card_summary = ctk.CTkFrame(modal, corner_radius=15, fg_color=("gray85", "gray17"))
        card_summary.pack(fill="x", padx=30, pady=(10, 20), ipady=10)
        
        lbl_total = ctk.CTkLabel(card_summary, text=f"📊 Total: {total}", font=self.font_label)
        lbl_total.pack(side="left", expand=True)
        lbl_success = ctk.CTkLabel(card_summary, text=f"✅ Éxitos: {exitosos}", font=self.font_label, text_color="#10b981")
        lbl_success.pack(side="left", expand=True)
        lbl_err = ctk.CTkLabel(card_summary, text=f"❌ Errores: {len(errores)}", font=self.font_label, text_color="#ef4444")
        lbl_err.pack(side="left", expand=True)

        # Textbox con los errores
        txt_errors = ctk.CTkTextbox(modal, width=540, height=230, font=self.font_text, corner_radius=10, fg_color=("gray90", "gray13"))
        txt_errors.pack(pady=10, padx=30)
        
        report_text = "--- REPORTE DE ERRORES ---\n\n"
        report_text += "\n".join(errores)
        
        txt_errors.insert("0.0", report_text)
        txt_errors.configure(state="disabled") # Solo lectura

        def copy_to_clipboard():
            self.clipboard_clear()
            self.clipboard_append(report_text)
            messagebox.showinfo("Copiado", "El reporte ha sido copiado al portapapeles.", parent=modal)

        def retry_failed():
            modal.destroy()
            self.btn_start.configure(state="disabled", fg_color="#4b5563")
            self.progress_bar.set(0)
            self.lbl_status.configure(text=f"Reintentando {len(records_fallidos)} envíos fallidos...")
            threading.Thread(target=self.run_workflow, args=(records_fallidos,), daemon=True).start()

        # Botones en la parte inferior
        btn_frame = ctk.CTkFrame(modal, fg_color="transparent")
        btn_frame.pack(pady=(15, 20), fill="x", padx=30)
        
        btn_copy = ctk.CTkButton(btn_frame, text="📋 Copiar Reporte", command=copy_to_clipboard, width=160, height=45, corner_radius=10, fg_color="#4b5563", hover_color="#374151")
        btn_copy.pack(side="left", padx=10, expand=True)

        if records_fallidos:
            btn_retry = ctk.CTkButton(btn_frame, text="🔄 Reintentar Fallidos", command=retry_failed, width=160, height=45, corner_radius=10, font=ctk.CTkFont(weight="bold"), fg_color="#f59e0b", hover_color="#d97706", text_color="white")
            btn_retry.pack(side="right", padx=10, expand=True)
