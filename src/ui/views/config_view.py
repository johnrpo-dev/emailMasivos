import customtkinter as ctk
from tkinter import messagebox
from src.config.config_manager import ConfigManager
from src.utils.logger import mask_email

class ConfigView(ctk.CTkFrame):
    """Componente vista de Configuración SMTP modular."""
    def __init__(self, parent, controller):
        super().__init__(parent, fg_color="transparent")
        self.controller = controller
        
        # Tipografías del controller
        self.font_title = controller.font_title
        self.font_label = controller.font_label
        self.font_text = controller.font_text
        
        self.setup_layout()
        
    def setup_layout(self):
        lbl_title = ctk.CTkLabel(self, text="Ajustes de Servidor SMTP", font=self.font_title, text_color=("#0f172a", "#f8fafc"))
        lbl_title.pack(anchor="w", pady=(0, 2))
        
        lbl_subtitle = ctk.CTkLabel(self, text="Configure las credenciales SMTP de su proveedor y la plantilla de correo", font=ctk.CTkFont(family="Segoe UI", size=13), text_color=("#64748b", "#94a3b8"))
        lbl_subtitle.pack(anchor="w", pady=(0, 20))
        
        # Contenedor scrollable para las tarjetas de configuración
        scroll_container = ctk.CTkScrollableFrame(self, fg_color="transparent", border_width=0)
        scroll_container.pack(fill="both", expand=True, pady=(0, 15))

        # Card Credenciales
        card_creds = ctk.CTkFrame(scroll_container, corner_radius=16, fg_color=("#ffffff", "#0e1322"), border_width=1, border_color=("#e2e8f0", "#1e293b"))
        card_creds.pack(fill="x", pady=(0, 20), ipady=5)
        card_creds.grid_columnconfigure(1, weight=1)
        
        ctk.CTkLabel(card_creds, text="Correo Remitente:", font=self.font_label, text_color=("#334155", "#cbd5e1")).grid(row=0, column=0, padx=20, pady=(20, 10), sticky="w")
        self.entry_user = ctk.CTkEntry(card_creds, textvariable=self.controller.config_user, font=self.font_text, height=36, fg_color=("#f8fafc", "#070a13"), border_color=("#cbd5e1", "#1e293b"), placeholder_text="ej. ventas@empresa.com")
        self.entry_user.grid(row=0, column=1, padx=20, pady=(20, 10), sticky="ew")
        self.entry_user.bind("<FocusIn>", self.on_focus_in)
        self.entry_user.bind("<FocusOut>", self.on_focus_out)
        
        ctk.CTkLabel(card_creds, text="Código de App:", font=self.font_label, text_color=("#334155", "#cbd5e1")).grid(row=1, column=0, padx=20, pady=(0, 10), sticky="w")
        ctk.CTkEntry(card_creds, textvariable=self.controller.config_pass, show="*", font=self.font_text, height=36, fg_color=("#f8fafc", "#070a13"), border_color=("#cbd5e1", "#1e293b"), placeholder_text="Contraseña de 16 caracteres").grid(row=1, column=1, padx=20, pady=(0, 10), sticky="ew")
        
        ctk.CTkLabel(card_creds, text="Nombre del Remitente:", font=self.font_label, text_color=("#334155", "#cbd5e1")).grid(row=2, column=0, padx=20, pady=(0, 20), sticky="w")
        ctk.CTkEntry(card_creds, textvariable=self.controller.config_sender_name, font=self.font_text, height=36, fg_color=("#f8fafc", "#070a13"), border_color=("#cbd5e1", "#1e293b"), placeholder_text="ej. SEMS Pro").grid(row=2, column=1, padx=20, pady=(0, 20), sticky="ew")

        # Card Plantilla
        card_tpl = ctk.CTkFrame(scroll_container, corner_radius=16, fg_color=("#ffffff", "#0e1322"), border_width=1, border_color=("#e2e8f0", "#1e293b"))
        card_tpl.pack(fill="both", expand=True, pady=(0, 20))
        card_tpl.grid_columnconfigure(1, weight=1)
        card_tpl.grid_rowconfigure(2, weight=1)
        
        ctk.CTkLabel(card_tpl, text="Asunto del Correo:", font=self.font_label, text_color=("#334155", "#cbd5e1")).grid(row=0, column=0, padx=20, pady=(20, 10), sticky="w")
        ctk.CTkEntry(card_tpl, textvariable=self.controller.config_subject, font=self.font_text, height=36, fg_color=("#f8fafc", "#070a13"), border_color=("#cbd5e1", "#1e293b")).grid(row=0, column=1, padx=20, pady=(20, 10), sticky="ew")
        
        ctk.CTkLabel(card_tpl, text="Logo de Empresa (Opcional):", font=self.font_label, text_color=("#334155", "#cbd5e1")).grid(row=1, column=0, padx=20, pady=(0, 10), sticky="w")
        
        logo_frame = ctk.CTkFrame(card_tpl, fg_color="transparent")
        logo_frame.grid(row=1, column=1, padx=20, pady=(0, 10), sticky="ew")
        logo_frame.grid_columnconfigure(0, weight=1)
        
        self.entry_logo = ctk.CTkEntry(logo_frame, textvariable=self.controller.config_logo_path, font=self.font_text, height=36, fg_color=("#f8fafc", "#070a13"), border_color=("#cbd5e1", "#1e293b"))
        self.entry_logo.grid(row=0, column=0, sticky="ew", padx=(0, 10))
        
        btn_browse_logo = ctk.CTkButton(logo_frame, text="📁 Buscar", width=80, height=36, font=self.font_label, fg_color=("#4b5563", "#1e293b"), hover_color=("#374151", "#2d3748"), command=self.browse_logo)
        btn_browse_logo.grid(row=0, column=1, sticky="e")
        
        ctk.CTkLabel(card_tpl, text="Cuerpo del Correo:", font=self.font_label, text_color=("#334155", "#cbd5e1")).grid(row=2, column=0, padx=20, pady=(0, 20), sticky="nw")
        self.txt_body = ctk.CTkTextbox(card_tpl, font=self.font_text, fg_color=("#f8fafc", "#070a13"), border_color=("#cbd5e1", "#1e293b"), border_width=1, corner_radius=10)
        self.txt_body.grid(row=2, column=1, padx=20, pady=(0, 20), sticky="nsew")
        self.txt_body.insert("0.0", self.controller.initial_body)
        
        btn_save = ctk.CTkButton(self, text="💾 Guardar Configuración", font=ctk.CTkFont(family="Segoe UI", size=15, weight="bold"), fg_color=("#4f46e5", "#6366f1"), hover_color=("#4338ca", "#4f46e5"), height=48, corner_radius=12, command=self.save_settings)
        btn_save.pack(pady=0, fill="x")
        
    def on_focus_in(self, event):
        self.controller.config_user.set(self.controller._real_smtp_user)

    def on_focus_out(self, event):
        val = self.controller.config_user.get().strip()
        if val and "***" not in val:
            self.controller._real_smtp_user = val
        self.controller.config_user.set(mask_email(self.controller._real_smtp_user))

    def save_settings(self):
        val = self.controller.config_user.get().strip()
        if val and "***" not in val:
            self.controller._real_smtp_user = val
            
        body = self.txt_body.get("0.0", "end").strip()
        provider = self.controller.smtp_providers.get(self.controller.config_provider.get(), {"host": "smtp.gmail.com", "port": 587})
        success = ConfigManager.save_config(
            self.controller._real_smtp_user, self.controller.config_pass.get(),
            provider["host"], str(provider["port"]),
            self.controller.config_subject.get(), body,
            send_delay=self.controller.config_delay.get(),
            sender_name=self.controller.config_sender_name.get().strip() or "SEMS Pro",
            logo_path=self.controller.config_logo_path.get().strip()
        )
        if success:
            messagebox.showinfo("Éxito", "Configuración guardada correctamente.")
            self.controller.config_user.set(mask_email(self.controller._real_smtp_user))
        else:
            messagebox.showerror("Error", "No se pudo guardar la configuración.")

    def browse_logo(self):
        from tkinter import filedialog
        path = filedialog.askopenfilename(
            parent=self,
            title="Seleccionar Logo de la Empresa",
            filetypes=[("Imágenes", "*.png *.jpg *.jpeg *.gif *.webp")]
        )
        if path:
            self.controller.config_logo_path.set(path)
