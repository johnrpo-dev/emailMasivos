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
            
    # 2. Si ya está activa o se acaba de activar con éxito, registrar el arranque y lanzar app
    LicenseManager.update_last_run()
    app = App()
    app.mainloop()

if __name__ == "__main__":
    main()

