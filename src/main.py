import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.license_manager import LicenseManager
from src.ui.modals.activation_modal import ActivationModal
from src.ui.app import App


def _verificar_boveda_credenciales():
    """Comprueba que el almacén de credenciales del sistema esté operativo.

    keyring resuelve sus backends dinámicamente en tiempo de ejecución. Si el
    empaquetado del ejecutable omitiera el backend nativo, o si el servicio
    Administrador de Credenciales de Windows estuviera deshabilitado, tanto la
    activación de licencia como el guardado de credenciales SMTP fallarían de
    forma silenciosa. Se verifica al arranque para dar un diagnóstico claro en
    lugar de un error genérico más adelante.
    """
    try:
        import keyring
        backend = keyring.get_keyring()
        modulo = backend.__class__.__module__
        # keyring.backends.fail y .null son marcadores de "sin backend disponible":
        # se identifican por su módulo, no por el nombre de la clase.
        if modulo.startswith("keyring.backends.fail") or modulo.startswith("keyring.backends.null"):
            raise RuntimeError("no hay un almacén de credenciales disponible en el sistema")
        # Prueba funcional: una lectura real sobre un identificador inexistente debe
        # devolver None sin lanzar excepción.
        keyring.get_password("SEMS_Pro_Preflight", "check")
        return True, backend.__class__.__name__
    except Exception as e:
        return False, str(e)


def main():
    # 0. Verificación previa del almacén de credenciales del sistema
    ok_boveda, detalle = _verificar_boveda_credenciales()
    if not ok_boveda:
        import tkinter as tk
        from tkinter import messagebox
        _r = tk.Tk()
        _r.withdraw()
        messagebox.showerror(
            "SEMS Pro — Error de configuración del sistema",
            "No se pudo acceder al Administrador de Credenciales de Windows.\n\n"
            "La aplicación requiere este servicio para almacenar de forma segura la "
            "licencia y las credenciales de correo.\n\n"
            "Verifique que el servicio 'Administrador de credenciales' esté habilitado "
            "en su equipo y vuelva a intentarlo.\n\n"
            f"Detalle técnico: {detalle}"
        )
        _r.destroy()
        sys.exit(1)

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

