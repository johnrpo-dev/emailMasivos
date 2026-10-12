"""Pruebas de la marca monotónica last_run del LicenseManager
(ancla de la detección de retroceso de reloj)."""
import unittest
from unittest.mock import patch
from datetime import datetime, timedelta, timezone

from src.core.license_manager import LicenseManager


class TestUpdateLastRunMonotonico(unittest.TestCase):
    @patch("src.core.license_manager.keyring")
    def test_no_retrocede_si_el_reloj_esta_atras(self, mock_keyring):
        """Si la marca guardada es futura respecto al reloj actual (retroceso),
        NO debe sobrescribirse: hacerlo 'lavaría' la evidencia del retroceso."""
        futuro = (datetime.now(timezone.utc) + timedelta(hours=6)).isoformat()
        mock_keyring.get_password.return_value = futuro

        LicenseManager.update_last_run()

        mock_keyring.set_password.assert_not_called()

    @patch("src.core.license_manager.keyring")
    def test_avanza_normalmente(self, mock_keyring):
        pasado = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
        mock_keyring.get_password.return_value = pasado

        LicenseManager.update_last_run()

        mock_keyring.set_password.assert_called_once()

    @patch("src.core.license_manager.keyring")
    def test_sin_marca_previa_escribe(self, mock_keyring):
        mock_keyring.get_password.return_value = None

        LicenseManager.update_last_run()

        mock_keyring.set_password.assert_called_once()

    @patch("src.core.license_manager.keyring")
    def test_marca_ilegible_se_sobrescribe(self, mock_keyring):
        mock_keyring.get_password.return_value = "no-es-una-fecha"

        LicenseManager.update_last_run()

        mock_keyring.set_password.assert_called_once()


class TestLicenciaPerpetua(unittest.TestCase):
    """La licencia perpetua (vence 2099) nunca debe dejar al cliente sin servicio."""

    def _estado(self, expires, last_run):
        valores = {"license_key": "token", "expiration_date": expires, "last_run": last_run}
        with patch("src.core.license_manager.keyring") as mock_keyring, \
             patch.object(LicenseManager, "verify_signature", return_value={"expires": expires}):
            mock_keyring.get_password.side_effect = lambda _servicio, campo: valores.get(campo)
            return LicenseManager.get_license_state()

    def test_perpetua_esta_activa(self):
        ahora = datetime.now(timezone.utc).isoformat()
        self.assertEqual(self._estado("2099-12-31T23:59:59+00:00", ahora), "active")

    def test_perpetua_ignora_retroceso_de_reloj(self):
        """Un reloj atrasado no debe bloquear una licencia que no vence."""
        futuro = (datetime.now(timezone.utc) + timedelta(days=3)).isoformat()
        self.assertEqual(self._estado("2099-12-31T23:59:59+00:00", futuro), "active")

    def test_mensual_sigue_detectando_retroceso_de_reloj(self):
        futuro = (datetime.now(timezone.utc) + timedelta(days=3)).isoformat()
        vence = (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()
        self.assertEqual(self._estado(vence, futuro), "inactive")


if __name__ == "__main__":
    unittest.main()
