import customtkinter as ctk
import sys
from datetime import datetime, timedelta
from src.core.license_manager import LicenseManager
from src.ui import theme, dialogs
from src.ui.components import Card, PrimaryButton, DangerButton, ThemedTextbox, apply_window_icon, center_window

class ActivationModal(ctk.CTk):
    """Ventana independiente para la activación de la licencia del software.

    Es un root de Tk propio (con su propio mainloop) porque se ejecuta antes
    de construir la ventana principal; App limpia el caché de fuentes del
    tema al arrancar para no heredar fuentes de este root destruido.
    """
    def __init__(self):
        super().__init__()

        self.activated = False
        self._attempt_count = 0
        self._max_attempts = 5
        self._lockout_until = None

        ctk.set_appearance_mode(theme.DEFAULT_APPEARANCE)

        self.title("Activación de Licencia — SEMS Pro")
        center_window(self, 560, 360)
        self.resizable(False, False)
        self.configure(fg_color=theme.APP_BG)
        apply_window_icon(self)

        self.setup_ui()
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

    def setup_ui(self):
        # Título
        lbl_title = ctk.CTkLabel(
            self, text="Activación de Software",
            font=theme.font("h1"),
            text_color=theme.PRIMARY
        )
        lbl_title.pack(pady=(25, 5))

        lbl_sub = ctk.CTkLabel(
            self,
            text="Ingrese su clave de licencia (Base64) para activar su periodo de prueba o suscripción.",
            font=theme.font("body"),
            text_color=theme.TEXT_SECONDARY
        )
        lbl_sub.pack(pady=(0, 15), padx=20)

        # Contenedor de entrada
        input_frame = Card(self, corner_radius=theme.RAD_MD)
        input_frame.pack(fill="x", padx=40, pady=5, ipady=5)

        ctk.CTkLabel(input_frame, text="Clave de Licencia:", font=theme.font("body_strong"), text_color=theme.TEXT).pack(anchor="w", padx=20, pady=(10, 5))

        # Caja de texto multilinea para pegar el Base64 largo de forma cómoda
        self.txt_license = ThemedTextbox(input_frame, height=80)
        self.txt_license.pack(fill="x", padx=20, pady=(0, 10))
        self.txt_license.focus_set()

        # Barra de actividad indeterminada durante la validación
        self.validation_bar = ctk.CTkProgressBar(
            self, mode="indeterminate", height=6,
            progress_color=theme.PROGRESS_FG, fg_color=theme.PROGRESS_BG
        )
        # Se muestra solo mientras se valida (ver activate_license/_validation_done)

        # Botones de Acción
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(fill="x", padx=40, pady=(20, 10))

        self.btn_cancel = DangerButton(
            btn_frame, text="Salir", command=self.on_closing,
            width=120, height=40
        )
        self.btn_cancel.pack(side="left", padx=5)

        self.btn_activate = PrimaryButton(
            btn_frame, text="Activar Sistema", command=self.activate_license,
            width=220, height=40
        )
        self.btn_activate.pack(side="right", padx=5, fill="x", expand=True)

    def _show_validation_bar(self):
        self.validation_bar.pack(fill="x", padx=40, pady=(12, 0))
        self.validation_bar.start()

    def _hide_validation_bar(self):
        self.validation_bar.stop()
        self.validation_bar.pack_forget()

    def _validation_done(self):
        """Restablece el botón y oculta la barra tras un intento de validación."""
        self._hide_validation_bar()
        self.btn_activate.configure(state="normal", text="Activar Sistema")

    def activate_license(self):
        now = datetime.now()

        # Verificar si hay un bloqueo activo
        if self._lockout_until and now < self._lockout_until:
            remaining = int((self._lockout_until - now).total_seconds())
            dialogs.show_error(self, "Bloqueado", f"Demasiados intentos. Espere {remaining} segundos.")
            return

        license_key = self.txt_license.get("0.0", "end").strip()
        if not license_key:
            dialogs.show_warning(self, "Atención", "Por favor, ingrese o pegue la clave de licencia.")
            return

        self.btn_activate.configure(state="disabled", text="Validando...")
        self._show_validation_bar()

        # Retardo anti-bruteforce sin bloquear el hilo de UI (M-07): programar la
        # validación 1 segundo después con after() en lugar de time.sleep().
        self.after(1000, lambda: self._validate_license(license_key))

    def _validate_license(self, license_key: str):
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
                    # Fecha ilegible en el payload = licencia inválida (sin fallbacks naive
                    # que comparan fechas con y sin timezone o relanzan la excepción).
                    dialogs.show_error(self, "Error de Activación", "La clave de licencia contiene una fecha de expiración ilegible.")
                    self._validation_done()
                    return

                if now_utc > exp_date:
                    dialogs.show_error(self, "Error de Activación", "Esta clave de licencia ya ha expirado.")
                    self._validation_done()
                    return

            # Guardar en Keyring
            success = LicenseManager.save_license(license_key, payload)
            if success:
                self._hide_validation_bar()
                dialogs.show_success(self, "Activación Exitosa", f"¡Software activado correctamente!\n\nPropietario: {payload.get('email')}\nVence el: {expires[:10]}")
                self.activated = True
                self.destroy()
            else:
                dialogs.show_error(self, "Error", "No se pudo escribir en el almacén de credenciales del sistema.")
                self._validation_done()
        else:
            # Incrementar contador de intentos fallidos
            self._attempt_count += 1
            if self._attempt_count >= self._max_attempts:
                self._lockout_until = datetime.now() + timedelta(minutes=5)
                self._attempt_count = 0
                dialogs.show_error(self, "Bloqueado", "Límite de intentos alcanzado. Espere 5 minutos.")
            else:
                remaining_attempts = self._max_attempts - self._attempt_count
                dialogs.show_error(self, "Licencia Inválida", f"La clave de licencia proporcionada es incorrecta o está alterada.\nIntentos restantes: {remaining_attempts}")

            self._validation_done()

    def on_closing(self):
        if not self.activated:
            if dialogs.ask_yes_no(self, "Salir", "¿Está seguro de que desea salir del software? El sistema requiere activación para funcionar.", danger=True):
                self.destroy()
                sys.exit(0)
        else:
            self.destroy()
