import keyring
from src.core.license_manager import LicenseManager

def main():
    print("==================================================")
    print("    SEMS Pro — DESACTIVADOR DE LICENCIA (RESET)   ")
    print("==================================================")
    
    try:
        # Verificar si hay una licencia registrada
        key_exists = keyring.get_password(LicenseManager.SERVICE_NAME, "license_key")
        
        if not key_exists:
            print("\n[!] No se encontró ninguna licencia activa registrada en este sistema.")
            return

        confirmacion = input("\n[?] ¿Está seguro de que desea desactivar/eliminar la licencia actual? (s/n): ").strip().lower()
        if confirmacion == 's':
            # Eliminar las credenciales de la bóveda de Windows
            try:
                keyring.delete_password(LicenseManager.SERVICE_NAME, "license_key")
            except Exception:
                pass
                
            try:
                keyring.delete_password(LicenseManager.SERVICE_NAME, "expiration_date")
            except Exception:
                pass
                
            try:
                keyring.delete_password(LicenseManager.SERVICE_NAME, "last_run")
            except Exception:
                pass
                
            print("\n[+] ¡Licencia eliminada con éxito!")
            print("[+] La aplicación volverá a pedir la pantalla de activación en el siguiente arranque.")
        else:
            print("\n[-] Operación cancelada por el usuario.")
            
    except Exception as e:
        print(f"\n[-] Error al intentar limpiar el almacén de credenciales: {str(e)}")
        
    print("==================================================")

if __name__ == "__main__":
    main()
