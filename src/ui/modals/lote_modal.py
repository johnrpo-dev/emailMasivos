import customtkinter as ctk

class LoteModal(ctk.CTkToplevel):
    """Modal premium con la lista detallada de envíos en un lote anterior."""
    def __init__(self, parent, lote_id, lote_data):
        super().__init__(parent)
        self.lote_data = lote_data
        
        self.title(f"Detalle de Envío - Lote #{lote_id}")
        self.geometry("750x580")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()
        self.configure(fg_color=("#f8fafc", "#080c14"))
        
        # Tipografías base
        self.font_label = ctk.CTkFont(family="Segoe UI", size=14, weight="bold")
        self.font_text = ctk.CTkFont(family="Segoe UI", size=13)
        self.font_status = ctk.CTkFont(family="Segoe UI", size=14, slant="italic")
        
        # Título
        lbl_title = ctk.CTkLabel(
            self, text=f"Detalle del Lote #{lote_id}", 
            font=ctk.CTkFont(family="Segoe UI", size=20, weight="bold"), 
            text_color=("#0f172a", "#f8fafc")
        )
        lbl_title.pack(pady=(20, 5))
        
        # Tarjeta de datos del lote con estética premium
        info_frame = ctk.CTkFrame(self, corner_radius=16, fg_color=("#ffffff", "#0e1322"), border_width=1, border_color=("#e2e8f0", "#1e293b"))
        info_frame.pack(fill="x", padx=30, pady=10, ipady=5)
        
        info_str = f"Archivo: {lote_data['csv_nombre']}   |   Fecha: {lote_data['fecha']}"
        ctk.CTkLabel(info_frame, text=info_str, font=self.font_text, text_color=("#334155", "#cbd5e1")).pack(pady=5)
        
        stats_str = f"Total Registros: {lote_data['total_registros']}   -   Exitosos: {lote_data['exitosos']}   -   Fallidos: {lote_data['fallidos']}"
        ctk.CTkLabel(
            info_frame, text=stats_str, font=self.font_label, 
            text_color=("#4f46e5", "#818cf8")
        ).pack(pady=(0, 5))
        
        # Scrollable Frame con los envíos del lote
        envios_scroll = ctk.CTkScrollableFrame(self, corner_radius=16, fg_color=("#ffffff", "#0e1322"), border_width=1, border_color=("#e2e8f0", "#1e293b"))
        envios_scroll.pack(fill="both", expand=True, padx=30, pady=10)
        
        envios = list(lote_data.get('envios', []))  # Usamos copia superficial para seguridad
        if not envios:
            ctk.CTkLabel(envios_scroll, text="No hay registros individuales para este lote.", font=self.font_status, text_color=("#64748b", "#94a3b8")).pack(pady=40)
        else:
            for ev in envios:
                row_frame = ctk.CTkFrame(envios_scroll, corner_radius=12, fg_color=("#f8fafc", "#070a13"), border_width=1, border_color=("#e2e8f0", "#1e293b"))
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
                lbl_desc = ctk.CTkLabel(row_frame, text=desc, font=self.font_text, justify="left", anchor="w", text_color=("#334155", "#cbd5e1"))
                lbl_desc.grid(row=0, column=0, padx=15, pady=8, sticky="w")
                
                # Etiqueta Estado premium plana con ícono (chulo verde / x roja)
                if estado == "exito":
                    bg_color = ("#e6f4ea", "#0f2d1a")
                    text_color = ("#137333", "#81c995")
                    status_text = "✓ Exitoso"
                else:
                    bg_color = ("#fce8e6", "#3c1e1e")
                    text_color = ("#c5221f", "#f28b82")
                    status_text = "✕ Fallido"
                
                lbl_est = ctk.CTkLabel(
                    row_frame, text=status_text,
                    font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
                    fg_color=bg_color,
                    text_color=text_color,
                    corner_radius=12,
                    height=26,
                    padx=14
                )
                lbl_est.grid(row=0, column=1, padx=20, pady=8, sticky="e")
                
                # Detalles del error
                if detalles:
                    lbl_det = ctk.CTkLabel(row_frame, text=f"Detalle: {detalles}", font=ctk.CTkFont(family="Segoe UI", size=11, slant="italic"), text_color=("#ef4444", "#f87171"), justify="left", anchor="w")
                    lbl_det.grid(row=1, column=0, columnspan=2, padx=15, pady=(0, 8), sticky="w")
                    
        # Botón para cerrar modal y reintentar si existen registros fallidos en RAM
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(pady=15, fill="x", padx=30)
        
        btn_close = ctk.CTkButton(
            btn_frame, text="Cerrar", font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"), 
            width=120, height=42, fg_color=("#4b5563", "#374151"), hover_color=("#374151", "#1f2937"), 
            command=self.destroy
        )
        btn_close.pack(side="left", padx=5, expand=True)
        
        raw_records = lote_data.get("raw_records_fallidos")
        raw_email_corrections = lote_data.get("raw_email_corrections", {})
        raw_pdf_corrections = lote_data.get("raw_pdf_corrections", {})
        
        if raw_records:
            if raw_email_corrections or raw_pdf_corrections:
                btn_correct = ctk.CTkButton(
                    btn_frame, text="✨ Corregir y Reintentar", font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
                    width=180, height=42, fg_color=("#10b981", "#059669"), hover_color=("#059669", "#047857"),
                    text_color="white", command=self.handle_correct_and_retry
                )
                btn_correct.pack(side="left", padx=5, expand=True)
                
            btn_retry = ctk.CTkButton(
                btn_frame, text="🔄 Reintentar Fallidos", font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
                width=160, height=42, fg_color=("#f59e0b", "#d97706"), hover_color=("#d97706", "#b45309"),
                text_color="white", command=self.handle_retry
            )
            btn_retry.pack(side="right", padx=5, expand=True)

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
