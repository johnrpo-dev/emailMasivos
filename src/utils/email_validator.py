"""
Módulo de validación de correos electrónicos.
Valida formato, dominios con typos comunes, y existencia de servidores MX.
"""
import re
import socket
from src.utils.logger import logger

# Regex para validación de formato de email (RFC 5322 simplificado)
EMAIL_REGEX = re.compile(
    r'^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$'
)

# Dominios comunes y sus typos frecuentes
DOMAIN_TYPOS = {
    # Gmail
    "gmial.com": "gmail.com",
    "gmal.com": "gmail.com",
    "gamil.com": "gmail.com",
    "gnail.com": "gmail.com",
    "gmaill.com": "gmail.com",
    "gmali.com": "gmail.com",
    "gmail.co": "gmail.com",
    "gmaul.com": "gmail.com",
    "gmeil.com": "gmail.com",
    "gmail.con": "gmail.com",
    "gmail.om": "gmail.com",
    "gmail.cm": "gmail.com",
    # Hotmail
    "hotmal.com": "hotmail.com",
    "hotmial.com": "hotmail.com",
    "hotamil.com": "hotmail.com",
    "hotmil.com": "hotmail.com",
    "hotmail.co": "hotmail.com",
    "hotmail.con": "hotmail.com",
    "hotmeil.com": "hotmail.com",
    "hotmaill.com": "hotmail.com",
    # Outlook
    "outlok.com": "outlook.com",
    "outllook.com": "outlook.com",
    "outlook.co": "outlook.com",
    "outlook.con": "outlook.com",
    "outloock.com": "outlook.com",
    # Yahoo
    "yaho.com": "yahoo.com",
    "yahooo.com": "yahoo.com",
    "yahoo.co": "yahoo.com",
    "yahoo.con": "yahoo.com",
    "yhoo.com": "yahoo.com",
    "yaoo.com": "yahoo.com",
}


class EmailValidationResult:
    """Resultado de la validación de un email."""
    def __init__(self, email: str, is_valid: bool, error_type: str = None, message: str = None, suggestion: str = None):
        self.email = email
        self.is_valid = is_valid
        self.error_type = error_type      # "formato", "typo_dominio", "dominio_inexistente"
        self.message = message
        self.suggestion = suggestion       # Corrección sugerida (si aplica)


def validate_email(email: str) -> EmailValidationResult:
    """
    Valida un correo electrónico en 3 niveles:
    1. Formato (regex)
    2. Typos en dominios comunes
    3. Existencia del dominio (DNS lookup)
    
    Returns:
        EmailValidationResult con el resultado de la validación.
    """
    email = email.strip().lower()
    
    # Nivel 1: Validar formato básico
    if not EMAIL_REGEX.match(email):
        return EmailValidationResult(
            email=email,
            is_valid=False,
            error_type="formato",
            message=f"Formato de email inválido: '{email}'"
        )
    
    # Extraer dominio
    domain = email.split("@")[1]
    
    # Nivel 2: Detectar typos comunes en dominios
    if domain in DOMAIN_TYPOS:
        suggested_domain = DOMAIN_TYPOS[domain]
        suggested_email = email.replace(f"@{domain}", f"@{suggested_domain}")
        return EmailValidationResult(
            email=email,
            is_valid=False,
            error_type="typo_dominio",
            message=f"Posible typo en dominio: '{domain}' -- Quisiste decir '{suggested_domain}'?",
            suggestion=suggested_email
        )
    
    # Nivel 3: Verificar que el dominio tenga servidores de correo (MX/A record)
    if not _domain_has_mail_server(domain):
        return EmailValidationResult(
            email=email,
            is_valid=False,
            error_type="dominio_inexistente",
            message=f"El dominio '{domain}' no tiene servidores de correo válidos"
        )
    
    return EmailValidationResult(email=email, is_valid=True)


def _domain_has_mail_server(domain: str) -> bool:
    """
    Verifica si un dominio tiene servidores de correo.
    Usa socket.getaddrinfo como alternativa sin dependencias externas.
    Intenta resolver el dominio - si no se puede resolver, no es válido.
    """
    try:
        # Intentar resolver el dominio (verificar que existe)
        socket.getaddrinfo(domain, 25, socket.AF_UNSPEC, socket.SOCK_STREAM)
        return True
    except socket.gaierror:
        # Si falla puerto 25, intentar con puerto 443 (el dominio podría existir pero no tener puerto 25 abierto)
        try:
            socket.getaddrinfo(domain, 443, socket.AF_UNSPEC, socket.SOCK_STREAM)
            return True
        except socket.gaierror:
            return False
    except Exception:
        # En caso de error de red, asumir válido para no bloquear envíos
        logger.warning(f"No se pudo verificar el dominio '{domain}' (posible problema de red). Se permitirá el envío.")
        return True


def validate_emails_batch(emails: list) -> dict:
    """
    Valida una lista de emails y retorna los resultados agrupados.
    
    Returns:
        dict con keys: 'valid', 'invalid' (listas de EmailValidationResult)
    """
    results = {"valid": [], "invalid": []}
    
    for email in emails:
        result = validate_email(email)
        if result.is_valid:
            results["valid"].append(result)
        else:
            results["invalid"].append(result)
            logger.warning(f"Email inválido detectado: {result.message}")
    
    return results
