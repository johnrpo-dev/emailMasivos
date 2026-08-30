"""Pruebas del soporte de varias llaves publicas confiables.

Permite que una rotacion de llaves no invalide las licencias ya entregadas y
todavia vigentes: la aplicacion acepta tanto las firmadas con la llave nueva
como con la anterior, mientras esta se conserve en la lista.
"""
import unittest
from unittest.mock import patch
import base64
import json

from cryptography.hazmat.primitives.asymmetric import ed25519

from src.core.license_manager import LicenseManager


def _hex_publica(priv):
    from cryptography.hazmat.primitives import serialization
    return priv.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    ).hex()


def _firmar(priv, email="cliente@ejemplo.com", expires="2027-01-01T23:59:59+00:00"):
    payload = {"email": email, "expires": expires}
    firma = priv.sign(json.dumps(payload, sort_keys=True).encode("utf-8")).hex()
    return base64.b64encode(
        json.dumps({"payload": payload, "signature": firma}).encode("utf-8")
    ).decode("utf-8")


class TestVariasLlavesConfiables(unittest.TestCase):
    def setUp(self):
        self.llave_nueva = ed25519.Ed25519PrivateKey.generate()
        self.llave_vieja = ed25519.Ed25519PrivateKey.generate()
        self.ajena = ed25519.Ed25519PrivateKey.generate()

    def test_valida_con_la_llave_activa(self):
        with patch.object(LicenseManager, "PUBLIC_KEYS_HEX",
                          [_hex_publica(self.llave_nueva)]):
            self.assertIsNotNone(LicenseManager.verify_signature(_firmar(self.llave_nueva)))

    def test_valida_con_una_llave_retirada_que_sigue_en_la_lista(self):
        """El caso que evita reinstalar en el cliente tras una rotacion."""
        with patch.object(LicenseManager, "PUBLIC_KEYS_HEX",
                          [_hex_publica(self.llave_nueva), _hex_publica(self.llave_vieja)]):
            self.assertIsNotNone(LicenseManager.verify_signature(_firmar(self.llave_vieja)))
            self.assertIsNotNone(LicenseManager.verify_signature(_firmar(self.llave_nueva)))

    def test_rechaza_una_llave_ajena(self):
        with patch.object(LicenseManager, "PUBLIC_KEYS_HEX",
                          [_hex_publica(self.llave_nueva), _hex_publica(self.llave_vieja)]):
            self.assertIsNone(LicenseManager.verify_signature(_firmar(self.ajena)))

    def test_rechaza_cuando_se_retira_la_llave_de_la_lista(self):
        """Al sacar una llave, sus licencias dejan de validar."""
        with patch.object(LicenseManager, "PUBLIC_KEYS_HEX",
                          [_hex_publica(self.llave_nueva)]):
            self.assertIsNone(LicenseManager.verify_signature(_firmar(self.llave_vieja)))

    def test_ignora_marcadores_pendientes(self):
        """Un marcador de llave sin definir no debe romper la verificacion."""
        with patch.object(LicenseManager, "PUBLIC_KEYS_HEX",
                          ["PENDIENTE_NUEVA_LLAVE", _hex_publica(self.llave_vieja)]):
            self.assertIsNotNone(LicenseManager.verify_signature(_firmar(self.llave_vieja)))

    def test_payload_alterado_no_valida(self):
        with patch.object(LicenseManager, "PUBLIC_KEYS_HEX",
                          [_hex_publica(self.llave_nueva)]):
            token = _firmar(self.llave_nueva)
            datos = json.loads(base64.b64decode(token))
            datos["payload"]["expires"] = "2099-12-31T23:59:59+00:00"
            alterado = base64.b64encode(json.dumps(datos).encode()).decode()
            self.assertIsNone(LicenseManager.verify_signature(alterado))


if __name__ == "__main__":
    unittest.main()
