"""Cierre de un envío en WorkflowController: mensajes finales correctos y
liberación del candado (menores de la auditoría funcional)."""
import unittest
from unittest.mock import patch, MagicMock

from src.ui.controllers.workflow_controller import WorkflowController


class FakeApp:
    """Doble de App: ejecuta en el acto lo que la UI programaría con after()."""
    def __init__(self):
        self.session_batches = []
        self._hmac_key = b"clave_de_prueba_hmac_32_bytes___"
        self.home_panel = MagicMock()
        self.csv_path = MagicMock()
        self.pdf_dir = MagicMock()

    def after(self, _ms, fn):
        fn()

    def state(self):
        return "normal"


@patch("src.ui.controllers.workflow_controller.LicenseManager")
@patch("src.ui.controllers.workflow_controller.WorkflowOrchestrator")
@patch("src.ui.controllers.workflow_controller.dialogs")
class TestCierreDelEnvio(unittest.TestCase):

    def _completar(self, mock_orquestador, *resultado):
        """Lanza un envío simulado y entrega el resultado indicado al cierre."""
        app = FakeApp()
        ctrl = WorkflowController(app)
        ctrl.show_results_modal = MagicMock()
        ctrl._workflow_active = True
        ctrl.execute_workflow()
        on_complete = mock_orquestador.return_value.start.call_args.kwargs["on_complete"]
        on_complete(*resultado)
        return app, ctrl

    def test_fallo_grave_no_muestra_exitosos_negativos(self, _dialogs, mock_orq, _licencia):
        app, _ = self._completar(mock_orq, ["Error fatal: disco lleno"], 0, [], {}, {})

        linea = app.home_panel.add_console_log.call_args[0][0]
        self.assertIn("0 exitosos", linea)
        self.assertNotIn("-1", linea)

    def test_csv_vacio_avisa_en_vez_de_reportar_exito(self, mock_dialogs, mock_orq, _licencia):
        self._completar(mock_orq, [], 0, [], {}, {})

        mock_dialogs.show_warning.assert_called_once()
        self.assertEqual(mock_dialogs.show_warning.call_args[0][1], "Sin registros")
        mock_dialogs.show_success.assert_not_called()

    def test_envio_sin_errores_reporta_exito(self, mock_dialogs, mock_orq, _licencia):
        self._completar(mock_orq, [], 5, [], {}, {})

        mock_dialogs.show_success.assert_called_once()
        mock_dialogs.show_warning.assert_not_called()

    def test_al_terminar_se_libera_el_candado(self, _dialogs, mock_orq, _licencia):
        app, ctrl = self._completar(mock_orq, [], 5, [], {}, {})

        self.assertFalse(ctrl.is_busy())
        app.home_panel.set_busy.assert_called_with(False)


if __name__ == "__main__":
    unittest.main()
