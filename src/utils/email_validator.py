"""
Módulo de validación de correos electrónicos.
Valida formato, dominios con typos comunes, y existencia de servidores MX.
"""
import re
import socket
import threading
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
    "gamail": "gmail",
    "gmaio": "gmail",
    "gmil": "gmail",
    # Hotmail
    "hotmal": "hotmail",
    "hotmial": "hotmail",
    "hotamil": "hotmail",
    "hotmil": "hotmail",
    "hotmeil": "hotmail",
    "hotmaill": "hotmail",
    "hotmali": "hotmail",
    "hotmai": "hotmail",
    "hotamail": "hotmail",
    "htomail": "hotmail",
    "hotmaiil": "hotmail",
    "homail": "hotmail",
    "htmail": "hotmail",
    "hotail": "hotmail",
    "hotmall": "hotmail",
    "hotmaul": "hotmail",
    # Outlook
    "outlok": "outlook",
    "outllook": "outlook",
    "outloock": "outlook",
    "outlool": "outlook",
    "outook": "outlook",
    "outiook": "outlook",
    "outlookk": "outlook",
    "outloook": "outlook",
    "outluk": "outlook",
    "outlouk": "outlook",
    "oultook": "outlook",
    "outlokk": "outlook",
    "oulook": "outlook",
    "outllok": "outlook",
    "ouutlook": "outlook",
    "outlock": "outlook",
    # Live
    "lve": "live",
    "liive": "live",
    "livee": "live",
    "ive": "live",
    "liv": "live",
    # MSN
    "msnn": "msn",
    "mns": "msn",
    # Yahoo
    "yaho": "yahoo",
    "yahooo": "yahoo",
    "yhoo": "yahoo",
    "yaoo": "yahoo",
    "yahho": "yahoo",
    "yhaoo": "yahoo",
    "yahhoo": "yahoo",
    "yaboo": "yahoo",
    "yahho": "yahoo",
    # Ymail (Yahoo)
    "ymial": "ymail",
    "ymall": "ymail",
    "ymaiil": "ymail",
    # AOL
    "aoll": "aol",
    "aaol": "aol",
    "aool": "aol",
    # iCloud
    "iclould": "icloud",
    "icoud": "icloud",
    "iclooud": "icloud",
    "iclod": "icloud",
    "icluod": "icloud",
    # ProtonMail
    "protonmal": "protonmail",
    "protonmial": "protonmail",
    "protonmall": "protonmail",
    "protonmaill": "protonmail",
    "protnmail": "protonmail",
    # Zoho
    "zho": "zoho",
    "zooh": "zoho",
    "zhoo": "zoho",
}

