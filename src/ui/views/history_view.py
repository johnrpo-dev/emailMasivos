import customtkinter as ctk
import hmac
import hashlib
from src.ui.components.history_detail_modal import HistoryDetailModal

class HistoryView(ctk.CTkFrame):
    """Componente modular de la vista de Historial de Auditoría con buscador HMAC."""
    def __init__(self, parent, controller):
        super().__init__(parent, fg_color="transparent")
        self.controller = controller
        
        # Tipografías del controller
        self.font_title = controller.font_title
        self.font_label = controller.font_label
        self.font_text = controller.font_text
        self.font_status = controller.font_status
        
        self.setup_layout()
        
    def setup_layout(self):
        lbl_title = ctk.CTkLabel(self, text="Historial de Auditoría", font=self.font_title, text_color=("#0f172a", "#f8fafc"))
        lbl_title.pack(anchor="w", pady=(0, 2))
        
        lbl_subtitle = ctk.CTkLabel(self, text="Consulte el registro histórico y la trazabilidad de todos los envíos masivos realizados", font=ctk.CTkFont(family="Segoe UI", size=13), text_color=("#64748b", "#94a3b8"))
        lbl_subtitle.pack(anchor="w", pady=(0, 20))
        
        # Card del buscador
        search_card = ctk.CTkFrame(self, corner_radius=16, fg_color=("#ffffff", "#0e1322"), border_width=1, border_color=("#e2e8f0", "#1e293b"))
        search_card.pack(fill="x", pady=(0, 20), ipady=5)
        search_card.grid_columnconfigure(0, weight=1)
        
        self.search_query = ctk.StringVar()
        self.search_entry = ctk.CTkEntry(
            search_card, textvariable=self.search_query, font=self.font_text, height=36,
            fg_color=("#f8fafc", "#070a13"), border_color=("#cbd5e1", "#1e293b"),
            placeholder_text="Buscar en todos los envíos por email, cédula, ID de servicio o archivo..."
        )
        self.search_entry.grid(row=0, column=0, padx=(20, 10), pady=15, sticky="ew")
        
        btn_search = ctk.CTkButton(
            search_card, text="🔍 Buscar", font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"), width=100, height=36,
            fg_color=("#3b82f6", "#2563eb"), hover_color=("#2563eb", "#1d4ed8"), command=self.perform_history_search
        )
        btn_search.grid(row=0, column=1, padx=5, pady=15)
        
        btn_clear_search = ctk.CTkButton(
            search_card, text="Limpiar", font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"), width=80, height=36,
            fg_color=("#4b5563", "#374151"), hover_color=("#374151", "#1f2937"), command=self.clear_history_search
        )
        btn_clear_search.grid(row=0, column=2, padx=(5, 20), pady=15)
        
        # Contenedor dinámico (Scrollable Frame)
        self.history_content_frame = ctk.CTkScrollableFrame(self, corner_radius=16, fg_color=("#ffffff", "#0e1322"), border_width=1, border_color=("#e2e8f0", "#1e293b"))
        self.history_content_frame.pack(fill="both", expand=True)

    def load_history_batches(self):
        """Carga y muestra el listado de todos los lotes de envío con diseño premium."""
        for widget in self.history_content_frame.winfo_children():
            widget.destroy()
        
        self.search_query.set("")
        
        lotes = list(reversed(self.controller.session_batches))
        if not lotes:
            lbl_empty = ctk.CTkLabel(
                self.history_content_frame, 
                text="No hay registros de envíos en el historial todavía.", 
                font=self.font_status, text_color=("#64748b", "#94a3b8")
            )
            lbl_empty.pack(pady=50)
            return
            
        lbl_subtitle = ctk.CTkLabel(
            self.history_content_frame, 
            text="📋 Lotes Recientes de Envíos Masivos (Esta Sesión)", 
            font=ctk.CTkFont(family="Segoe UI", size=15, weight="bold"),
            text_color=("#0f172a", "#f8fafc")
        )
        lbl_subtitle.pack(anchor="w", padx=20, pady=(15, 10))
        
        for lote in lotes:
            lote_card = ctk.CTkFrame(self.history_content_frame, corner_radius=12, fg_color=("#f8fafc", "#070a13"), border_width=1, border_color=("#e2e8f0", "#1e293b"))
            lote_card.pack(fill="x", padx=15, pady=8, ipady=5)
            lote_card.grid_columnconfigure(0, weight=1)
            
            lote_id = lote['id']
            fecha = lote['fecha']
            csv_nombre = lote['csv_nombre']
            total = lote['total_registros']
            exitos = lote['exitosos']
            fallos = lote['fallidos']
            
            info_text = f"Lote #{lote_id} — {fecha}\nCSV: {csv_nombre}"
            lbl_info = ctk.CTkLabel(lote_card, text=info_text, font=self.font_text, justify="left", anchor="w", text_color=("#334155", "#cbd5e1"))
            lbl_info.grid(row=0, column=0, padx=20, pady=10, sticky="w")
            
            stat_frame = ctk.CTkFrame(lote_card, fg_color="transparent")
            stat_frame.grid(row=0, column=1, padx=10, pady=10)
            
            ctk.CTkLabel(stat_frame, text=f"Total: {total}", font=self.font_text, text_color=("#475569", "#94a3b8")).pack(side="left", padx=10)
            ctk.CTkLabel(stat_frame, text=f"Éxitos: {exitos}", font=self.font_label, text_color=("#10b981", "#34d399")).pack(side="left", padx=10)
            ctk.CTkLabel(stat_frame, text=f"Fallos: {fallos}", font=self.font_label, text_color=("#ef4444", "#f87171")).pack(side="left", padx=10)
            
            btn_details = ctk.CTkButton(
                lote_card, text="Ver Detalle", font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"), width=100, height=32,
                fg_color=("#4f46e5", "#6366f1"), hover_color=("#4338ca", "#4f46e5"),
                command=lambda lid=lote_id, ldata=lote: self.show_lote_details_modal(lid, ldata)
            )
            btn_details.grid(row=0, column=2, padx=20, pady=10)

    def show_lote_details_modal(self, lote_id, lote_data):
        HistoryDetailModal(self.controller, lote_id, lote_data)

    def perform_history_search(self):
        query = self.search_query.get().strip()
        if not query:
            self.load_history_batches()
            return
            
        for widget in self.history_content_frame.winfo_children():
            widget.destroy()
            
        query_strip = query.strip()
        query_lower = query_strip.lower()
        
        query_email_hash = hmac.new(self.controller._hmac_key, query_lower.encode(), hashlib.sha256).hexdigest()
        query_cedula_hash = hmac.new(self.controller._hmac_key, query_strip.encode(), hashlib.sha256).hexdigest()
        
        results = []
        for lote in self.controller.session_batches:
            for ev in lote.get("envios", []):
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
            text=f"🔍 Resultados de búsqueda para: '{query}' ({len(results)} encontrados)", 
            font=ctk.CTkFont(family="Segoe UI", size=16, weight="bold"),
            text_color=("#0f172a", "#f8fafc")
        )
        lbl_subtitle.pack(anchor="w", padx=20, pady=(15, 10))
        
        if not results:
            lbl_empty = ctk.CTkLabel(
                self.history_content_frame, 
                text="No se encontraron coincidencias en los envíos de historial.", 
                font=self.font_status, text_color=("#64748b", "#94a3b8")
            )
            lbl_empty.pack(pady=50)
            return
            
        for ev in results:
            row_frame = ctk.CTkFrame(self.history_content_frame, corner_radius=12, fg_color=("#f8fafc", "#070a13"), border_width=1, border_color=("#e2e8f0", "#1e293b"))
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
            lbl_desc = ctk.CTkLabel(row_frame, text=desc, font=self.font_text, justify="left", anchor="w", text_color=("#334155", "#cbd5e1"))
            lbl_desc.grid(row=0, column=0, padx=20, pady=10, sticky="w")
            
            if estado == "exito":
                lbl_est = ctk.CTkLabel(row_frame, text="ÉXITO", font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"), text_color="white", fg_color="#10b981", corner_radius=6, width=90, height=26)
            else:
                lbl_est = ctk.CTkLabel(row_frame, text="FALLIDO", font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"), text_color="white", fg_color="#ef4444", corner_radius=6, width=90, height=26)
            lbl_est.grid(row=0, column=1, padx=20, pady=10, sticky="e")
            
            if detalles:
                lbl_det = ctk.CTkLabel(row_frame, text=f"Detalle: {detalles}", font=ctk.CTkFont(family="Segoe UI", size=11, slant="italic"), text_color=("#ef4444", "#f87171"), justify="left", anchor="w")
                lbl_det.grid(row=1, column=0, columnspan=2, padx=20, pady=(0, 10), sticky="w")

    def clear_history_search(self):
        self.load_history_batches()
