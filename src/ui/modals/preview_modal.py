import customtkinter as ctk
from tkinter import messagebox
from src.core.data_manager import DataManager
from src.config.config_manager import ConfigManager
from src.utils.logger import mask_email

class PreviewModal(ctk.CTkToplevel):
    """Modal de Vista Previa de Correo desacoplado de la ventana coordinadora."""
    def __init__(self, parent, csv_path_str, remitente_email):
        super().__init__(parent)
        
        self.title("Vista Previa de Correo")
        self.geometry("600x580")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()
        self.configure(fg_color=("#f8fafc", "#080c14"))
        
        # Tipografías base
        self.font_label = ctk.CTkFont(family="Segoe UI", size=14, weight="bold")
        self.font_text = ctk.CTkFont(family="Segoe UI", size=13)
        
        # Cargar y verificar datos del CSV
        try:
            records = DataManager.load_csv(csv_path_str)
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo cargar el CSV: {str(e)}")
            self.destroy()
            return
            
        if not records:
            messagebox.showwarning("Atención", "El archivo CSV está vacío.")
            self.destroy()
            return
            
        # Tomar el primer registro de prueba
        record = records[0]
        email = str(record.get("email", "")).strip()
        id_archivo = str(record.get("id_archivo", "")).strip()
        id_servicio = str(record.get("id_servicio", "")).strip()
        
        # Cargar templates de correo
        config = ConfigManager.get_config()
        subject_template = config.get("email_subject", "")
        body_template = config.get("email_body", "")
        
        subject = subject_template.replace("{id_servicio}", id_servicio)
        body = body_template
        
        # Renderizado de componentes UI
        lbl_title = ctk.CTkLabel(
            self, text="Vista Previa de Correo", 
            font=ctk.CTkFont(family="Segoe UI", size=20, weight="bold"), 
            text_color=("#0f172a", "#f8fafc")
        )
        lbl_title.pack(pady=(20, 10))
        
        # Contenedor de datos
        details_frame = ctk.CTkFrame(self, corner_radius=16, fg_color=("#ffffff", "#0e1322"), border_width=1, border_color=("#e2e8f0", "#1e293b"))
        details_frame.pack(fill="x", padx=30, pady=10, ipady=5)
        details_frame.grid_columnconfigure(1, weight=1)
        
        ctk.CTkLabel(details_frame, text="Remitente:", font=self.font_label, text_color=("#334155", "#cbd5e1")).grid(row=0, column=0, padx=20, pady=8, sticky="w")
        ctk.CTkLabel(details_frame, text="Cuenta SMTP configurada", font=self.font_text, text_color=("#64748b", "#94a3b8")).grid(row=0, column=1, padx=20, pady=8, sticky="w")
        
        ctk.CTkLabel(details_frame, text="Destinatario:", font=self.font_label, text_color=("#334155", "#cbd5e1")).grid(row=1, column=0, padx=20, pady=8, sticky="w")
        ctk.CTkLabel(details_frame, text=mask_email(email), font=self.font_text, text_color=("#4f46e5", "#818cf8")).grid(row=1, column=1, padx=20, pady=8, sticky="w")
        
        ctk.CTkLabel(details_frame, text="Adjunto:", font=self.font_label, text_color=("#334155", "#cbd5e1")).grid(row=2, column=0, padx=20, pady=8, sticky="w")
        ctk.CTkLabel(details_frame, text=f"{id_archivo} (Protegido con contraseña)", font=self.font_text, text_color=("#64748b", "#94a3b8")).grid(row=2, column=1, padx=20, pady=8, sticky="w")
        
        ctk.CTkLabel(details_frame, text="Asunto:", font=self.font_label, text_color=("#334155", "#cbd5e1")).grid(row=3, column=0, padx=20, pady=8, sticky="w")
        ctk.CTkLabel(details_frame, text=subject, font=self.font_text, text_color=("#0f172a", "#f8fafc")).grid(row=3, column=1, padx=20, pady=8, sticky="w")
        
        # Contenedor del cuerpo
        body_frame = ctk.CTkFrame(self, corner_radius=16, fg_color=("#ffffff", "#0e1322"), border_width=1, border_color=("#e2e8f0", "#1e293b"))
        body_frame.pack(fill="both", expand=True, padx=30, pady=(10, 20))
        
        ctk.CTkLabel(body_frame, text="Cuerpo del Correo:", font=self.font_label, text_color=("#334155", "#cbd5e1")).pack(anchor="w", padx=20, pady=(15, 5))
        
        txt_body = ctk.CTkTextbox(body_frame, font=self.font_text, corner_radius=10, fg_color=("#f8fafc", "#070a13"), border_color=("#cbd5e1", "#1e293b"), border_width=1)
        txt_body.pack(fill="both", expand=True, padx=20, pady=(0, 20))
        txt_body.insert("0.0", body)
        txt_body.configure(state="disabled")
