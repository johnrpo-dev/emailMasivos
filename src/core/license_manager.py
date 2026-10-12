import keyring
import json
import base64
from datetime import datetime, timedelta, timezone
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric import ed25519
from src.utils.logger import logger

class LicenseManager:
    SERVICE_NAME = "SEMS_Pro_Licensing"
    # SEGURIDAD: llaves públicas Ed25519 en las que confía la aplicación.
    #
    # La PRIMERA es la activa: con ella se firman las licencias nuevas y contra
    # ella verifica el emisor. Las siguientes son llaves retiradas que se
    # conservan para no invalidar licencias ya entregadas y todavía vigentes.
    #
    # Al rotar: ponga la nueva al principio y conserve la anterior mientras haya
    # licencias suyas en circulación. Asi una rotacion deja de obligar a
    # reinstalar y reactivar en los equipos del cliente.
    #
    # Historial:
    #   4a203277...b5c0c988 - retirada 2026-08-14 (passphrase perdida). Sin
    #       licencias vigentes en circulacion: se elimino de la lista.
    #   90b59b8d...e8727689 - retirada 2026-08-22 (passphrase perdida). Firma la
    #       licencia 2 del cliente (vence 14/10/2026, gracia hasta el 21/10).
    #       Puede retirarse en una version posterior a esa fecha.
    #   8c0c1d15...d5efaf81 - ACTIVA desde 2026-10. Firma las licencias 3 a 6 y
    #       la PERPETUA del cliente: NUNCA retirarla de esta lista, o la
    #       licencia perpetua dejaria de validar al actualizar la aplicacion.
    #
    # Cada entrada debe ser el hex de una llave Ed25519 de 32 bytes (64 chars).
    # tests/test_license_multikey.py falla si alguna no lo es: un marcador como
    # "PENDIENTE_NUEVA_LLAVE" bloquea el release hasta pegar la llave real.
    PUBLIC_KEYS_HEX = [
        "8c0c1d15a3c6bd661e971ec2017c8b6f0f35ef87a76f1bd7ba0eec76d5efaf81",
        "90b59b8d0d2a72563e02ef11c4fbb4a2415cf5c0beccf67b3ff2a37de8727689",
    ]

    # Alias de solo lectura de la llave activa (PUBLIC_KEYS_HEX[0]), usado por
    # los scripts emisores. Al rotar NO se edita aqui: se edita la lista.
    PUBLIC_KEY_HEX = PUBLIC_KEYS_HEX[0]

    # Periodo de gracia tras el vencimiento (días). Evita bloquear en seco a un
    # cliente al día por un retraso administrativo en la renovación mensual.
    GRACE_DAYS = 7

    # Licencia perpetua (consolidación del mes 6, cláusula Décima Segunda): se
    # emite con vencimiento simbólico 31/12/2099. Desde ese año se considera que
    # no vence, y además no se le aplica la detección de retroceso de reloj: ese
    # chequeo solo evita estirar un vencimiento real, y en una perpetua bloquearía
    # al cliente por un desajuste de hora sin proteger nada.
    PERPETUA_DESDE_ANIO = 2099

    @staticmethod
    def es_perpetua(exp_date: datetime) -> bool:
        """True si el vencimiento corresponde a una licencia perpetua."""
        return exp_date.year >= LicenseManager.PERPETUA_DESDE_ANIO

    @staticmethod
    def _parse_iso_datetime(iso_str: str) -> datetime:
        """Parsea una cadena ISO y se asegura de retornar un objeto datetime en UTC (aware)."""
        dt = datetime.fromisoformat(iso_str)
        if dt.tzinfo is None:
            # Si no tiene timezone, asumimos UTC por compatibilidad
            dt = dt.replace(tzinfo=timezone.utc)
        else:
            dt = dt.astimezone(timezone.utc)
        return dt

    @staticmethod
    def parse_public_key(hex_llave: str) -> ed25519.Ed25519PublicKey:
        """Convierte el hex de una llave pública Ed25519. Lanza ValueError si está mal formada."""
        try:
            crudo = bytes.fromhex(hex_llave)
        except ValueError:
            raise ValueError("no es hexadecimal valido") from None
        if len(crudo) != 32:
            raise ValueError(f"mide {len(crudo)} bytes, se esperaban 32")
        return ed25519.Ed25519PublicKey.from_public_bytes(crudo)

    @staticmethod
    def verify_signature(license_base64: str) -> dict:
        """Valida la firma Ed25519 y retorna el payload si es correcto."""
        try:
            # Asegurar que el relleno Base64 sea correcto ante posibles pérdidas en copiar/pegar
            missing_padding = len(license_base64) % 4
            if missing_padding:
                license_base64 += '=' * (4 - missing_padding)
                
            # Decodificar el token Base64
            license_json = base64.b64decode(license_base64.encode('utf-8')).decode('utf-8')
            license_data = json.loads(license_json)
            
            firma = bytes.fromhex(license_data["signature"])
            payload = license_data["payload"] # {"email": "...", "expires": "..."}
            
            # Serializar de la misma forma que en el generador (sort_keys=True)
            json_payload = json.dumps(payload, sort_keys=True)
            
            # Verificar contra cada llave confiable: basta que una valide.
            # Permite que convivan licencias firmadas antes y despues de una rotacion.
            for posicion, hex_llave in enumerate(LicenseManager.PUBLIC_KEYS_HEX):
                try:
                    llave = LicenseManager.parse_public_key(hex_llave)
                except ValueError as e:
                    # Una llave mal pegada no debe pasar por "firma no corresponde".
                    logger.error(f"Llave pública confiable #{posicion} mal formada ({e}); se omite.")
                    continue
                try:
                    llave.verify(firma, json_payload.encode('utf-8'))
                    return payload
                except InvalidSignature:
                    continue
            raise ValueError("la firma no corresponde a ninguna llave confiable")
        except Exception as e:
            logger.error(f"Fallo en verificación criptográfica de la licencia: {str(e)}")
            return None

    @staticmethod
    def get_license_state() -> str:
        """Evalúa la licencia y la consistencia del reloj (monotonic tracking).

        Retorna:
            'active'   — licencia válida y vigente.
            'grace'    — licencia vencida pero dentro del periodo de gracia (GRACE_DAYS).
            'inactive' — sin licencia, firma inválida, vencida fuera de gracia o reloj alterado.
        """
        try:
            license_key = keyring.get_password(LicenseManager.SERVICE_NAME, "license_key")
            exp_date_str = keyring.get_password(LicenseManager.SERVICE_NAME, "expiration_date")
            last_run_str = keyring.get_password(LicenseManager.SERVICE_NAME, "last_run")

            if not license_key or not exp_date_str:
                return "inactive"

            # Verificar la firma criptográfica de la licencia guardada para evitar bypass local
            payload = LicenseManager.verify_signature(license_key)
            if not payload or payload.get("expires") != exp_date_str:
                logger.critical("SEGURIDAD: La clave de licencia almacenada es inválida o ha sido alterada.")
                return "inactive"

            now = datetime.now(timezone.utc)
            exp_date = LicenseManager._parse_iso_datetime(exp_date_str)

            if LicenseManager.es_perpetua(exp_date):
                return "active"

            # 1. ¿Reloj de Windows alterado hacia el pasado? (Tolerancia de 2 horas)
            if last_run_str:
                last_run = LicenseManager._parse_iso_datetime(last_run_str)
                # Si el reloj actual está más de 2 horas por detrás del último arranque guardado
                if now < (last_run - timedelta(hours=2)):
                    logger.error(f"Detección de alteración del reloj. Reloj actual: {now.isoformat()} | Último arranque registrado: {last_run_str}")
                    return "inactive"
            else:
                # Con licencia guardada siempre debería existir last_run (save_license lo
                # escribe). Su ausencia deja la detección de retroceso de reloj sin ancla:
                # registrarlo como anomalía en vez de saltarla en silencio.
                logger.warning("SEGURIDAD: no existe marca 'last_run' en Keyring; la detección de retroceso de reloj queda sin referencia hasta el próximo registro.")

            # 2. ¿Licencia expirada? (con periodo de gracia para renovaciones tardías)
            if now > exp_date:
                if now <= exp_date + timedelta(days=LicenseManager.GRACE_DAYS):
                    logger.warning(f"Licencia vencida el {exp_date_str}: operando en periodo de gracia de {LicenseManager.GRACE_DAYS} días.")
                    return "grace"
                logger.warning(f"La licencia de prueba/suscripción ha expirado el {exp_date_str} (gracia agotada).")
                return "inactive"

            return "active"
        except Exception as e:
            logger.error(f"Error al verificar el estado de la licencia en Keyring: {str(e)}")
            return "inactive"

    @staticmethod
    def is_license_active() -> bool:
        """Compatibilidad: True si la licencia permite operar (vigente o en gracia)."""
        return LicenseManager.get_license_state() in ("active", "grace")

    @staticmethod
    def save_license(license_base64: str, payload: dict) -> bool:
        """Almacena la clave de licencia y datos en la bóveda de credenciales."""
        try:
            keyring.set_password(LicenseManager.SERVICE_NAME, "license_key", license_base64)
            keyring.set_password(LicenseManager.SERVICE_NAME, "expiration_date", payload["expires"])
            keyring.set_password(LicenseManager.SERVICE_NAME, "last_run", datetime.now(timezone.utc).isoformat())
            logger.info("Licencia guardada y activada exitosamente en Keyring.")
            return True
        except Exception as e:
            logger.error(f"No se pudo guardar la licencia en Keyring: {str(e)}")
            return False

    @staticmethod
    def update_last_run():
        """Actualiza la marca del último arranque exitoso para mantener consistencia horaria.

        Monotónica: nunca retrocede. Si el reloj actual está por detrás de la marca
        guardada, sobrescribirla "lavaría" un retroceso de reloj y anularía la detección.
        """
        try:
            now = datetime.now(timezone.utc)
            stored = keyring.get_password(LicenseManager.SERVICE_NAME, "last_run")
            if stored:
                try:
                    if now < LicenseManager._parse_iso_datetime(stored):
                        logger.warning("last_run no actualizado: el reloj actual está por detrás de la marca guardada (posible retroceso de reloj).")
                        return
                except Exception:
                    pass  # Marca ilegible: se sobrescribe con la actual
            keyring.set_password(LicenseManager.SERVICE_NAME, "last_run", now.isoformat())
        except Exception as e:
            logger.warning(f"No se pudo actualizar last_run en Keyring: {str(e)}")
