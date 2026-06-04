import customtkinter as ctk
from tkinter import messagebox
import sys
from datetime import datetime, timedelta
from src.core.license_manager import LicenseManager

class ActivationModal(ctk.CTk):
    """Ventana independiente premium para la activación de la licencia del software."""
    def __init__(self):
        super().__init__()
        
        self.activated = False
        self._attempt_count = 0
        self._max_attempts = 5
        self._lockout_until = None
        
        self.title("Activación de Licencia — SEMS Pro")
        self.geometry("560x320")
        self.resizable(False, False)
        self.configure(fg_color=("#f8fafc", "#080c14"))
        
        # Tipografías premium
        self.font_title = ctk.CTkFont(family="Segoe UI", size=20, weight="bold")
        self.font_label = ctk.CTkFont(family="Segoe UI", size=13, weight="bold")
        self.font_text = ctk.CTkFont(family="Segoe UI", size=12)
        
        self.setup_ui()
        self.protocol("WM_DELETE_WINDOW", self.on_closing)
        
    def setup_ui(self):
        # Título
        lbl_title = ctk.CTkLabel(
            self, text="Activación de Software", 
            font=self.font_title, 
            text_color=("#4f46e5", "#818cf8")
        )
        lbl_title.pack(pady=(25, 5))
        
        lbl_sub = ctk.CTkLabel(
            self, 
            text="Ingrese su clave de licencia (Base64) para activar su periodo de prueba o suscripción.",
            font=self.font_text,
            text_color=("#64748b", "#94a3b8")
        )
        lbl_sub.pack(pady=(0, 15), padx=20)
        
        # Contenedor de entrada
        input_frame = ctk.CTkFrame(self, corner_radius=12, fg_color=("#ffffff", "#0e1322"), border_width=1, border_color=("#e2e8f0", "#1e293b"))
        input_frame.pack(fill="x", padx=40, pady=5, ipady=5)
        
        ctk.CTkLabel(input_frame, text="Clave de Licencia:", font=self.font_label, text_color=("#334155", "#cbd5e1")).pack(anchor="w", padx=20, pady=(10, 5))
        
        # Caja de texto multilinea para pegar el Base64 largo de forma cómoda
        self.txt_license = ctk.CTkTextbox(
            input_frame, font=self.font_text, height=80, 
            fg_color=("#f8fafc", "#070a13"), border_color=("#cbd5e1", "#1e293b"), 
            border_width=1, corner_radius=8
        )
        self.txt_license.pack(fill="x", padx=20, pady=(0, 10))
        
        # Botones de Acción
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(fill="x", padx=40, pady=(20, 10))
        
        self.btn_cancel = ctk.CTkButton(
            btn_frame, text="Salir", command=self.on_closing,
            width=120, height=40, corner_radius=10,
            fg_color=("#ef4444", "#dc2626"), hover_color=("#dc2626", "#b91c1c"),
            text_color="white", font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold")
        )
        self.btn_cancel.pack(side="left", padx=5)
        
        self.btn_activate = ctk.CTkButton(
            btn_frame, text="✓ Activar Sistema", command=self.activate_license,
            width=220, height=40, corner_radius=10,
            fg_color=("#10b981", "#059669"), hover_color=("#059669", "#047857"),
            text_color="white", font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold")
        )
        self.btn_activate.pack(side="right", padx=5, fill="x", expand=True)
        
    def activate_license(self):
        import time
        now = datetime.now()
        
        # Verificar si hay un bloqueo activo
        if self._lockout_until and now < self._lockout_until:
            remaining = int((self._lockout_until - now).total_seconds())
            messagebox.showerror("Bloqueado", f"Demasiados intentos. Espere {remaining} segundos.", parent=self)
            return
            
        license_key = self.txt_license.get("0.0", "end").strip()
        if not license_key:
            messagebox.showwarning("Atención", "Por favor, ingrese o pegue la clave de licencia.", parent=self)
            return
            
        self.btn_activate.configure(state="disabled", text="Validando...")
        self.update()
        
        # Retardo artificial (1 segundo) para ralentizar bruteforce
        time.sleep(1.0)
        
        # Verificar firma
        payload = LicenseManager.verify_signature(license_key)
        
        if payload:
            # Validar que no esté expirada
            expires = payload.get("expires", "")
            if expires:
                try:
                    exp_date = LicenseManager._parse_iso_datetime(expires)
                    from datetime import timezone
                    now_utc = datetime.now(timezone.utc)
                except Exception:
                    # Fallback si falla timezone
                    exp_date = datetime.fromisoformat(expires)
                    now_utc = datetime.now()
                    
                if now_utc > exp_date:
                    messagebox.showerror("Error de Activación", "Esta clave de licencia ya ha expirado.", parent=self)
                    self.btn_activate.configure(state="normal", text="✓ Activar Sistema")
                    return
            
            # Guardar en Keyring
            success = LicenseManager.save_license(license_key, payload)
            if success:
                messagebox.showinfo("Activación Exitosa", f"¡Software activado correctamente!\n\nPropietario: {payload.get('email')}\nVence el: {expires[:10]}", parent=self)
                self.activated = True
                self.destroy()
            else:
                messagebox.showerror("Error", "No se pudo escribir en el almacén de credenciales del sistema.", parent=self)
                self.btn_activate.configure(state="normal", text="✓ Activar Sistema")
        else:
            # Incrementar contador de intentos fallidos
            self._attempt_count += 1
            if self._attempt_count >= self._max_attempts:
                self._lockout_until = datetime.now() + timedelta(minutes=5)
                self._attempt_count = 0
                messagebox.showerror("Bloqueado", "Límite de intentos alcanzado. Espere 5 minutos.", parent=self)
            else:
                remaining_attempts = self._max_attempts - self._attempt_count
                messagebox.showerror("Licencia Inválida", f"La clave de licencia proporcionada es incorrecta o está alterada.\nIntentos restantes: {remaining_attempts}", parent=self)
                
            self.btn_activate.configure(state="normal", text="✓ Activar Sistema")
            
    def on_closing(self):
        if not self.activated:
            if messagebox.askyesno("Salir", "¿Está seguro de que desea salir del software? El sistema requiere activación para funcionar.", parent=self):
                self.destroy()
                sys.exit(0)
        else:
            self.destroy()
