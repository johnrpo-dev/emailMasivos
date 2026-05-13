import json
import os
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
            "email_subject": "Documento de {id_servicio}",
            "email_body": "Estimado usuario,\n\nAdjunto encontrará su documento seguro. Para garantizar la máxima privacidad, este archivo ha sido cifrado con altos estándares de seguridad (AES-256).\n\nPara abrir el archivo, por favor use su número de documento de identidad (cédula) sin espacios ni puntos como contraseña.\n\nAtentamente,\nEl equipo."
        }
        
        if not os.path.exists(ConfigManager.CONFIG_FILE):
            return default_config
            
        try:
            with open(ConfigManager.CONFIG_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            # Combinar datos cargados con defaults por si faltan claves
            config = {**default_config, **data}
            
            # Obtener contraseña desde Windows Credential Manager
            user = config.get("smtp_user", "")
            if user:
                try:
                    pw = keyring.get_password(ConfigManager.SERVICE_NAME, user)
                    config["smtp_password"] = pw if pw else ""
                except Exception as e:
                    logger.error(f"Error al leer keyring: {e}")
                    config["smtp_password"] = ""
            else:
                config["smtp_password"] = ""
                
            return config
            
        except Exception as e:
            logger.error(f"Error al leer config.json: {e}")
            return default_config
            
    @staticmethod
    def save_config(smtp_user, smtp_password, email_subject, email_body):
        """Guarda la configuración actualizando el archivo y Keyring."""
        config = {
            "smtp_user": smtp_user,
            "email_subject": email_subject,
            "email_body": email_body
        }
        
        try:
            # Guardar datos públicos en JSON
            with open(ConfigManager.CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=4, ensure_ascii=False)
                
            # Guardar contraseña de forma segura en Windows Credential Manager
            if smtp_user and smtp_password:
                keyring.set_password(ConfigManager.SERVICE_NAME, smtp_user, smtp_password)
                
            logger.info("Configuración y credenciales guardadas exitosamente.")
            return True
        except Exception as e:
            logger.error(f"Error al guardar configuración: {e}")
            return False
