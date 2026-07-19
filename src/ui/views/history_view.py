import customtkinter as ctk
from src.ui import theme
from src.ui.components import Card, SectionHeader, StatusBadge, PrimaryButton, SecondaryButton, ThemedEntry
from src.ui.modals.lote_modal import LoteModal

class HistoryView(ctk.CTkFrame):
    """Componente modular de la vista de Historial de Auditoría con buscador HMAC."""
    def __init__(self, parent, controller):
        super().__init__(parent, fg_color="transparent")
        self.controller = controller
        self.setup_layout()

    def setup_layout(self):
        SectionHeader(
            self, "Historial de Auditoría",
            "Consulte el registro histórico y la trazabilidad de todos los envíos masivos realizados"
        ).pack(anchor="w", fill="x", pady=(0, theme.SP_LG))

        # Card del buscador
        search_card = Card(self)
        search_card.pack(fill="x", pady=(0, theme.SP_LG), ipady=5)
        search_card.grid_columnconfigure(0, weight=1)

        self.search_query = ctk.StringVar()
        self.search_entry = ThemedEntry(
            search_card, textvariable=self.search_query,
            placeholder_text="Buscar en todos los envíos por email, cédula, ID de servicio o archivo..."
        )
        self.search_entry.grid(row=0, column=0, padx=(20, 10), pady=15, sticky="ew")
        self.search_entry.bind("<Return>", lambda e: self.perform_history_search())

        PrimaryButton(
            search_card, text="Buscar", width=100, height=theme.INPUT_H,
            command=self.perform_history_search
        ).grid(row=0, column=1, padx=5, pady=15)

        SecondaryButton(
            search_card, text="Limpiar", width=80, height=theme.INPUT_H,
            command=self.clear_history_search
        ).grid(row=0, column=2, padx=(5, 20), pady=15)

        # Contenedor dinámico (Scrollable Frame)
        self.history_content_frame = ctk.CTkScrollableFrame(
            self, corner_radius=theme.RAD_LG, fg_color=theme.SURFACE,
            border_width=1, border_color=theme.BORDER
        )
        self.history_content_frame.pack(fill="both", expand=True)

    def load_history_batches(self):
        """Carga y muestra el listado de todos los lotes de envío de la sesión."""
        for widget in self.history_content_frame.winfo_children():
            widget.destroy()

        self.search_query.set("")

        lotes = list(reversed(self.controller.session_batches))
        if not lotes:
            lbl_empty = ctk.CTkLabel(
                self.history_content_frame,
                text="No hay registros de envíos en el historial todavía.",
                font=theme.font("status"), text_color=theme.TEXT_MUTED
            )
            lbl_empty.pack(pady=50)
            return

        lbl_subtitle = ctk.CTkLabel(
            self.history_content_frame,
            text="Lotes recientes de envíos masivos (esta sesión)",
            font=theme.font("h2"), text_color=theme.TEXT
        )
        lbl_subtitle.pack(anchor="w", padx=20, pady=(15, 10))

        for lote in lotes:
            lote_card = ctk.CTkFrame(
                self.history_content_frame, corner_radius=theme.RAD_MD,
                fg_color=theme.SURFACE_ALT, border_width=1, border_color=theme.BORDER
            )
            lote_card.pack(fill="x", padx=15, pady=8, ipady=5)
            lote_card.grid_columnconfigure(0, weight=1)

            lote_id = lote['id']
            fecha = lote['fecha']
            csv_nombre = lote['csv_nombre']
            total = lote['total_registros']
            exitos = lote['exitosos']
            fallos = lote['fallidos']

            info_text = f"Lote #{lote_id} — {fecha}\nCSV: {csv_nombre}"
            lbl_info = ctk.CTkLabel(lote_card, text=info_text, font=theme.font("body"), justify="left", anchor="w", text_color=theme.TEXT)
            lbl_info.grid(row=0, column=0, padx=20, pady=10, sticky="w")

            stat_frame = ctk.CTkFrame(lote_card, fg_color="transparent")
            stat_frame.grid(row=0, column=1, padx=10, pady=10)

            ctk.CTkLabel(stat_frame, text=f"Total: {total}", font=theme.font("body"), text_color=theme.TEXT_SECONDARY).pack(side="left", padx=10)
            ctk.CTkLabel(stat_frame, text=f"Éxitos: {exitos}", font=theme.font("body_strong"), text_color=theme.SUCCESS).pack(side="left", padx=10)
            ctk.CTkLabel(stat_frame, text=f"Fallos: {fallos}", font=theme.font("body_strong"), text_color=theme.DANGER).pack(side="left", padx=10)

            PrimaryButton(
                lote_card, text="Ver Detalle", width=100, height=theme.BTN_SM_H,
                font=theme.font("badge"),
                command=lambda lid=lote_id, ldata=lote: self.show_lote_details_modal(lid, ldata)
            ).grid(row=0, column=2, padx=20, pady=10)

    def show_lote_details_modal(self, lote_id, lote_data):
        LoteModal(self.controller, lote_id, lote_data)

    def perform_history_search(self):
        query = self.search_query.get().strip()
        if not query:
            self.load_history_batches()
            return

        for widget in self.history_content_frame.winfo_children():
            widget.destroy()

        query_strip = query.strip()
        query_lower = query_strip.lower()

        query_email_hash = self.controller.compute_search_hash(query_lower)
        query_cedula_hash = self.controller.compute_search_hash(query_strip)

        results = []
        for lote in self.controller.session_batches:
            # Usamos list() para una copia superficial segura contra modificaciones concurrentes del ThreadPool
            for ev in list(lote.get("envios", [])):
                is_match = False
                if query_email_hash == ev.get("email_hash"):
                    is_match = True
                elif query_cedula_hash == ev.get("cedula_hash"):
                    is_match = True
                elif (query_lower in ev.get("email", "").lower() or
                      query_lower in ev.get("id_archivo", "").lower() or
                      query_lower in ev.get("id_servicio", "").lower()):
                    is_match = True

                if is_match:
                    res_entry = dict(ev)
                    res_entry["fecha"] = lote["fecha"]
                    res_entry["csv_nombre"] = lote["csv_nombre"]
                    results.append(res_entry)
        results = list(reversed(results))[:200]

        lbl_subtitle = ctk.CTkLabel(
            self.history_content_frame,
            text=f"Resultados de búsqueda para: '{query}' ({len(results)} encontrados)",
            font=theme.font("h2"), text_color=theme.TEXT
        )
        lbl_subtitle.pack(anchor="w", padx=20, pady=(15, 10))

        if not results:
            lbl_empty = ctk.CTkLabel(
                self.history_content_frame,
                text="No se encontraron coincidencias en los envíos de historial.",
                font=theme.font("status"), text_color=theme.TEXT_MUTED
            )
            lbl_empty.pack(pady=50)
            return

        for ev in results:
            row_frame = ctk.CTkFrame(
                self.history_content_frame, corner_radius=theme.RAD_MD,
                fg_color=theme.SURFACE_ALT, border_width=1, border_color=theme.BORDER
            )
            row_frame.pack(fill="x", padx=15, pady=6, ipady=5)
            row_frame.grid_columnconfigure(0, weight=1)

            email = ev['email']
            cedula = ev['cedula']
            id_archivo = ev['id_archivo']
            id_servicio = ev['id_servicio']
            estado = ev['estado']
            detalles = ev['detalles']
            fecha = ev['fecha']
            csv_nombre = ev.get('csv_nombre', 'N/A')

            desc = f"Fecha: {fecha} | Lote CSV: {csv_nombre}\nDestinatario: {email}\nID: {cedula} | Servicio: {id_servicio} | Archivo: {id_archivo}"
            lbl_desc = ctk.CTkLabel(row_frame, text=desc, font=theme.font("body"), justify="left", anchor="w", text_color=theme.TEXT)
            lbl_desc.grid(row=0, column=0, padx=20, pady=10, sticky="w")

            StatusBadge.from_estado(row_frame, estado).grid(row=0, column=1, padx=20, pady=8, sticky="e")

            if detalles:
                lbl_det = ctk.CTkLabel(row_frame, text=f"Detalle: {detalles}", font=theme.font("caption"), text_color=theme.DANGER, justify="left", anchor="w")
                lbl_det.grid(row=1, column=0, columnspan=2, padx=20, pady=(0, 10), sticky="w")

    def clear_history_search(self):
        self.load_history_batches()
