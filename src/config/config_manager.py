import json
import os
import base64
from src.utils.logger import logger

class ConfigManager:
    """Gestiona la lectura y escritura de la configuración dinámica del sistema."""
    
    CONFIG_FILE = "config.json"
    
    @staticmethod
    def _encode_password(password: str) -> str:
        """Ofusca la contraseña en Base64."""
        if not password:
            return ""
        return base64.b64encode(password.encode('utf-8')).decode('utf-8')
        
    @staticmethod
    def _decode_password(encoded_password: str) -> str:
        """Desofusca la contraseña desde Base64."""
        if not encoded_password:
            return ""
        try:
            return base64.b64decode(encoded_password.encode('utf-8')).decode('utf-8')
        except Exception:
            return ""

    @staticmethod
    def get_config() -> dict:
        """Retorna la configuración actual. Si no existe, retorna valores por defecto."""
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
            
            # Decodificar contraseña
            config["smtp_password"] = ConfigManager._decode_password(config.get("smtp_password", ""))
            return config
            
        except Exception as e:
            logger.error(f"Error al leer config.json: {e}")
            return default_config
            
    @staticmethod
    def save_config(smtp_user, smtp_password, email_subject, email_body):
        """Guarda la configuración actualizando el archivo."""
        config = {
            "smtp_user": smtp_user,
            "smtp_password": ConfigManager._encode_password(smtp_password),
            "email_subject": email_subject,
            "email_body": email_body
        }
        
        try:
            with open(ConfigManager.CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=4, ensure_ascii=False)
            logger.info("Configuración guardada exitosamente.")
            return True
        except Exception as e:
            logger.error(f"Error al guardar config.json: {e}")
            return False
