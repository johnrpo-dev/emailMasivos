import unittest
from unittest.mock import patch, MagicMock
import socket
from src.utils.email_validator import validate_email, validate_emails_batch, EmailValidationResult

class TestEmailValidator(unittest.TestCase):
    """Pruebas unitarias para validar la lógica del validador de correos electrónicos."""

    def test_format_validation_valid(self):
        """Verifica que los formatos de email válidos sean reconocidos correctamente."""
        valid_emails = [
            "test@gmail.com",
            "user.name+tag@yahoo.co.uk",
            "admin@empresa.com.co",
            "first.last@outlook.com",
            "a@b.cl"
        ]
        for email in valid_emails:
            with self.subTest(email=email):
                result = validate_email(email)
                # Si el dominio es corporativo (ej: empresa.com.co), podría resolver por DNS
                # o mockeamos la resolución para asegurar que siempre sea True en pruebas aisladas.
                with patch('src.utils.email_validator._domain_has_mail_server', return_value=True):
                    result = validate_email(email)
                    self.assertTrue(result.is_valid, f"El correo {email} debería ser válido.")

    def test_format_validation_invalid(self):
        """Verifica que los formatos de email inválidos sean rechazados."""
        invalid_emails = [
            "plainaddress",
            "#@%^%#$@#$@#.com",
            "@domain.com",
            "Joe Smith <email@domain.com>",
            "email.domain.com",
            "email@domain@domain.com",
            "email@domain.c"
        ]
        for email in invalid_emails:
            with self.subTest(email=email):
                result = validate_email(email)
                self.assertFalse(result.is_valid, f"El correo {email} debería ser inválido por formato.")
                self.assertEqual(result.error_type, "formato")

    def test_domain_typos_detection(self):
        """Verifica que los typos comunes en dominios de proveedores conocidos sean corregidos."""
        typo_cases = [
            ("user@gmial.com", "user@gmail.com"),
            ("test@hotmial.es", "test@hotmail.es"),
            ("info@outloock.com.co", "info@outlook.com.co"),
            ("admin@yaho.co", "admin@yahoo.co"),
            ("contact@iclould.com", "contact@icloud.com"),
            ("dev@protonmall.ch", "dev@protonmail.ch"),
            ("hello@zhoo.com", "hello@zoho.com")
        ]
        for input_email, expected_suggestion in typo_cases:
            with self.subTest(input_email=input_email):
                result = validate_email(input_email)
                self.assertFalse(result.is_valid)
                self.assertEqual(result.error_type, "typo_dominio")
                self.assertEqual(result.suggestion, expected_suggestion)
                self.assertIn("Posible typo en dominio", result.message)

    @patch('src.utils.email_validator._resolve_domain_with_timeout')
    def test_dns_validation_valid_domain(self, mock_resolve):
        """Verifica que dominios desconocidos válidos pasen la comprobación DNS (mockeada)."""
        mock_resolve.return_value = True
        result = validate_email("user@corporativo-valido.com")
        self.assertTrue(result.is_valid)

    @patch('src.utils.email_validator._resolve_domain_with_timeout')
    def test_dns_validation_invalid_domain(self, mock_resolve):
        """Verifica que dominios que no existen sean rechazados (mockeado)."""
        # Simulamos que socket.gaierror es levantado por el resolvedor DNS (Host no encontrado / 11001)
        mock_resolve.side_effect = socket.gaierror(11001, "getaddrinfo failed")
        
        result = validate_email("user@dominio-inexistente-fake.com")
        self.assertFalse(result.is_valid)
        self.assertEqual(result.error_type, "dominio_inexistente")
        self.assertIn("no existe o no es alcanzable", result.message)

    @patch('src.utils.email_validator._resolve_domain_with_timeout')
    def test_dns_validation_timeout_graceful(self, mock_resolve):
        """Verifica que si la consulta DNS expira (timeout), el dominio se asuma válido por usabilidad."""
        mock_resolve.side_effect = TimeoutError("DNS query timed out")
        
        result = validate_email("user@dns-lento.com")
        # Por diseño defensivo del validador, si hay timeout se asume válido para no bloquear envíos legítimos
        self.assertTrue(result.is_valid)

    def test_batch_validation(self):
        """Verifica que la validación en lote agrupe correctamente los válidos y los inválidos."""
        batch_list = ["valid@gmail.com", "invalid@gmial.com"]
        batch_results = validate_emails_batch(batch_list)
        
        self.assertEqual(len(batch_results["valid"]), 1)
        self.assertEqual(batch_results["valid"][0].email, "valid@gmail.com")
        self.assertEqual(len(batch_results["invalid"]), 1)
        self.assertEqual(batch_results["invalid"][0].email, "invalid@gmial.com")

if __name__ == '__main__':
    unittest.main()
