import json
import os
import stat
import keyring
from src.utils.logger import logger

class ConfigManager:
    """Gestiona la lectura y escritura de la configuración dinámica del sistema."""
    
    CONFIG_FILE = "config.json"
    SERVICE_NAME = "SEMS_App"
    
    @staticmethod
    def get_config() -> dict:
        """Retorna la configuración actual desde config.json y Keyring."""
        default_config = {
            "smtp_user": "",
            "smtp_password": "",
            "smtp_host": "smtp.gmail.com",
            "smtp_port": 587,
            "email_subject": "Documento de {id_servicio}",
            "email_body": "Estimado usuario,\n\nAdjunto encontrará su documento seguro. Para garantizar la máxima privacidad, este archivo ha sido cifrado con altos estándares de seguridad (AES-256).\n\nPara abrir el archivo, por favor utilice su clave de seguridad asignada.\n\nAtentamente,\nEl equipo.",
            "sender_name": "SEMS Pro",
            "send_delay": 2,
            "logo_path": ""
        }
        
        if not os.path.exists(ConfigManager.CONFIG_FILE):
            return default_config
            
        try:
            with open(ConfigManager.CONFIG_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            # Combinar datos cargados con defaults por si faltan claves
            config = {**default_config, **data}
            
            # Obtener credenciales seguras desde Windows Credential Manager (Keyring)
            try:
                creds_str = keyring.get_password(ConfigManager.SERVICE_NAME, "smtp_credentials")
                if creds_str:
                    creds = json.loads(creds_str)
                    config["smtp_user"] = creds.get("user", "")
                    config["smtp_password"] = creds.get("password", "")
                else:
                    # Fallback de compatibilidad para versiones anteriores que tenían smtp_user en config.json
                    old_user = config.get("smtp_user", "")
                    if old_user:
                        pw = keyring.get_password(ConfigManager.SERVICE_NAME, old_user)
                        config["smtp_password"] = pw if pw else ""
                    else:
                        config["smtp_password"] = ""
            except Exception as e:
                logger.critical(f"Fallo crítico al acceder a la bóveda de credenciales del SO (Keyring): {e}")
                config["smtp_password"] = ""
                config["keyring_failed"] = True
                
            return config
            
        except Exception as e:
            logger.error(f"Error al leer config.json: {e}")
            return default_config
            
    @staticmethod
    def save_config(smtp_user, smtp_password, smtp_host, smtp_port, email_subject, email_body, send_delay=2, sender_name="SEMS Pro", logo_path=""):
        """Guarda la configuración actualizando el archivo y Keyring."""
        config = {
            "smtp_host": smtp_host,
            "smtp_port": int(smtp_port) if smtp_port else 587,
            "email_subject": email_subject,
            "email_body": email_body,
            "sender_name": sender_name,
            "send_delay": int(send_delay),
            "logo_path": logo_path
        }
        
        try:
            # Guardar datos públicos en JSON
            with open(ConfigManager.CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=4, ensure_ascii=False)
            
            # Restringir permisos del archivo: solo lectura/escritura para el propietario
            try:
                os.chmod(ConfigManager.CONFIG_FILE, stat.S_IRUSR | stat.S_IWUSR)
            except OSError:
                logger.warning("No se pudieron restringir los permisos de config.json")
                
            # Guardar credenciales de forma segura en Windows Credential Manager
            if smtp_user and smtp_password:
                creds = json.dumps({"user": smtp_user, "password": smtp_password})
                keyring.set_password(ConfigManager.SERVICE_NAME, "smtp_credentials", creds)
                
            logger.info("Configuración y credenciales guardadas exitosamente.")
            return True
        except Exception as e:
            logger.error(f"Error al guardar configuración: {e}")
            return False
