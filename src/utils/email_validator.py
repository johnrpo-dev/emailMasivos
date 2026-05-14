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

# Nombres de dominio mal escritos -> nombre correcto (sin TLD)
# Esto permite detectar typos sin importar el TLD (.com, .es, .co, etc.)
DOMAIN_NAME_TYPOS = {
    # Gmail
    "gmial": "gmail",
    "gmal": "gmail",
    "gamil": "gmail",
    "gnail": "gmail",
    "gmaill": "gmail",
    "gmali": "gmail",
    "gmaul": "gmail",
    "gmeil": "gmail",
    "gemail": "gmail",
    "gimail": "gmail",
    "gmai": "gmail",
    # Hotmail
    "hotmal": "hotmail",
    "hotmial": "hotmail",
    "hotamil": "hotmail",
    "hotmil": "hotmail",
    "hotmeil": "hotmail",
    "hotmaill": "hotmail",
    "hotmali": "hotmail",
    "hotmai": "hotmail",
    "hotmal": "hotmail",
    "hotamail": "hotmail",
    "htomail": "hotmail",
    "hotmaiil": "hotmail",
    # Outlook
    "outlok": "outlook",
    "outllook": "outlook",
    "outloock": "outlook",
    "outlool": "outlook",
    "outook": "outlook",
    "outiook": "outlook",
    # Yahoo
    "yaho": "yahoo",
    "yahooo": "yahoo",
    "yhoo": "yahoo",
    "yaoo": "yahoo",
    "yahho": "yahoo",
    "yhaoo": "yahoo",
}

# Dominios conocidos y su TLD correcto
KNOWN_DOMAINS = {
    "gmail": "gmail.com",
    "hotmail": "hotmail.com",
    "outlook": "outlook.com",
    "yahoo": "yahoo.com",
}

# TLDs invalidos comunes (typos de .com)
INVALID_TLDS = {"con", "cm", "om", "comm", "cmo", "co"}



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
    
    # Extraer dominio y separar nombre de TLD
    domain = email.split("@")[1]
    parts = domain.rsplit(".", 1)
    if len(parts) != 2:
        return EmailValidationResult(
            email=email, is_valid=False, error_type="formato",
            message=f"Dominio invalido: '{domain}'"
        )
    domain_name, tld = parts[0], parts[1]
    
    # Nivel 2: Detectar typos en el nombre del dominio (sin importar TLD)
    # Ej: hotmial.es, gmial.co, gamil.com -> todos detectados
    if domain_name in DOMAIN_NAME_TYPOS:
        correct_name = DOMAIN_NAME_TYPOS[domain_name]
        suggested_domain = KNOWN_DOMAINS.get(correct_name, f"{correct_name}.com")
        suggested_email = email.split("@")[0] + "@" + suggested_domain
        return EmailValidationResult(
            email=email,
            is_valid=False,
            error_type="typo_dominio",
            message=f"Posible typo en dominio: '{domain}' -- Quisiste decir '{suggested_domain}'?",
            suggestion=suggested_email
        )
    
    # Nivel 2b: Nombre correcto pero TLD mal escrito
    # Ej: gmail.con, hotmail.cm, outlook.om
    if domain_name in KNOWN_DOMAINS and tld in INVALID_TLDS:
        suggested_domain = KNOWN_DOMAINS[domain_name]
        suggested_email = email.split("@")[0] + "@" + suggested_domain
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
