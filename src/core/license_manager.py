import keyring
import json
import base64
from datetime import datetime, timedelta
from cryptography.hazmat.primitives.asymmetric import ed25519
from src.utils.logger import logger

class LicenseManager:
    SERVICE_NAME = "SEMS_Pro_Licensing"
    PUBLIC_KEY_HEX = "caf90aeba6174a24891e0da1c366052e88fb3a60b28aa1c80301aab1856bd7b6"

    @staticmethod
    def verify_signature(license_base64: str) -> dict:
        """Valida la firma Ed25519 y retorna el payload si es correcto."""
        try:
            public_key = ed25519.Ed25519PublicKey.from_public_bytes(
                bytes.fromhex(LicenseManager.PUBLIC_KEY_HEX)
            )
            
            # Asegurar que el relleno Base64 sea correcto ante posibles pérdidas en copiar/pegar
            missing_padding = len(license_base64) % 4
            if missing_padding:
                license_base64 += '=' * (4 - missing_padding)
                
            # Decodificar el token Base64
            license_json = base64.b64decode(license_base64.encode('utf-8')).decode('utf-8')
            license_data = json.loads(license_json)
            
            firma = bytes.fromhex(license_data["signature"])
            payload = license_data["payload"] # {"email": "...", "expires": "..."}
            
            # Serializar de la misma forma que en el generador (sort_keys=True)
            json_payload = json.dumps(payload, sort_keys=True)
            
            # Verificar firma criptográfica
            public_key.verify(firma, json_payload.encode('utf-8'))
            return payload
        except Exception as e:
            logger.error(f"Fallo en verificación criptográfica de la licencia: {str(e)}")
            return None

    @staticmethod
    def is_license_active() -> bool:
        """Verifica la validez de la licencia y la consistencia del reloj (monotonic tracking)."""
        try:
            license_key = keyring.get_password(LicenseManager.SERVICE_NAME, "license_key")
            exp_date_str = keyring.get_password(LicenseManager.SERVICE_NAME, "expiration_date")
            last_run_str = keyring.get_password(LicenseManager.SERVICE_NAME, "last_run")
            
            if not license_key or not exp_date_str:
                return False

            # Verificar la firma criptográfica de la licencia guardada para evitar bypass local
            payload = LicenseManager.verify_signature(license_key)
            if not payload or payload.get("expires") != exp_date_str:
                logger.critical("SEGURIDAD: La clave de licencia almacenada es inválida o ha sido alterada.")
                return False

            now = datetime.now()
            exp_date = datetime.fromisoformat(exp_date_str)
            
            # 1. ¿Licencia expirada?
            if now > exp_date:
                logger.warning(f"La licencia de prueba/suscripción ha expirado el {exp_date_str}.")
                return False
                
            # 2. ¿Reloj de Windows alterado hacia el pasado? (Tolerancia de 2 horas)
            if last_run_str:
                last_run = datetime.fromisoformat(last_run_str)
                # Si el reloj actual está más de 2 horas por detrás del último arranque guardado
                if now < (last_run - timedelta(hours=2)):
                    logger.error(f"Detección de alteración del reloj. Reloj actual: {now.isoformat()} | Último arranque registrado: {last_run_str}")
                    return False
                    
            return True
        except Exception as e:
            logger.error(f"Error al verificar el estado de la licencia en Keyring: {str(e)}")
            return False

    @staticmethod
    def save_license(license_base64: str, payload: dict) -> bool:
        """Almacena la clave de licencia y datos en la bóveda de credenciales."""
        try:
            keyring.set_password(LicenseManager.SERVICE_NAME, "license_key", license_base64)
            keyring.set_password(LicenseManager.SERVICE_NAME, "expiration_date", payload["expires"])
            keyring.set_password(LicenseManager.SERVICE_NAME, "last_run", datetime.now().isoformat())
            logger.info("Licencia guardada y activada exitosamente en Keyring.")
            return True
        except Exception as e:
            logger.error(f"No se pudo guardar la licencia en Keyring: {str(e)}")
            return False

    @staticmethod
    def update_last_run():
        """Actualiza la marca del último arranque exitoso para mantener consistencia horaria."""
        try:
            keyring.set_password(LicenseManager.SERVICE_NAME, "last_run", datetime.now().isoformat())
        except Exception as e:
            logger.warning(f"No se pudo actualizar last_run en Keyring: {str(e)}")