# Proveedores conocidos: nombre correcto -> dominio mas comun
# Si el nombre coincide exactamente, se considera valido sin importar TLD
KNOWN_PROVIDERS = {
    "gmail": "gmail.com",
    "hotmail": "hotmail.com",
    "outlook": "outlook.com",
    "live": "live.com",
    "msn": "msn.com",
    "yahoo": "yahoo.com",
    "ymail": "ymail.com",
    "aol": "aol.com",
    "icloud": "icloud.com",
    "protonmail": "protonmail.com",
    "zoho": "zoho.com",
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
    
    # Extraer dominio completo y el nombre base del proveedor
    domain = email.split("@")[1]
    # Tomar solo la primera parte antes del primer punto
    # Ej: "hotmial.es" -> "hotmial", "empresa.com.co" -> "empresa"
    domain_name = domain.split(".")[0]
    
    # Nivel 2: Solo verificar si el NOMBRE del proveedor esta mal escrito
    # hotmial.es, hotmial.com, hotmial.co -> todos detectados (nombre incorrecto)
    # hotmail.es, hotmail.com, hotmail.co -> todos validos (nombre correcto)
    # empresa.com.co -> transparente (no es proveedor conocido)
    if domain_name in DOMAIN_NAME_TYPOS:
        correct_name = DOMAIN_NAME_TYPOS[domain_name]
        # Conservar el TLD original del usuario (solo corregir el nombre)
        # hotmial.es -> hotmail.es, gmial.com -> gmail.com
        tld_part = domain[len(domain_name):]  # ".es", ".com", ".co", ".com.co"
        suggested_domain = correct_name + tld_part
        suggested_email = email.split("@")[0] + "@" + suggested_domain
        return EmailValidationResult(
            email=email,
            is_valid=False,
            error_type="typo_dominio",
            message=f"Posible typo en dominio: '{domain}' -- Quisiste decir '{suggested_domain}'?",
            suggestion=suggested_email
        )
    # Si el nombre del proveedor esta bien escrito (gmail, hotmail, etc.),
    # es valido sin importar el TLD (.com, .es, .co, etc.)
    if domain_name in KNOWN_PROVIDERS:
        return EmailValidationResult(email=email, is_valid=True)
    
    # Nivel 3: Para dominios desconocidos/corporativos, verificar DNS
    # Ej: empresa.com.co -> verificar que exista
    if not _domain_has_mail_server(domain):
        return EmailValidationResult(
            email=email,
            is_valid=False,
            error_type="dominio_inexistente",
            message=f"El dominio '{domain}' no tiene servidores de correo validos"
        )
    
    return EmailValidationResult(email=email, is_valid=True)


def _resolve_domain_with_timeout(domain: str, port: int, timeout: float = 2.0) -> bool:
    """
    Intenta resolver el dominio y puerto usando socket.getaddrinfo en un hilo secundario
    para imponer un timeout estricto, previniendo bloqueos prolongados o indefinidos de DNS.
    """
    res_list = []
    exception_holder = []

    def target():
        try:
            res = socket.getaddrinfo(domain, port, socket.AF_UNSPEC, socket.SOCK_STREAM)
            res_list.append(res)
        except Exception as e:
            exception_holder.append(e)

    thread = threading.Thread(target=target)
    thread.daemon = True
    thread.start()
    thread.join(timeout)

    if thread.is_alive():
        logger.warning(f"La resolución DNS para {domain}:{port} excedió el tiempo límite de {timeout}s.")
        raise TimeoutError("DNS query timed out")

    if exception_holder:
        raise exception_holder[0]

    return len(res_list) > 0


def _domain_has_mail_server(domain: str) -> bool:
    """
    Verifica si un dominio tiene servidores de correo.
    Usa _resolve_domain_with_timeout para evitar bloqueos por DNS lentos o caídos.
    """
    if not domain or not isinstance(domain, str):
        return False

    try:
        # Intentar resolver el dominio en el puerto 25 con timeout de 2.0s
        _resolve_domain_with_timeout(domain, 25, timeout=2.0)
        return True
    except (socket.gaierror, socket.herror):
        # Si falla puerto 25 por dominio inexistente, intentar con puerto 443
        try:
            _resolve_domain_with_timeout(domain, 443, timeout=2.0)
            return True
        except (socket.gaierror, socket.herror):
            return False
        except (TimeoutError, socket.timeout):
            logger.warning(f"Resolución de fallback (443) para '{domain}' expiró. Se asume válido para no bloquear envíos.")
            return True
        except Exception as e:
            logger.warning(f"Error inesperado al verificar '{domain}' en puerto 443: {str(e)}. Se permitirá el envío.")
            return True
    except (TimeoutError, socket.timeout):
        # Si expira por completo en puerto 25, asumimos válido para no bloquear al usuario
        logger.warning(f"La resolución DNS principal para '{domain}' expiró (timeout). Se asumirá válido para no bloquear el proceso.")
        return True
    except Exception as e:
        # En caso de otros errores inesperados, asumir válido
        logger.warning(f"Error inesperado al verificar el dominio '{domain}': {str(e)}. Se permitirá el envío.")
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
