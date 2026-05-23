import customtkinter as ctk
from tkinter import messagebox

class ResultsModal(ctk.CTkToplevel):
    """Modal desacoplado y puro para el Reporte de Errores y Reintentos."""
    def __init__(self, parent, errores, total, records_fallidos, email_corrections=None, on_retry=None, on_correct_and_retry=None):
        super().__init__(parent)
        
        if email_corrections is None:
            email_corrections = {}
            
        self.errores = errores
        self.total = total
        self.records_fallidos = records_fallidos
        self.email_corrections = email_corrections
        self.on_retry = on_retry
        self.on_correct_and_retry = on_correct_and_retry
        
        self.title("Reporte de Envíos")
        self.geometry("620x580")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()
        self.configure(fg_color=("#f8fafc", "#080c14"))
        
        # Tipografías base
        self.font_label = ctk.CTkFont(family="Segoe UI", size=14, weight="bold")
        self.font_text = ctk.CTkFont(family="Segoe UI", size=13)
        
        self.protocol("WM_DELETE_WINDOW", self.safe_close_modal)
        self.setup_ui()
        
    def safe_close_modal(self):
        try:
            self.master.focus_set()
            self.destroy()
        except Exception:
            pass
            
    def setup_ui(self):
        self.lbl_title = ctk.CTkLabel(
            self, text="Atención Requerida", 
            font=ctk.CTkFont(family="Segoe UI", size=24, weight="bold"), 
            text_color=("#d97706", "#fbbf24")
        )
        self.lbl_title.pack(pady=(25, 10))
        
        exitosos = self.total - len(self.errores)
        
        card_summary = ctk.CTkFrame(self, corner_radius=16, fg_color=("#ffffff", "#0e1322"), border_width=1, border_color=("#e2e8f0", "#1e293b"))
        card_summary.pack(fill="x", padx=30, pady=(10, 15), ipady=10)
        
        lbl_total = ctk.CTkLabel(card_summary, text=f"Total: {self.total}", font=self.font_label, text_color=("#475569", "#cbd5e1"))
        lbl_total.pack(side="left", expand=True)
        lbl_success = ctk.CTkLabel(card_summary, text=f"Éxitos: {exitosos}", font=self.font_label, text_color=("#10b981", "#34d399"))
        lbl_success.pack(side="left", expand=True)
        lbl_err = ctk.CTkLabel(card_summary, text=f"Errores: {len(self.errores)}", font=self.font_label, text_color=("#ef4444", "#f87171"))
        lbl_err.pack(side="left", expand=True)
        
        if self.email_corrections:
            card_fix = ctk.CTkFrame(self, corner_radius=12, fg_color=("#fef3c7", "#291505"), border_width=1, border_color=("#f59e0b", "#d97706"))
            card_fix.pack(fill="x", padx=30, pady=(0, 10), ipady=5)
            fix_count = len(self.email_corrections)
            lbl_fix = ctk.CTkLabel(
                card_fix, 
                text=f"Se detectaron {fix_count} correo(s) con errores corregibles automáticamente.",
                font=self.font_text, text_color=("#92400e", "#fde047")
            )
            lbl_fix.pack(padx=15, pady=8)
            
        txt_errors = ctk.CTkTextbox(self, width=560, height=200, font=self.font_text, corner_radius=12, fg_color=("#f8fafc", "#070a13"), text_color=("#334155", "#cbd5e1"), border_width=1, border_color=("#e2e8f0", "#1e293b"))
        txt_errors.pack(pady=10, padx=30)
        
        self.report_text = "--- REPORTE DE ERRORES ---\n\n"
        self.report_text += "\n".join(self.errores)
        txt_errors.insert("0.0", self.report_text)
        txt_errors.configure(state="disabled")
        
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(pady=(15, 10), fill="x", padx=30)
        
        self.btn_copy = ctk.CTkButton(btn_frame, text="Copiar Reporte", command=self.copy_to_clipboard, width=140, height=45, corner_radius=12, fg_color=("#4b5563", "#374151"), hover_color=("#374151", "#1f2937"))
        self.btn_copy.pack(side="left", padx=5, expand=True)
        
        if self.email_corrections:
            self.btn_correct = ctk.CTkButton(
                btn_frame, text="Corregir y Reintentar", command=self.handle_correct_and_retry,
                width=180, height=45, corner_radius=12,
                font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
                fg_color=("#10b981", "#059669"), hover_color=("#059669", "#047857"), text_color="white"
            )
            self.btn_correct.pack(side="left", padx=5, expand=True)
            
        if self.records_fallidos:
            self.btn_retry = ctk.CTkButton(btn_frame, text="Reintentar Fallidos", command=self.handle_retry, width=160, height=45, corner_radius=12, font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"), fg_color=("#f59e0b", "#d97706"), hover_color=("#d97706", "#b45309"), text_color="white")
            self.btn_retry.pack(side="right", padx=5, expand=True)
            
    def copy_to_clipboard(self):
        self.clipboard_clear()
        self.clipboard_append(self.report_text)
        messagebox.showinfo("Copiado", "El reporte ha sido copiado al portapapeles.", parent=self)
        
    def handle_correct_and_retry(self):
        if self.on_correct_and_retry:
            # Deshabilitar botones para feedback visual de carga
            self.btn_correct.configure(state="disabled", text="Corrigiendo...", fg_color="#4b5563")
            self.btn_copy.configure(state="disabled")
            if hasattr(self, 'btn_retry'):
                self.btn_retry.configure(state="disabled")
            self.lbl_title.configure(text="Aplicando correcciones...", text_color="gray")
            
            # Invocar callback
            self.on_correct_and_retry()
            self.safe_close_modal()
            
    def handle_retry(self):
        if self.on_retry:
            # Deshabilitar botones
            self.btn_retry.configure(state="disabled", text="Reintentando...", fg_color="#4b5563")
            self.btn_copy.configure(state="disabled")
            if hasattr(self, 'btn_correct'):
                self.btn_correct.configure(state="disabled")
            self.lbl_title.configure(text="Reintentando envios...", text_color="gray")
            
            # Invocar callback
            self.on_retry()
            self.safe_close_modal()
