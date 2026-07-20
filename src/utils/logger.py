import logging
import os
import re
from logging.handlers import RotatingFileHandler


class PIIFilter(logging.Filter):
    """Filtro que redacta automáticamente secuencias numéricas (cédulas/documentos)
    de los mensajes de log usando dos estrategias complementarias:
    1. Contextual: prefijos como CC, NIT, ID, cédula (precisión quirúrgica).
    2. Catch-all: secuencias de 8+ dígitos sin contexto (red de seguridad).
    También filtra record.args para cubrir formateo %-style."""
    _contextual = re.compile(r'(?i)(c\.c\.|cc|nit|id|c[eé]dula|documento)([\s.:-]*)(\d{6,11})\b')
    # Catch-all ampliado a 6+ dígitos (M-06): las cédulas antiguas de 6-7 dígitos
    # también deben redactarse aunque no tengan prefijo contextual.
    _catchall = re.compile(r'\b(\d{6,11})\b')
    
    def _redact(self, text):
        """Aplica redacción contextual primero, luego catch-all sobre el resultado."""
        if not isinstance(text, str):
            return text
        text = self._contextual.sub(r'\1\2[REDACTED]', text)
        text = self._catchall.sub('[REDACTED]', text)
        return text
    
    def filter(self, record):
        # Redactar msg (cubre f-strings)
        if isinstance(record.msg, str):
            record.msg = self._redact(record.msg)
        # Redactar args (cubre %-style: logger.error("dato %s", cedula))
        if record.args:
            if isinstance(record.args, dict):
                record.args = {k: self._redact(v) if isinstance(v, str) else v for k, v in record.args.items()}
            elif isinstance(record.args, tuple):
                record.args = tuple(self._redact(a) if isinstance(a, str) else a for a in record.args)
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
    if not email:
        return email

    # Entradas sin '@' (formatos inválidos tecleados por el usuario) también se
    # ofuscan: devolverlas intactas filtraría el texto original a logs/UI.
    if "@" not in email:
        if len(email) <= 2:
            return email[:1] + "***"
        return email[0] + "***" + email[-1]

    parts = email.split("@")
    name = parts[0]
    domain = parts[1]
    
    if not name:
        return f"***@{domain}"
    
    if len(name) <= 2:
        masked_name = name[0] + "***"
    else:
        masked_name = name[0] + "***" + name[-1]
        
    return f"{masked_name}@{domain}"

def mask_filename(filename: str) -> str:
    """Ofusca un nombre de archivo para logs persistentes conservando la extensión.

    Los nombres de PDF suelen contener nombres de pacientes (ej. juan_perez_123.pdf);
    el PIIFilter redacta los dígitos pero no los nombres. Ej.: juan_perez_123.pdf -> ju***23.pdf
    """
    if not filename:
        return filename
    base = os.path.basename(str(filename))
    stem, dot, ext = base.rpartition(".")
    if not dot:
        stem, ext = base, ""
    if len(stem) <= 4:
        masked = stem[:1] + "***"
    else:
        masked = stem[:2] + "***" + stem[-2:]
    return f"{masked}.{ext}" if ext else masked

# Instancia global del logger
log_dir = os.path.join(os.environ.get("APPDATA", os.getcwd()), "SEMS_Pro")
os.makedirs(log_dir, exist_ok=True)
log_file_path = os.path.join(log_dir, "app.log")
logger = setup_logger(log_file_path)

