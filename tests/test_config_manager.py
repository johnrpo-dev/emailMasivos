"""Pruebas de ConfigManager: independencia del Keyring frente a config.json
corrupto y preservación de la contraseña con el placeholder de la UI."""
import unittest
from unittest.mock import patch
import json
import os
import tempfile

from src.config.config_manager import ConfigManager


class TestGetConfigResiliente(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8")
        self.addCleanup(lambda: os.path.exists(self.tmp.name) and os.remove(self.tmp.name))

    def _with_config_file(self, content: str):
        self.tmp.write(content)
        self.tmp.close()
        return patch.object(ConfigManager, "_resolve_config_file", return_value=self.tmp.name)

    @patch("src.config.config_manager.keyring")
    def test_json_corrupto_no_oculta_credenciales_del_keyring(self, mock_keyring):
        """Un config.json ilegible no debe impedir recuperar las credenciales SMTP."""
        mock_keyring.get_password.return_value = json.dumps(
            {"user": "lab@clinica.com", "password": "secreta123"}
        )
        with self._with_config_file("{esto no es json válido"):
            config = ConfigManager.get_config()

        self.assertEqual(config["smtp_user"], "lab@clinica.com")
        self.assertEqual(config["smtp_password"], "secreta123")
        # El resto de claves cae a defaults
        self.assertEqual(config["smtp_host"], "smtp.gmail.com")

    @patch("src.config.config_manager.keyring")
    def test_json_valido_combina_con_keyring(self, mock_keyring):
        mock_keyring.get_password.return_value = json.dumps(
            {"user": "lab@clinica.com", "password": "secreta123"}
        )
        with self._with_config_file(json.dumps({"send_delay": 5, "sender_name": "Lab"})):
            config = ConfigManager.get_config()

        self.assertEqual(config["send_delay"], 5)
        self.assertEqual(config["sender_name"], "Lab")
        self.assertEqual(config["smtp_password"], "secreta123")

    @patch("src.config.config_manager.keyring")
    def test_keyring_caido_marca_bandera(self, mock_keyring):
        mock_keyring.get_password.side_effect = RuntimeError("bóveda inaccesible")
        with self._with_config_file(json.dumps({})):
            config = ConfigManager.get_config()

        self.assertEqual(config["smtp_password"], "")
        self.assertTrue(config.get("keyring_failed"))


class TestSaveConfigPlaceholder(unittest.TestCase):
    @patch("src.config.config_manager.keyring")
    def test_placeholder_preserva_contrasena_anterior(self, mock_keyring):
        """Guardar con '••••••••' debe conservar la contraseña real del Keyring."""
        mock_keyring.get_password.return_value = json.dumps(
            {"user": "lab@clinica.com", "password": "la_real"}
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.object(ConfigManager, "CONFIG_DIR", tmpdir), \
                 patch.object(ConfigManager, "CONFIG_FILE", os.path.join(tmpdir, "config.json")):
                ok = ConfigManager.save_config(
                    "lab@clinica.com", "••••••••", "smtp.gmail.com", "587",
                    "Asunto", "Cuerpo"
                )

        self.assertTrue(ok)
        args = mock_keyring.set_password.call_args[0]
        saved = json.loads(args[2])
        self.assertEqual(saved["password"], "la_real")


if __name__ == "__main__":
    unittest.main()
