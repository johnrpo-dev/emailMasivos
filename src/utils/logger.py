import logging
import os
import re
from logging.handlers import RotatingFileHandler


class PIIFilter(logging.Filter):
    """Filtro que redacta automáticamente secuencias numéricas largas (cédulas/documentos)
    de los mensajes de log para prevenir exposición accidental de PII."""
    _pattern = re.compile(r'\b\d{7,}\b')
    
    def filter(self, record):
        if isinstance(record.msg, str):
            record.msg = self._pattern.sub('[REDACTED]', record.msg)
        return True


def setup_logger(log_file="app.log"):
    """Configura y retorna el logger principal de la aplicación."""
    logger = logging.getLogger("EnvioMasivo")
    logger.setLevel(logging.INFO)
    
    # Evitar handlers duplicados si se llama múltiples veces
    if not logger.handlers:
        # Formato de los logs
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        # Handler para archivo con rotación automática (5MB max, 3 backups)
        file_handler = RotatingFileHandler(log_file, maxBytes=5*1024*1024, backupCount=3, encoding='utf-8')
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        
        # Handler para consola
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
        
        # Filtro PII: redactar cédulas y documentos numéricos en todos los logs
        pii_filter = PIIFilter()
        logger.addFilter(pii_filter)
        
    return logger

def mask_email(email: str) -> str:
    """Ofusca un correo electrónico (ej. juan.perez@gmail.com -> j***z@gmail.com)."""
    if not email or "@" not in email:
        return email
    
    parts = email.split("@")
    name = parts[0]
    domain = parts[1]
    
    if len(name) <= 2:
        masked_name = name[0] + "***"
    else:
        masked_name = name[0] + "***" + name[-1]
        
    return f"{masked_name}@{domain}"

# Instancia global del logger
log_dir = os.path.join(os.environ.get("APPDATA", os.getcwd()), "SEMS_Pro")
os.makedirs(log_dir, exist_ok=True)
log_file_path = os.path.join(log_dir, "app.log")
logger = setup_logger(log_file_path)

