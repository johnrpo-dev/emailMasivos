import customtkinter as ctk
from tkinter import messagebox
import re

class ResultsModal(ctk.CTkToplevel):
    """Modal premium, modular y altamente visual para el Reporte de Errores y Reintentos."""
    def __init__(self, parent, errores, total, records_fallidos, email_corrections=None, on_retry=None, on_correct_and_retry=None, pdf_corrections=None):
        super().__init__(parent)
        
        if email_corrections is None:
            email_corrections = {}
        if pdf_corrections is None:
            pdf_corrections = {}
            
        self.errores = errores
        self.total = total
        self.records_fallidos = records_fallidos
        self.email_corrections = email_corrections
        self.pdf_corrections = pdf_corrections
        self.on_retry = on_retry
        self.on_correct_and_retry = on_correct_and_retry
        self._is_retrying = False
        
        self.title("Reporte de Envíos — SEMS Pro")
        self.geometry("650x680")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()
        self.configure(fg_color=("#f8fafc", "#080c14"))
        
        # Tipografías base
        self.font_title = ctk.CTkFont(family="Segoe UI", size=22, weight="bold")
        self.font_section = ctk.CTkFont(family="Segoe UI", size=15, weight="bold")
        self.font_label = ctk.CTkFont(family="Segoe UI", size=13, weight="bold")
        self.font_text = ctk.CTkFont(family="Segoe UI", size=12)
        self.font_mono = ctk.CTkFont(family="Consolas", size=11)
        
        self.protocol("WM_DELETE_WINDOW", self.safe_close_modal)
        self.setup_ui()
        
    def safe_close_modal(self):
        if self.records_fallidos and not self._is_retrying:
            confirm = messagebox.askyesno(
                "Confirmar Cierre",
                "¿Estás seguro de que deseas cerrar el reporte?\n\n"
                "Los envíos fallidos de este lote solo podrán ser reintentados desde la pestaña 'Historial de Auditoría' mientras la aplicación siga abierta.",
                parent=self
            )
            if not confirm:
                return
        try:
            self.master.focus_set()
            self.destroy()
        except Exception:
            pass
            
    def setup_ui(self):
        # 1. Círculo de Alerta Premium (Evita el emoji básico y crea un gráfico vectorial elegante)
        icon_container = ctk.CTkFrame(
            self, width=60, height=60, corner_radius=30, 
            fg_color=("#fffbeb", "#1e1404"), 
            border_width=2, 
            border_color=("#f59e0b", "#d97706")
        )
        icon_container.pack(pady=(25, 2))
        icon_container.pack_propagate(False)
        
        lbl_icon = ctk.CTkLabel(
            icon_container, text="!", 
            font=ctk.CTkFont(family="Segoe UI", size=30, weight="bold"),
            text_color=("#d97706", "#fbbf24")
        )
        lbl_icon.place(relx=0.5, rely=0.5, anchor="center")
        
        self.lbl_title = ctk.CTkLabel(
            self, text="Atención Requerida", 
            font=self.font_title, 
            text_color=("#d97706", "#fbbf24")
        )
        self.lbl_title.pack(pady=(2, 10))
        
        exitosos = self.total - len(self.errores)
        
        # 2. Rejilla de Resumen de Contadores (KPI Cards Modernas)
        stats_frame = ctk.CTkFrame(self, fg_color="transparent")
        stats_frame.pack(fill="x", padx=30, pady=(10, 15))
        stats_frame.grid_columnconfigure((0, 1, 2), weight=1)
        
        # Caja Total (Indigo Accent)
        box_total = ctk.CTkFrame(stats_frame, corner_radius=14, fg_color=("#ffffff", "#0c101b"), border_width=1, border_color=("#e2e8f0", "#182235"))
        box_total.grid(row=0, column=0, padx=6, sticky="nsew")
        ctk.CTkLabel(box_total, text="Procesados", font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"), text_color=("#64748b", "#64748b")).pack(pady=(12, 2))
        ctk.CTkLabel(box_total, text=str(self.total), font=ctk.CTkFont(family="Segoe UI", size=24, weight="bold"), text_color=("#4f46e5", "#818cf8")).pack(pady=(0, 12))
        
        # Caja Éxitos (Emerald Accent)
        box_success = ctk.CTkFrame(stats_frame, corner_radius=14, fg_color=("#ffffff", "#0c101b"), border_width=1, border_color=("#e2e8f0", "#182235"))
        box_success.grid(row=0, column=1, padx=6, sticky="nsew")
        ctk.CTkLabel(box_success, text="Éxitos", font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"), text_color=("#64748b", "#64748b")).pack(pady=(12, 2))
        ctk.CTkLabel(box_success, text=str(exitosos), font=ctk.CTkFont(family="Segoe UI", size=24, weight="bold"), text_color=("#10b981", "#34d399")).pack(pady=(0, 12))
        
        # Caja Errores (Rose Accent)
        box_failed = ctk.CTkFrame(stats_frame, corner_radius=14, fg_color=("#ffffff", "#0c101b"), border_width=1, border_color=("#e2e8f0", "#182235"))
        box_failed.grid(row=0, column=2, padx=6, sticky="nsew")
        ctk.CTkLabel(box_failed, text="Fallidos", font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"), text_color=("#64748b", "#64748b")).pack(pady=(12, 2))
        ctk.CTkLabel(box_failed, text=str(len(self.errores)), font=ctk.CTkFont(family="Segoe UI", size=24, weight="bold"), text_color=("#ef4444", "#f87171")).pack(pady=(0, 12))
        
        # 3. Aviso Inteligente de Correcciones Disponibles (Amber Glow)
        if self.email_corrections or self.pdf_corrections:
            card_fix = ctk.CTkFrame(
                self, corner_radius=12, 
                fg_color=("#fffbeb", "#1c1407"), 
                border_width=1, 
                border_color=("#fde047", "#a16207")
            )
            card_fix.pack(fill="x", padx=30, pady=(0, 15))
            
            fix_count = len(self.email_corrections) + len(self.pdf_corrections)
            lbl_fix = ctk.CTkLabel(
                card_fix, 
                text=f"✨ Se detectaron {fix_count} sugerencia(s) de corrección automática.\nPresione 'Corregir y Reintentar' para auto-repararlos e iniciar el reenvío.",
                font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"), 
                text_color=("#d97706", "#fef08a"), 
                justify="center",
                pady=10
            )
            lbl_fix.pack(padx=20, fill="both")
            
        # 4. Sección de Historial de Errores - Scrollable & Tarjetas Modulares
        lbl_list_title = ctk.CTkLabel(self, text="Detalle de Fallos Encontrados:", font=self.font_section, text_color=("#334155", "#cbd5e1"))
        lbl_list_title.pack(anchor="w", padx=35, pady=(0, 8))
        
        self.scroll_frame = ctk.CTkScrollableFrame(
            self, height=210, fg_color="transparent", 
            border_width=0
        )
        self.scroll_frame.pack(fill="both", expand=True, padx=25, pady=(0, 15))
        
        # Poblar lista de errores estructurados
        for err_str in self.errores:
            self._render_error_card(err_str)
            
        # 5. Botones de Acción Premium con Micro-animaciones en barra inferior
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(pady=(5, 20), fill="x", padx=30)
        
        self.btn_copy = ctk.CTkButton(
            btn_frame, text="📋 Copiar Reporte", command=self.copy_to_clipboard, 
            width=140, height=45, corner_radius=12, 
            fg_color=("#4b5563", "#1e293b"), hover_color=("#374151", "#2d3748"),
            text_color=("#ffffff", "#e2e8f0"), font=self.font_label
        )
        self.btn_copy.pack(side="left", padx=5, expand=True)
        
        if self.email_corrections or self.pdf_corrections:
            self.btn_correct = ctk.CTkButton(
                btn_frame, text="✨ Corregir y Reintentar", command=self.handle_correct_and_retry,
                width=200, height=45, corner_radius=12,
                fg_color=("#10b981", "#059669"), hover_color=("#059669", "#047857"),
                text_color="white", font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold")
            )
            self.btn_correct.pack(side="left", padx=5, expand=True)
            
        if self.records_fallidos:
            self.btn_retry = ctk.CTkButton(
                btn_frame, text="🔄 Reintentar Fallidos", command=self.handle_retry, 
                width=160, height=45, corner_radius=12, 
                fg_color=("#f59e0b", "#d97706"), hover_color=("#d97706", "#b45309"), 
                text_color="white", font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold")
            )
            self.btn_retry.pack(side="right", padx=5, expand=True)
            
    def _render_error_card(self, err_str):
        """Renderiza una tarjeta visual e individual para cada error."""
        card = ctk.CTkFrame(
            self.scroll_frame, corner_radius=12, 
            fg_color=("#ffffff", "#090d16"), 
            border_width=1, border_color=("#e2e8f0", "#182235")
        )
        card.pack(fill="x", pady=6, padx=5, ipady=6)
        card.grid_columnconfigure(0, weight=1)
        
        # Intentar parsear el formato "email: detalle"
        email_part = "Fallo General"
        detail_part = err_str
        
        if ":" in err_str:
            parts = err_str.split(":", 1)
            if "@" in parts[0]:
                email_part = parts[0].strip()
                detail_part = parts[1].strip()
                
        # Clasificar la naturaleza del error para pintar tags y colores inteligentes
        badge_text = "⚠️ FALLO"
        badge_color = ("#64748b", "#222a36")
        text_color = ("#475569", "#94a3b8")
        border_color = ("#cbd5e1", "#334155")
        is_suggestion = False
        suggestion_val = ""
        
        detail_lower = detail_part.lower()
        sug_match = re.search(r'\(sugerencia:\s*([^)]+)\)', detail_lower)
        if sug_match:
            is_suggestion = True
            suggestion_val = sug_match.group(1).strip()
            
        if "no encontrado" in detail_lower or "pdf" in detail_lower:
            if is_suggestion:
                badge_text = "📄 PDF SUGERIDO"
                badge_color = ("#e0f2fe", "#0c2340")
                text_color = ("#0284c7", "#7dd3fc")
                border_color = ("#7dd3fc", "#0369a1")
            else:
                badge_text = "📄 PDF FALTANTE"
                badge_color = ("#ffedd5", "#2a1405")
                text_color = ("#ea580c", "#fed7aa")
                border_color = ("#fdba74", "#9a3412")
        elif "typo" in detail_lower or "quisiste decir" in detail_lower or is_suggestion:
            badge_text = "💡 SUGERENCIA"
            badge_color = ("#fef3c7", "#291505")
            text_color = ("#d97706", "#fef08a")
            border_color = ("#fde047", "#854d0e")
        elif "servidores" in detail_lower or "dominio" in detail_lower or "dns" in detail_lower:
            badge_text = "🌐 DOMINIO INVÁLIDO"
            badge_color = ("#fee2e2", "#2d1616")
            text_color = ("#dc2626", "#fca5a5")
            border_color = ("#fca5a5", "#991b1b")
        elif "conexión" in detail_lower or "smtp" in detail_lower or "timeout" in detail_lower:
            badge_text = "📡 ERROR SMTP"
            badge_color = ("#f3e8ff", "#21152d")
            text_color = ("#9333ea", "#e9d5ff")
            border_color = ("#d8b4fe", "#6b21a8")
            
        # 1. Header de la tarjeta (Email del Destinatario + Badge Contorneado)
        header_frame = ctk.CTkFrame(card, fg_color="transparent")
        header_frame.pack(fill="x", padx=15, pady=(8, 2))
        
        lbl_email = ctk.CTkLabel(
            header_frame, text=email_part, 
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            text_color=("#1e293b", "#e2e8f0")
        )
        lbl_email.pack(side="left")
        
        # Contenedor del Badge Premium con borde fino
        badge_frame = ctk.CTkFrame(
            header_frame, corner_radius=6,
            fg_color=badge_color[1] if ctk.get_appearance_mode() == "Dark" else badge_color[0],
            border_width=1,
            border_color=border_color[1] if ctk.get_appearance_mode() == "Dark" else border_color[0]
        )
        badge_frame.pack(side="right")
        
        lbl_badge = ctk.CTkLabel(
            badge_frame, text=badge_text, 
            font=ctk.CTkFont(family="Segoe UI", size=9, weight="bold"),
            text_color=text_color[1] if ctk.get_appearance_mode() == "Dark" else text_color[0],
            padx=10, pady=2
        )
        lbl_badge.pack()
        
        # 2. Contenido descriptivo del fallo
        content_frame = ctk.CTkFrame(card, fg_color="transparent")
        content_frame.pack(fill="x", padx=15, pady=(2, 6))
        
        clean_detail = re.sub(r'\(sugerencia:.*?\)', '', detail_part, flags=re.IGNORECASE).strip()
        
        if is_suggestion and suggestion_val:
            is_pdf = "pdf" in detail_lower or "no encontrado" in detail_lower
            desc_text = "El archivo PDF no fue encontrado con el nombre exacto especificado." if is_pdf else "El dominio ingresado contiene un error de ortografía común."
            
            lbl_desc = ctk.CTkLabel(
                content_frame, 
                text=desc_text, 
                font=self.font_text, text_color=("#475569", "#94a3b8"),
                justify="left", anchor="w"
            )
            lbl_desc.pack(anchor="w", pady=(0, 4))
            
            # Pill de sugerencia perfectamente encajada (sin expandirse artificialmente a la derecha)
            sug_frame = ctk.CTkFrame(
                content_frame, corner_radius=8, 
                fg_color=("#e6f4ea", "#0a1f11"), 
                border_width=1, border_color=("#bbf7d0", "#14532d")
            )
            sug_frame.pack(anchor="w", pady=(4, 2), padx=2)
            
            pill_text = f"¿Usar: {suggestion_val}?" if is_pdf else f"¿Quisiste decir: {suggestion_val}?"
            lbl_sug_text = ctk.CTkLabel(
                sug_frame, 
                text=pill_text, 
                font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
                text_color=("#166534", "#4ade80"),
                padx=12, pady=4
            )
            lbl_sug_text.pack()
        else:
            lbl_desc = ctk.CTkLabel(
                content_frame, text=clean_detail, 
                font=self.font_text, text_color=("#475569", "#94a3b8"),
                justify="left", anchor="w", wraplength=540
            )
            lbl_desc.pack(anchor="w", fill="x")
            
    def copy_to_clipboard(self):
        self.clipboard_clear()
        raw_report = "--- REPORTE DE ERRORES SEMS PRO ---\n\n"
        raw_report += "\n".join(self.errores)
        self.clipboard_append(raw_report)
        messagebox.showinfo("Copiado", "El reporte ha sido copiado al portapapeles.", parent=self)
        
    def handle_correct_and_retry(self):
        if self.on_correct_and_retry:
            self._is_retrying = True
            self.btn_correct.configure(state="disabled", text="Corrigiendo...", fg_color="#4b5563")
            self.btn_copy.configure(state="disabled")
            if hasattr(self, 'btn_retry'):
                self.btn_retry.configure(state="disabled")
            self.lbl_title.configure(text="Aplicando correcciones...", text_color="gray")
            self.on_correct_and_retry()
            self.safe_close_modal()
            
    def handle_retry(self):
        if self.on_retry:
            self._is_retrying = True
            self.btn_retry.configure(state="disabled", text="Reintentando...", fg_color="#4b5563")
            self.btn_copy.configure(state="disabled")
            if hasattr(self, 'btn_correct'):
                self.btn_correct.configure(state="disabled")
            self.lbl_title.configure(text="Reintentando envios...", text_color="gray")
            self.on_retry()
            self.safe_close_modal()
