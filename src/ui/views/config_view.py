import customtkinter as ctk
from src.config.config_manager import ConfigManager
from src.utils.logger import mask_email
from src.ui import theme, dialogs
from src.ui.components import Card, SectionHeader, PrimaryButton, SecondaryButton, ThemedEntry, ThemedTextbox

class ConfigView(ctk.CTkFrame):
    """Componente vista de Configuración SMTP modular."""
    def __init__(self, parent, controller):
        super().__init__(parent, fg_color="transparent")
        self.controller = controller
        self.setup_layout()

    def setup_layout(self):
        SectionHeader(
            self, "Ajustes de Servidor SMTP",
            "Configure las credenciales SMTP de su proveedor y la plantilla de correo"
        ).pack(anchor="w", fill="x", pady=(0, theme.SP_LG))

        # Contenedor scrollable para las tarjetas de configuración
        scroll_container = ctk.CTkScrollableFrame(self, fg_color="transparent", border_width=0)
        scroll_container.pack(fill="both", expand=True, pady=(0, 15))

        # Card Servidor y Envío (proveedor SMTP + pausa entre correos)
        card_server = Card(scroll_container)
        card_server.pack(fill="x", pady=(0, theme.SP_LG), ipady=5)
        card_server.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(card_server, text="Proveedor de Correo:", font=theme.font("body_strong"), text_color=theme.TEXT).grid(row=0, column=0, padx=20, pady=(20, 10), sticky="w")
        self.provider_menu = ctk.CTkOptionMenu(
            card_server,
            values=list(self.controller.smtp_providers.keys()),
            variable=self.controller.config_provider,
            font=theme.font("body"), height=theme.INPUT_H,
            fg_color=theme.SURFACE_ALT, text_color=theme.TEXT,
            button_color=theme.BTN_PRIMARY_FG, button_hover_color=theme.BTN_PRIMARY_HOVER,
            dropdown_font=theme.font("body"), dropdown_fg_color=theme.SURFACE,
            dropdown_text_color=theme.TEXT, dropdown_hover_color=theme.PRIMARY_SOFT
        )
        self.provider_menu.grid(row=0, column=1, padx=20, pady=(20, 10), sticky="w")

        ctk.CTkLabel(card_server, text="Pausa entre Envíos:", font=theme.font("body_strong"), text_color=theme.TEXT).grid(row=1, column=0, padx=20, pady=(0, 20), sticky="w")

        delay_frame = ctk.CTkFrame(card_server, fg_color="transparent")
        delay_frame.grid(row=1, column=1, padx=20, pady=(0, 20), sticky="ew")
        delay_frame.grid_columnconfigure(0, weight=1)

        try:
            delay_initial = max(1, min(10, int(float(self.controller.config_delay.get()))))
        except (ValueError, TypeError):
            delay_initial = 2

        self.delay_slider = ctk.CTkSlider(
            delay_frame, from_=1, to=10, number_of_steps=9,
            progress_color=theme.BTN_PRIMARY_FG, button_color=theme.BTN_PRIMARY_FG,
            button_hover_color=theme.BTN_PRIMARY_HOVER,
            command=self._on_delay_change
        )
        self.delay_slider.set(delay_initial)
        self.delay_slider.grid(row=0, column=0, sticky="ew", padx=(0, 12))

        self.lbl_delay_value = ctk.CTkLabel(
            delay_frame, text=f"{delay_initial} s", width=40,
            font=theme.font("body_strong"), text_color=theme.PRIMARY
        )
        self.lbl_delay_value.grid(row=0, column=1)

        # Card Credenciales
        card_creds = Card(scroll_container)
        card_creds.pack(fill="x", pady=(0, theme.SP_LG), ipady=5)
        card_creds.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(card_creds, text="Correo Remitente:", font=theme.font("body_strong"), text_color=theme.TEXT).grid(row=0, column=0, padx=20, pady=(20, 10), sticky="w")
        self.entry_user = ThemedEntry(card_creds, textvariable=self.controller.config_user, placeholder_text="ej. ventas@empresa.com")
        self.entry_user.grid(row=0, column=1, padx=20, pady=(20, 10), sticky="ew")
        self.entry_user.bind("<FocusIn>", self.on_focus_in)
        self.entry_user.bind("<FocusOut>", self.on_focus_out)

        ctk.CTkLabel(card_creds, text="Código de App:", font=theme.font("body_strong"), text_color=theme.TEXT).grid(row=1, column=0, padx=20, pady=(0, 10), sticky="w")
        ThemedEntry(card_creds, textvariable=self.controller.config_pass, show="*", placeholder_text="Contraseña de 16 caracteres").grid(row=1, column=1, padx=20, pady=(0, 10), sticky="ew")

        ctk.CTkLabel(card_creds, text="Nombre del Remitente:", font=theme.font("body_strong"), text_color=theme.TEXT).grid(row=2, column=0, padx=20, pady=(0, 20), sticky="w")
        ThemedEntry(card_creds, textvariable=self.controller.config_sender_name, placeholder_text="ej. SEMS Pro").grid(row=2, column=1, padx=20, pady=(0, 20), sticky="ew")

        # Card Plantilla
        card_tpl = Card(scroll_container)
        card_tpl.pack(fill="both", expand=True, pady=(0, theme.SP_LG))
        card_tpl.grid_columnconfigure(1, weight=1)
        card_tpl.grid_rowconfigure(2, weight=1)

        ctk.CTkLabel(card_tpl, text="Asunto del Correo:", font=theme.font("body_strong"), text_color=theme.TEXT).grid(row=0, column=0, padx=20, pady=(20, 10), sticky="w")
        ThemedEntry(card_tpl, textvariable=self.controller.config_subject).grid(row=0, column=1, padx=20, pady=(20, 10), sticky="ew")

        ctk.CTkLabel(card_tpl, text="Logo de Empresa (Opcional):", font=theme.font("body_strong"), text_color=theme.TEXT).grid(row=1, column=0, padx=20, pady=(0, 10), sticky="w")

        logo_frame = ctk.CTkFrame(card_tpl, fg_color="transparent")
        logo_frame.grid(row=1, column=1, padx=20, pady=(0, 10), sticky="ew")
        logo_frame.grid_columnconfigure(0, weight=1)

        self.entry_logo = ThemedEntry(logo_frame, textvariable=self.controller.config_logo_path)
        self.entry_logo.grid(row=0, column=0, sticky="ew", padx=(0, 10))

        SecondaryButton(logo_frame, text="Buscar", width=80, height=theme.INPUT_H, command=self.browse_logo).grid(row=0, column=1, sticky="e")

        ctk.CTkLabel(card_tpl, text="Cuerpo del Correo:", font=theme.font("body_strong"), text_color=theme.TEXT).grid(row=2, column=0, padx=20, pady=(0, 20), sticky="nw")
        self.txt_body = ThemedTextbox(card_tpl, corner_radius=theme.RAD_MD)
        self.txt_body.grid(row=2, column=1, padx=20, pady=(0, 20), sticky="nsew")
        self.txt_body.insert("0.0", self.controller.initial_body)

        # Card Seguridad PDF
        card_sec = Card(scroll_container)
        card_sec.pack(fill="x", pady=(0, theme.SP_LG), ipady=5)
        card_sec.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(card_sec, text="Seguridad de Contraseñas PDF:", font=theme.font("body_strong"), text_color=theme.TEXT).grid(row=0, column=0, columnspan=2, padx=20, pady=(15, 10), sticky="w")

        ctk.CTkLabel(card_sec, text="Prefijo de Contraseña:", font=theme.font("body_strong"), text_color=theme.TEXT).grid(row=1, column=0, padx=20, pady=(0, 10), sticky="w")
        ThemedEntry(card_sec, textvariable=self.controller.config_pdf_prefix, placeholder_text="ej. SEMS_").grid(row=1, column=1, padx=20, pady=(0, 10), sticky="ew")

        ctk.CTkLabel(card_sec, text="Sufijo de Contraseña:", font=theme.font("body_strong"), text_color=theme.TEXT).grid(row=2, column=0, padx=20, pady=(0, 15), sticky="w")
        ThemedEntry(card_sec, textvariable=self.controller.config_pdf_suffix, placeholder_text="ej. _2026").grid(row=2, column=1, padx=20, pady=(0, 15), sticky="ew")

        PrimaryButton(self, text="Guardar Configuración", height=48, command=self.save_settings).pack(pady=0, fill="x")

    def _on_delay_change(self, value):
        # El backend consume config_delay como StringVar: escribir entero en texto ("2", no "2.0")
        delay = int(round(value))
        self.controller.config_delay.set(str(delay))
        self.lbl_delay_value.configure(text=f"{delay} s")

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
            logo_path=self.controller.config_logo_path.get().strip(),
            pdf_password_prefix=self.controller.config_pdf_prefix.get().strip(),
            pdf_password_suffix=self.controller.config_pdf_suffix.get().strip()
        )
        if success:
            dialogs.show_success(self.controller, "Éxito", "Configuración guardada correctamente.")
            self.controller.config_user.set(mask_email(self.controller._real_smtp_user))
        else:
            dialogs.show_error(self.controller, "Error", "No se pudo guardar la configuración.")

    def browse_logo(self):
        from tkinter import filedialog
        path = filedialog.askopenfilename(
            parent=self,
            title="Seleccionar Logo de la Empresa",
            filetypes=[("Imágenes", "*.png *.jpg *.jpeg *.gif *.webp")]
        )
        if path:
            self.controller.config_logo_path.set(path)
