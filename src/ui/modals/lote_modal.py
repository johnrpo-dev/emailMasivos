import customtkinter as ctk
from src.ui import theme
from src.ui.components import Card, StatusBadge, PrimaryButton, SecondaryButton, WarningButton, apply_window_icon, center_window

class LoteModal(ctk.CTkToplevel):
    """Modal con la lista detallada de envíos de un lote anterior."""
    def __init__(self, parent, lote_id, lote_data):
        super().__init__(parent)
        self.lote_data = lote_data

        self.title(f"Detalle de Envío - Lote #{lote_id}")
        center_window(self, 750, 580, min_w=640, min_h=480)
        self.resizable(True, True)
        self.transient(parent)
        self.grab_set()
        self.configure(fg_color=theme.APP_BG)
        apply_window_icon(self)

        # Título
        lbl_title = ctk.CTkLabel(
            self, text=f"Detalle del Lote #{lote_id}",
            font=theme.font("h1"), text_color=theme.TEXT
        )
        lbl_title.pack(pady=(20, 5))

        # Tarjeta de datos del lote
        info_frame = Card(self)
        info_frame.pack(fill="x", padx=30, pady=10, ipady=5)

        info_str = f"Archivo: {lote_data['csv_nombre']}   |   Fecha: {lote_data['fecha']}"
        ctk.CTkLabel(info_frame, text=info_str, font=theme.font("body"), text_color=theme.TEXT).pack(pady=5)

        stats_str = f"Total Registros: {lote_data['total_registros']}   -   Exitosos: {lote_data['exitosos']}   -   Fallidos: {lote_data['fallidos']}"
        ctk.CTkLabel(
            info_frame, text=stats_str, font=theme.font("body_strong"),
            text_color=theme.PRIMARY
        ).pack(pady=(0, 5))

        # Barra inferior de botones: se empaqueta primero con side="bottom" para
        # reservar su altura completa; ante falta de espacio se encoge la lista.
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(side="bottom", pady=15, fill="x", padx=30)

        btn_close = SecondaryButton(
            btn_frame, text="Cerrar", width=120, height=42, command=self.destroy
        )
        btn_close.pack(side="left", padx=5, expand=True)

        raw_records = lote_data.get("raw_records_fallidos")
        raw_email_corrections = lote_data.get("raw_email_corrections", {})
        raw_pdf_corrections = lote_data.get("raw_pdf_corrections", {})

        if raw_records:
            if raw_email_corrections or raw_pdf_corrections:
                btn_correct = PrimaryButton(
                    btn_frame, text="Corregir y Reintentar", width=180, height=42,
                    command=self.handle_correct_and_retry
                )
                btn_correct.pack(side="left", padx=5, expand=True)

            btn_retry = WarningButton(
                btn_frame, text="Reintentar Fallidos",
                width=160, height=42, command=self.handle_retry
            )
            btn_retry.pack(side="right", padx=5, expand=True)

        # Scrollable Frame con los envíos del lote
        envios_scroll = ctk.CTkScrollableFrame(
            self, corner_radius=theme.RAD_LG, fg_color=theme.SURFACE,
            border_width=1, border_color=theme.BORDER
        )
        envios_scroll.pack(fill="both", expand=True, padx=30, pady=10)

        envios = list(lote_data.get('envios', []))  # Usamos copia superficial para seguridad
        if not envios:
            ctk.CTkLabel(envios_scroll, text="No hay registros individuales para este lote.", font=theme.font("status"), text_color=theme.TEXT_MUTED).pack(pady=40)
        else:
            for ev in envios:
                row_frame = ctk.CTkFrame(
                    envios_scroll, corner_radius=theme.RAD_MD,
                    fg_color=theme.SURFACE_ALT, border_width=1, border_color=theme.BORDER
                )
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
                lbl_desc = ctk.CTkLabel(row_frame, text=desc, font=theme.font("body"), justify="left", anchor="w", text_color=theme.TEXT)
                lbl_desc.grid(row=0, column=0, padx=15, pady=8, sticky="w")

                StatusBadge.from_estado(row_frame, estado).grid(row=0, column=1, padx=20, pady=8, sticky="e")

                # Detalles del error
                if detalles:
                    lbl_det = ctk.CTkLabel(row_frame, text=f"Detalle: {detalles}", font=theme.font("caption"), text_color=theme.DANGER, justify="left", anchor="w")
                    lbl_det.grid(row=1, column=0, columnspan=2, padx=15, pady=(0, 8), sticky="w")

    def handle_retry(self):
        raw_records = self.lote_data.get("raw_records_fallidos")
        if raw_records:
            self.master.workflow_controller.retry_batch(
                raw_records,
                self.lote_data.get("raw_email_corrections"),
                self.lote_data.get("raw_pdf_corrections"),
                apply_corrections=False
            )
            self.destroy()

    def handle_correct_and_retry(self):
        raw_records = self.lote_data.get("raw_records_fallidos")
        if raw_records:
            self.master.workflow_controller.retry_batch(
                raw_records,
                self.lote_data.get("raw_email_corrections"),
                self.lote_data.get("raw_pdf_corrections"),
                apply_corrections=True
            )
            self.destroy()
