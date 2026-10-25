"""Saneamiento de cabeceras del correo (menor de la auditoría funcional):
un destinatario con saltos de línea no debe inyectar cabeceras nuevas."""
import os
import tempfile
import unittest
from unittest.mock import patch, MagicMock

from src.core.email_service import EmailService


class TestCabecerasSaneadas(unittest.TestCase):
    def setUp(self):
        fd, self.pdf = tempfile.mkstemp(suffix=".pdf")
        os.write(fd, b"%PDF-1.4 prueba")
        os.close(fd)
        self.addCleanup(os.remove, self.pdf)

    @patch("src.core.email_service.ConfigManager")
    def test_destinatario_con_salto_de_linea_no_inyecta_cabeceras(self, mock_config):
        mock_config.get_config.return_value = {
            "smtp_user": "laboratorio@gmail.com",
            "sender_name": "Laboratorio",
            "email_body": "Adjunto su resultado.",
            "logo_path": "",
        }
        servicio = EmailService()
        servicio.server = MagicMock()

        servicio.send_email_with_attachment(
            "paciente@gmail.com\r\nBcc: atacante@dominio.com", "Resultado", self.pdf)

        mensaje = servicio.server.send_message.call_args[0][0]
        self.assertNotIn("\r", mensaje["To"])
        self.assertNotIn("\n", mensaje["To"])
        self.assertIsNone(mensaje["Bcc"])


if __name__ == "__main__":
    unittest.main()
