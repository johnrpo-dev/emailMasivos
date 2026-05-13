import logging
import os

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
        
        # Handler para archivo
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        
        # Handler para consola
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
        
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
logger = setup_logger()
