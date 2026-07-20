import json
import os
import stat
import keyring
from src.utils.logger import logger

class ConfigManager:
    """Gestiona la lectura y escritura de la configuración dinámica del sistema."""

    # La configuración vive en %APPDATA%/SEMS_Pro: cuando la app está instalada en
    # Program Files, el directorio de trabajo es de solo lectura para usuarios sin
    # privilegios y escribir config.json ahí falla con PermissionError.
    CONFIG_DIR = os.path.join(os.environ.get("APPDATA", os.getcwd()), "SEMS_Pro")
    CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")
    LEGACY_CONFIG_FILE = "config.json"
    SERVICE_NAME = "SEMS_App"

    @staticmethod
    def _resolve_config_file() -> str:
        """Retorna la ruta del config.json a leer, contemplando el archivo legado en CWD."""
        if os.path.exists(ConfigManager.CONFIG_FILE):
            return ConfigManager.CONFIG_FILE
        if os.path.exists(ConfigManager.LEGACY_CONFIG_FILE):
            return ConfigManager.LEGACY_CONFIG_FILE
        return ConfigManager.CONFIG_FILE
    
    @staticmethod
    def get_config() -> dict:
        """Retorna la configuración actual desde config.json y Keyring."""
        default_config = {
            "smtp_user": "",
            "smtp_password": "",
            "smtp_host": "smtp.gmail.com",
            "smtp_port": 587,
            "email_subject": "Documento seguro adjunto",
            "email_body": "Estimado usuario,\n\nAdjunto encontrará su documento seguro. Para garantizar la máxima privacidad, este archivo ha sido cifrado con altos estándares de seguridad (AES-256).\n\nPara abrir el archivo, por favor utilice su clave de seguridad asignada.\n\nAtentamente,\nEl equipo.",
            "sender_name": "SEMS Pro",
            "send_delay": 2,
            "logo_path": "",
            "pdf_password_prefix": "",
            "pdf_password_suffix": ""
        }
        
        # ROBUSTEZ: la lectura del Keyring es independiente del estado del JSON.
        # Antes, un config.json corrupto (o ausente) hacía retornar defaults sin
        # consultar el Keyring, "ocultando" credenciales SMTP que seguían intactas.
        config = dict(default_config)
        data = {}
        config_file = ConfigManager._resolve_config_file()
        if os.path.exists(config_file):
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                # Combinar datos cargados con defaults por si faltan claves
                config = {**default_config, **data}
            except Exception as e:
                logger.error(f"Error al leer config.json (se usarán valores por defecto): {e}")

        # Obtener credenciales seguras desde Windows Credential Manager (Keyring)
        try:
            creds_str = keyring.get_password(ConfigManager.SERVICE_NAME, "smtp_credentials")
            if creds_str:
                creds = json.loads(creds_str)
                config["smtp_user"] = creds.get("user", "")
                config["smtp_password"] = creds.get("password", "")
            else:
                # Fallback de compatibilidad para versiones anteriores que tenían smtp_user en config.json.
                # Si encontramos datos legados, los migramos automáticamente a Keyring y limpiamos el JSON.
                old_user = config.get("smtp_user", "")
                if old_user:
                    pw = keyring.get_password(ConfigManager.SERVICE_NAME, old_user)
                    config["smtp_password"] = pw if pw else ""

                    # Migración automática: persistir en el nuevo formato de Keyring
                    if pw:
                        creds = json.dumps({"user": old_user, "password": pw})
                        keyring.set_password(ConfigManager.SERVICE_NAME, "smtp_credentials", creds)
                        logger.info("Credenciales migradas automáticamente al nuevo formato de Keyring.")

                    # Limpiar smtp_user del archivo JSON en disco (en la misma ruta leída)
                    if "smtp_user" in data:
                        del data["smtp_user"]
                        try:
                            with open(config_file, 'w', encoding='utf-8') as fw:
                                json.dump(data, fw, indent=4, ensure_ascii=False)
                            logger.info("Campo 'smtp_user' eliminado de config.json tras migración.")
                        except Exception as ew:
                            logger.warning(f"No se pudo limpiar smtp_user de config.json: {ew}")
                else:
                    config["smtp_password"] = ""
        except Exception as e:
            logger.critical(f"Fallo crítico al acceder a la bóveda de credenciales del SO (Keyring): {e}")
            config["smtp_password"] = ""
            config["keyring_failed"] = True

        return config
            
    @staticmethod
    def save_config(smtp_user, smtp_password, smtp_host, smtp_port, email_subject, email_body, send_delay=2, sender_name="SEMS Pro", logo_path="", pdf_password_prefix="", pdf_password_suffix=""):
        """Guarda la configuración actualizando el archivo y Keyring."""
        config = {
            "smtp_host": smtp_host,
            "smtp_port": int(smtp_port) if smtp_port else 587,
            "email_subject": email_subject,
            "email_body": email_body,
            "sender_name": sender_name,
            "send_delay": int(send_delay),
            "logo_path": logo_path,
            "pdf_password_prefix": pdf_password_prefix,
            "pdf_password_suffix": pdf_password_suffix
        }
        
        try:
            # Guardar datos públicos en JSON (siempre en %APPDATA%/SEMS_Pro)
            os.makedirs(ConfigManager.CONFIG_DIR, exist_ok=True)
            with open(ConfigManager.CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=4, ensure_ascii=False)

            # Migración: retirar el config.json legado del directorio de trabajo
            # para que futuras lecturas no encuentren datos desactualizados.
            try:
                if os.path.exists(ConfigManager.LEGACY_CONFIG_FILE) and \
                   os.path.abspath(ConfigManager.LEGACY_CONFIG_FILE) != os.path.abspath(ConfigManager.CONFIG_FILE):
                    os.remove(ConfigManager.LEGACY_CONFIG_FILE)
                    logger.info("config.json legado del directorio de trabajo migrado a APPDATA.")
            except Exception as em:
                logger.warning(f"No se pudo retirar el config.json legado: {em}")
            
            # Restringir permisos del archivo: solo lectura/escritura para el propietario
            try:
                if os.name == 'nt':
                    import subprocess
                    creationflags = 0
                    if hasattr(subprocess, 'CREATE_NO_WINDOW'):
                        creationflags = subprocess.CREATE_NO_WINDOW
                    # *S-1-3-4 = OWNER RIGHTS: concede al propietario actual del archivo,
                    # sin depender del nombre de usuario del entorno (que falla con cuentas
                    # Microsoft o nombres localizados).
                    subprocess.run(
                        ["icacls", ConfigManager.CONFIG_FILE, "/inheritance:r",
                         "/grant:r", "*S-1-3-4:(R,W)"],
                        capture_output=True, check=True, creationflags=creationflags
                    )
                else:
                    os.chmod(ConfigManager.CONFIG_FILE, stat.S_IRUSR | stat.S_IWUSR)
            except Exception as e:
                logger.warning(f"No se pudieron restringir los permisos de config.json: {e}")
                
            # Guardar credenciales de forma segura en Windows Credential Manager
            if smtp_user:
                password_to_save = smtp_password
                if password_to_save == "••••••••":
                    # Intentar obtener la contraseña anterior del Keyring
                    try:
                        old_creds_str = keyring.get_password(ConfigManager.SERVICE_NAME, "smtp_credentials")
                        if old_creds_str:
                            old_creds = json.loads(old_creds_str)
                            password_to_save = old_creds.get("password", "")
                        else:
                            # Buscar en el formato legado
                            old_pw = keyring.get_password(ConfigManager.SERVICE_NAME, smtp_user)
                            password_to_save = old_pw if old_pw else ""
                    except Exception:
                        password_to_save = ""
                
                if password_to_save:
                    creds = json.dumps({"user": smtp_user, "password": password_to_save})
                    keyring.set_password(ConfigManager.SERVICE_NAME, "smtp_credentials", creds)
                
            logger.info("Configuración y credenciales guardadas exitosamente.")
            return True
        except Exception as e:
            logger.error(f"Error al guardar configuración: {e}")
            return False
