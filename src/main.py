import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.license_manager import LicenseManager
from src.ui.modals.activation_modal import ActivationModal
from src.ui.app import App

def main():
    # 1. Verificar si la licencia está activa y el reloj es consistente
    if not LicenseManager.is_license_active():
        # Lanzar el modal premium de activación si no hay licencia válida
        activation = ActivationModal()
        activation.mainloop()
        
        # Si no se activó con éxito y se cerró el modal, abortar ejecución
        if not LicenseManager.is_license_active():
            sys.exit(0)
            
    # 2. Aviso no bloqueante si la licencia venció pero sigue en periodo de gracia
    if LicenseManager.get_license_state() == "grace":
        import customtkinter as ctk
        from src.ui import theme, dialogs
        # Si venimos de ActivationModal (root ya destruido), las fuentes cacheadas
        # apuntan a un Tk muerto: limpiar antes de crear este root temporal.
        theme.reset_font_cache()
        ctk.set_appearance_mode(theme.DEFAULT_APPEARANCE)
        _tmp_root = ctk.CTk()
        _tmp_root.withdraw()
        dialogs.show_warning(
            _tmp_root,
            "Licencia vencida — Periodo de gracia",
            f"Su licencia ha vencido. La aplicación seguirá funcionando durante un periodo "
            f"de gracia de {LicenseManager.GRACE_DAYS} días.\n\n"
            f"Contacte a su proveedor para renovar la suscripción y evitar la interrupción del servicio."
        )
        _tmp_root.destroy()

    # 3. Si ya está activa o se acaba de activar con éxito, registrar el arranque y lanzar app
    LicenseManager.update_last_run()
    app = App()
    app.mainloop()

if __name__ == "__main__":
    main()

