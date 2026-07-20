"""Pruebas de la validación de TLD en proveedores conocidos
(antes 'gmail.con' se aceptaba como válido sin chequeo alguno)."""
import unittest
from unittest.mock import patch

from src.utils.email_validator import validate_email


class TestTLDProveedoresConocidos(unittest.TestCase):
    def test_tld_typo_con_detectado_con_sugerencia(self):
        result = validate_email("usuario@gmail.con")
        self.assertFalse(result.is_valid)
        self.assertEqual(result.error_type, "typo_dominio")
        self.assertEqual(result.suggestion, "usuario@gmail.com")

    def test_tld_typo_cmo_detectado(self):
        result = validate_email("usuario@hotmail.cmo")
        self.assertFalse(result.is_valid)
        self.assertEqual(result.suggestion, "usuario@hotmail.com")

    def test_tlds_legitimos_validos(self):
        for email in ("a@gmail.com", "b@hotmail.es", "c@outlook.com.co", "d@yahoo.com.mx"):
            with self.subTest(email=email):
                self.assertTrue(validate_email(email).is_valid)

    @patch("src.utils.email_validator._domain_has_mail_server", return_value=False)
    def test_tld_raro_sin_dns_es_invalido(self, _mock_dns):
        result = validate_email("usuario@gmail.zzz")
        self.assertFalse(result.is_valid)
        self.assertEqual(result.error_type, "dominio_inexistente")

    @patch("src.utils.email_validator._domain_has_mail_server", return_value=True)
    def test_tld_raro_con_dns_se_acepta(self, _mock_dns):
        self.assertTrue(validate_email("usuario@gmail.zzz").is_valid)

    @patch("src.utils.email_validator._domain_has_mail_server", return_value=True)
    def test_dominios_cortos_reales_ya_no_se_marcan_como_typo(self, _mock_dns):
        """'ive.com'/'zho.com' son dominios corporativos plausibles: no deben
        bloquearse como typos de live/zoho."""
        for email in ("contacto@ive.com", "info@zho.com", "a@mns.com"):
            with self.subTest(email=email):
                self.assertTrue(validate_email(email).is_valid)

    def test_typo_de_nombre_sigue_detectandose(self):
        result = validate_email("usuario@gmial.com")
        self.assertFalse(result.is_valid)
        self.assertEqual(result.error_type, "typo_dominio")
        self.assertEqual(result.suggestion, "usuario@gmail.com")


if __name__ == "__main__":
    unittest.main()
