import customtkinter as ctk
from src.core.data_manager import DataManager
from src.config.config_manager import ConfigManager
from src.utils.logger import mask_email
from src.ui import theme, dialogs
from src.ui.components import Card, ThemedTextbox, apply_window_icon, center_window

class PreviewModal(ctk.CTkToplevel):
    """Modal de Vista Previa de Correo desacoplado de la ventana coordinadora."""
    def __init__(self, parent, csv_path_str):
        super().__init__(parent)

        self.title("Vista Previa de Correo")
        center_window(self, 600, 580, min_w=520, min_h=480)
        self.resizable(True, True)
        self.transient(parent)
        self.grab_set()
        self.configure(fg_color=theme.APP_BG)
        apply_window_icon(self)

        # Cargar y verificar datos del CSV
        try:
            records = DataManager.load_csv(csv_path_str)
        except Exception as e:
            dialogs.show_error(parent, "Error", f"No se pudo cargar el CSV: {str(e)}")
            self.destroy()
            return

        if not records:
            dialogs.show_warning(parent, "Atención", "El archivo CSV está vacío.")
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
            font=theme.font("h1"), text_color=theme.TEXT
        )
        lbl_title.pack(pady=(20, 10))

        # Contenedor de datos
        details_frame = Card(self)
        details_frame.pack(fill="x", padx=30, pady=10, ipady=5)
        details_frame.grid_columnconfigure(1, weight=1)

        rows = [
            ("Remitente:", "Cuenta SMTP configurada", theme.TEXT_SECONDARY),
            ("Destinatario:", mask_email(email), theme.PRIMARY),
            ("Adjunto:", f"{id_archivo} (Protegido con contraseña)", theme.TEXT_SECONDARY),
            ("Asunto:", subject, theme.TEXT),
        ]
        for i, (label, value, color) in enumerate(rows):
            ctk.CTkLabel(details_frame, text=label, font=theme.font("body_strong"), text_color=theme.TEXT).grid(row=i, column=0, padx=20, pady=8, sticky="w")
            ctk.CTkLabel(details_frame, text=value, font=theme.font("body"), text_color=color).grid(row=i, column=1, padx=20, pady=8, sticky="w")

        # Contenedor del cuerpo
        body_frame = Card(self)
        body_frame.pack(fill="both", expand=True, padx=30, pady=(10, 20))

        ctk.CTkLabel(body_frame, text="Cuerpo del Correo:", font=theme.font("body_strong"), text_color=theme.TEXT).pack(anchor="w", padx=20, pady=(15, 5))

        txt_body = ThemedTextbox(body_frame, corner_radius=theme.RAD_MD)
        txt_body.pack(fill="both", expand=True, padx=20, pady=(0, 20))
        txt_body.insert("0.0", body)
        txt_body.configure(state="disabled")
