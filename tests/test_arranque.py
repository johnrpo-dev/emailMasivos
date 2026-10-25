"""Arranque de la aplicación y apertura de la vista previa (hallazgo 7 y menor
de la auditoría funcional)."""
import unittest
from unittest.mock import patch, MagicMock

import src.main as arranque
from src.ui.modals.preview_modal import PreviewModal


@patch("src.main.App")
@patch("src.main.LicenseManager")
@patch("src.main._verificar_boveda_credenciales", return_value=(True, "prueba"))
class TestAvisoDePeriodoDeGracia(unittest.TestCase):
    """Hallazgo 7: tras la activación, el aviso de gracia crea una ventana nueva;
    la caché de fuentes debe limpiarse antes, o las fuentes apuntarían a una
    ventana ya destruida."""

    def _arrancar(self, mock_licencia, estado):
        mock_licencia.is_license_active.return_value = True
        mock_licencia.get_license_state.return_value = estado
        mock_licencia.GRACE_DAYS = 7
        orden = MagicMock()
        with patch("src.ui.theme.reset_font_cache") as limpiar_fuentes, \
             patch("customtkinter.CTk") as ventana, \
             patch("customtkinter.set_appearance_mode"), \
             patch("src.ui.dialogs.show_warning"):
            orden.attach_mock(limpiar_fuentes, "reset_font_cache")
            orden.attach_mock(ventana, "CTk")
            arranque.main()
        return [llamada[0] for llamada in orden.mock_calls]

    def test_limpia_fuentes_antes_de_crear_la_ventana(self, _boveda, mock_licencia, _app):
        llamadas = self._arrancar(mock_licencia, "grace")

        self.assertIn("reset_font_cache", llamadas)
        self.assertIn("CTk", llamadas)
        self.assertLess(llamadas.index("reset_font_cache"), llamadas.index("CTk"))

    def test_licencia_vigente_no_crea_ventana_temporal(self, _boveda, mock_licencia, _app):
        llamadas = self._arrancar(mock_licencia, "active")

        self.assertNotIn("CTk", llamadas)


@patch("src.ui.modals.preview_modal.dialogs")
@patch("src.ui.modals.preview_modal.DataManager")
class TestVistaPreviaValidaAntesDeAbrir(unittest.TestCase):
    """Menor: con un CSV ilegible o vacío solo se muestra el aviso, sin abrir
    antes una ventana vacía."""

    def test_csv_ilegible_no_crea_ventana(self, mock_datos, mock_dialogs):
        mock_datos.load_csv.side_effect = ValueError("archivo dañado")

        with patch("customtkinter.CTkToplevel.__init__") as crear_ventana:
            PreviewModal(MagicMock(), "pacientes.csv")

        mock_dialogs.show_error.assert_called_once()
        crear_ventana.assert_not_called()

    def test_csv_vacio_no_crea_ventana(self, mock_datos, mock_dialogs):
        mock_datos.load_csv.return_value = []

        with patch("customtkinter.CTkToplevel.__init__") as crear_ventana:
            PreviewModal(MagicMock(), "pacientes.csv")

        mock_dialogs.show_warning.assert_called_once()
        crear_ventana.assert_not_called()


if __name__ == "__main__":
    unittest.main()
