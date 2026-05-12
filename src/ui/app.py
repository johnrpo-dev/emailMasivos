# pyrefly: ignore [missing-import]
import customtkinter as ctk
from tkinter import filedialog, messagebox
import os
import threading
from src.core.data_manager import DataManager
from src.core.pdf_crypto import PDFCrypto
from src.core.email_service import EmailService
from src.config.config_manager import ConfigManager
from src.utils.logger import logger

class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Sistema de Envío Masivo Seguro")
        self.geometry("750x650")
        self.resizable(False, False)
        
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
        # Header global
        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.pack(pady=(20, 10), fill="x")
        lbl_title = ctk.CTkLabel(header_frame, text="Envío de PDFs Cifrados", font=self.font_title)
        lbl_title.pack()

        # Tabview principal
        self.tabview = ctk.CTkTabview(self, width=650, height=500, corner_radius=15)
        self.tabview.pack(padx=20, pady=10, fill="both", expand=True)
        
        self.tab_envio = self.tabview.add("Envío Masivo")
        self.tab_config = self.tabview.add("Configuración")
        
        self.setup_envio_tab()
        self.setup_config_tab()
        
    def setup_envio_tab(self):
        card_frame = ctk.CTkFrame(self.tab_envio, fg_color="transparent")
        card_frame.pack(pady=10, padx=20, fill="x")
        card_frame.grid_columnconfigure(1, weight=1)
        
        # Archivos
        ctk.CTkLabel(card_frame, text="Archivo CSV:", font=self.font_label).grid(row=0, column=0, padx=10, pady=20, sticky="w")
        ctk.CTkEntry(card_frame, textvariable=self.csv_path, font=self.font_text, height=35).grid(row=0, column=1, padx=10, pady=20, sticky="ew")
        ctk.CTkButton(card_frame, text="Examinar", font=self.font_text, width=100, height=35, command=self.browse_csv).grid(row=0, column=2, padx=10, pady=20)
        
        ctk.CTkLabel(card_frame, text="Carpeta PDFs:", font=self.font_label).grid(row=1, column=0, padx=10, pady=10, sticky="w")
        ctk.CTkEntry(card_frame, textvariable=self.pdf_dir, font=self.font_text, height=35).grid(row=1, column=1, padx=10, pady=10, sticky="ew")
        ctk.CTkButton(card_frame, text="Examinar", font=self.font_text, width=100, height=35, command=self.browse_pdf_dir).grid(row=1, column=2, padx=10, pady=10)
        
        # Progreso
        progress_frame = ctk.CTkFrame(self.tab_envio, fg_color="transparent")
        progress_frame.pack(pady=20, fill="x", padx=30)
        self.progress_bar = ctk.CTkProgressBar(progress_frame, height=12, progress_color="#10b981")
        self.progress_bar.pack(fill="x", pady=10)
        self.progress_bar.set(0)
        self.lbl_status = ctk.CTkLabel(progress_frame, text="Listo para iniciar...", font=self.font_status, text_color="gray")
        self.lbl_status.pack()
        
        # Botón Iniciar
        self.btn_start = ctk.CTkButton(
            self.tab_envio, text="INICIAR PROCESO", font=ctk.CTkFont(family="Segoe UI", size=16, weight="bold"),
            fg_color="#10b981", hover_color="#059669", text_color_disabled="#ffffff", height=50, corner_radius=10, command=self.start_process
        )
        self.btn_start.pack(pady=20, padx=50, fill="x")

    def setup_config_tab(self):
        # Credenciales
        frame_creds = ctk.CTkFrame(self.tab_config)
        frame_creds.pack(pady=10, padx=20, fill="x")
        frame_creds.grid_columnconfigure(1, weight=1)
        
        ctk.CTkLabel(frame_creds, text="Correo Remitente:", font=self.font_label).grid(row=0, column=0, padx=10, pady=15, sticky="w")
        ctk.CTkEntry(frame_creds, textvariable=self.config_user, font=self.font_text, placeholder_text="ej. ventas@empresa.com").grid(row=0, column=1, padx=10, pady=15, sticky="ew")
        
        ctk.CTkLabel(frame_creds, text="Código de App:", font=self.font_label).grid(row=1, column=0, padx=10, pady=10, sticky="w")
        ctk.CTkEntry(frame_creds, textvariable=self.config_pass, show="*", font=self.font_text, placeholder_text="Contraseña de 16 letras").grid(row=1, column=1, padx=10, pady=10, sticky="ew")

        # Plantilla
        frame_tpl = ctk.CTkFrame(self.tab_config)
        frame_tpl.pack(pady=10, padx=20, fill="both", expand=True)
        frame_tpl.grid_columnconfigure(1, weight=1)
        
        ctk.CTkLabel(frame_tpl, text="Asunto:", font=self.font_label).grid(row=0, column=0, padx=10, pady=15, sticky="w")
        ctk.CTkEntry(frame_tpl, textvariable=self.config_subject, font=self.font_text).grid(row=0, column=1, padx=10, pady=15, sticky="ew")
        
        ctk.CTkLabel(frame_tpl, text="Cuerpo:", font=self.font_label).grid(row=1, column=0, padx=10, pady=10, sticky="nw")
        self.txt_body = ctk.CTkTextbox(frame_tpl, font=self.font_text, height=130)
        self.txt_body.grid(row=1, column=1, padx=10, pady=10, sticky="nsew")
        self.txt_body.insert("0.0", self.initial_body)
        
        btn_save = ctk.CTkButton(self.tab_config, text="Guardar Configuración", font=self.font_label, height=40, command=self.save_settings)
        btn_save.pack(pady=10)

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

    def run_workflow(self):
        try:
            records = DataManager.load_csv(self.csv_path.get())
            total = len(records)
            
            # Refrescar config antes de enviar
            config = ConfigManager.get_config()
            subject_template = config.get("email_subject", "")
            
            errores = []
            
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
                    logger.error(f"Falta el archivo PDF: {input_pdf}")
                    errores.append(f"{email}: PDF no encontrado ({id_archivo})")
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
                    logger.info(f"Éxito: {email}")
                except Exception as e:
                    logger.error(f"Fallo con {email}: {str(e)}")
                    errores.append(f"{email}: Error ({str(e)})")
                finally:
                    PDFCrypto.secure_cleanup(temp_pdf)
                    
                self.after(0, self.update_ui_status, f"Procesando {i+1} de {total}: {email}", (i + 1) / total)
                
            email_service.disconnect()
                
            self.after(0, self.update_ui_status, "¡Proceso masivo completado!")
            
            if errores:
                self.after(0, lambda: self.show_results_modal(errores, total))
            else:
                self.after(0, lambda: messagebox.showinfo("Completado", "El proceso ha finalizado con éxito sin errores."))
            
        except Exception as e:
            self.after(0, self.update_ui_status, "Error crítico en el proceso.")
            self.after(0, lambda e=e: messagebox.showerror("Error", f"Ocurrió un error: {str(e)}"))
            
        finally:
            self.after(0, lambda: self.btn_start.configure(state="normal", fg_color="#10b981"))

    def show_results_modal(self, errores, total):
        modal = ctk.CTkToplevel(self)
        modal.title("Reporte de Errores del Envío")
        modal.geometry("550x450")
        modal.resizable(False, False)
        
        # Para evitar que el usuario interactúe con la ventana principal mientras está abierto
        modal.transient(self)
        modal.grab_set()

        lbl_title = ctk.CTkLabel(modal, text="Proceso Finalizado con Observaciones", font=self.font_title)
        lbl_title.pack(pady=(20, 10))

        exitosos = total - len(errores)
        lbl_summary = ctk.CTkLabel(modal, text=f"Total procesados: {total} | Éxitos: {exitosos} | Errores: {len(errores)}", font=self.font_label)
        lbl_summary.pack(pady=(0, 10))

        # Textbox con los errores
        txt_errors = ctk.CTkTextbox(modal, width=500, height=250, font=self.font_text)
        txt_errors.pack(pady=10, padx=20)
        
        report_text = "--- REPORTE DE ERRORES ---\n\n"
        report_text += "\n".join(errores)
        
        txt_errors.insert("0.0", report_text)
        txt_errors.configure(state="disabled") # Solo lectura

        def copy_to_clipboard():
            self.clipboard_clear()
            self.clipboard_append(report_text)
            messagebox.showinfo("Copiado", "El reporte ha sido copiado al portapapeles.", parent=modal)

        btn_copy = ctk.CTkButton(modal, text="Copiar Reporte", command=copy_to_clipboard)
        btn_copy.pack(pady=(10, 20))
