"""Pruebas del candado de concurrencia y de la purga de fallidos recuperados
en WorkflowController (consistencia del historial en RAM y anti-duplicados)."""
import unittest
from unittest.mock import patch, MagicMock
import hashlib
import hmac as hmac_mod

from src.ui.controllers.workflow_controller import WorkflowController


class FakeApp:
    """Doble mínimo de App: solo lo que consume WorkflowController en estas rutas."""
    def __init__(self):
        self.session_batches = []
        self._hmac_key = b"clave_de_prueba_hmac_32_bytes___"

    def compute_search_hash(self, value: str) -> str:
        return hmac_mod.new(self._hmac_key, value.encode(), hashlib.sha256).hexdigest()


def _envio(app, cedula, servicio, estado, detalles=None):
    return {
        "email": "x***x@dominio.com",
        "email_hash": "irrelevante",
        "id_archivo": "doc.pdf",
        "id_servicio": servicio,
        "cedula": f"***{cedula[-3:]}",
        "cedula_hash": app.compute_search_hash(cedula.strip()),
        "estado": estado,
        "detalles": detalles,
    }


class TestPurgeRecoveredFailures(unittest.TestCase):
    def setUp(self):
        self.app = FakeApp()
        self.controller = WorkflowController(self.app)

    def test_registro_recuperado_se_purga_y_marca(self):
        """Un fallido entregado con éxito en un lote posterior se purga del lote viejo,
        su envío se marca 'recuperado' y las correcciones aplicadas se podan."""
        record = {"email": "mal@gmial.com", "cedula": "123456", "id_servicio": "SRV-1", "id_archivo": "a.pdf"}
        lote_viejo = {
            "csv_nombre": "lote1.csv",
            "envios": [_envio(self.app, "123456", "SRV-1", "error", "Typo en dominio")],
            "raw_records_fallidos": [record],
            "raw_email_corrections": {"mal@gmial.com": "mal@gmail.com"},
            "raw_pdf_corrections": {},
        }
        lote_nuevo = {
            "csv_nombre": "Reintento: lote1.csv",
            "envios": [_envio(self.app, "123456", "SRV-1", "exito")],
            "raw_records_fallidos": [],
        }
        self.app.session_batches = [lote_viejo, lote_nuevo]

        self.controller._purge_recovered_failures()

        self.assertEqual(lote_viejo["raw_records_fallidos"], [])
        self.assertEqual(lote_viejo["envios"][0]["estado"], "recuperado")
        self.assertIn("reintento posterior", lote_viejo["envios"][0]["detalles"])
        self.assertEqual(lote_viejo["recuperados"], 1)
        self.assertEqual(lote_viejo["raw_email_corrections"], {})

    def test_claves_duplicadas_no_se_purgan(self):
        """M-04: dos fallidos distintos con la misma (cedula, id_servicio) no se purgan
        aunque uno de ellos figure como entregado — evita suprimir un pendiente legítimo."""
        rec_a = {"email": "a@x.com", "cedula": "999888", "id_servicio": "SRV-9", "id_archivo": "a.pdf"}
        rec_b = {"email": "b@x.com", "cedula": "999888", "id_servicio": "SRV-9", "id_archivo": "b.pdf"}
        lote_viejo = {
            "csv_nombre": "lote1.csv",
            "envios": [
                _envio(self.app, "999888", "SRV-9", "error"),
                _envio(self.app, "999888", "SRV-9", "error"),
            ],
            "raw_records_fallidos": [rec_a, rec_b],
        }
        lote_nuevo = {
            "csv_nombre": "Reintento: lote1.csv",
            "envios": [_envio(self.app, "999888", "SRV-9", "exito")],
        }
        self.app.session_batches = [lote_viejo, lote_nuevo]

        self.controller._purge_recovered_failures()

        self.assertEqual(len(lote_viejo["raw_records_fallidos"]), 2)
        self.assertNotIn("recuperados", lote_viejo)

    def test_sin_exitos_no_toca_nada(self):
        record = {"email": "a@x.com", "cedula": "111222", "id_servicio": "S", "id_archivo": "a.pdf"}
        lote = {
            "csv_nombre": "lote1.csv",
            "envios": [_envio(self.app, "111222", "S", "error")],
            "raw_records_fallidos": [record],
        }
        self.app.session_batches = [lote]

        self.controller._purge_recovered_failures()

        self.assertEqual(lote["raw_records_fallidos"], [record])
        self.assertEqual(lote["envios"][0]["estado"], "error")


class TestWorkflowLock(unittest.TestCase):
    """El candado _workflow_active debe impedir workflows concurrentes."""

    def setUp(self):
        self.app = FakeApp()
        self.controller = WorkflowController(self.app)

    @patch("src.ui.controllers.workflow_controller.dialogs")
    def test_retry_batch_bloqueado_si_hay_proceso_activo(self, mock_dialogs):
        self.controller._workflow_active = True
        self.controller._sync_records_with_current_csv = MagicMock()
        self.controller.execute_workflow = MagicMock()

        self.controller.retry_batch([{"email": "a@x.com"}])

        mock_dialogs.show_warning.assert_called_once()
        self.controller._sync_records_with_current_csv.assert_not_called()
        self.controller.execute_workflow.assert_not_called()

    @patch("src.ui.controllers.workflow_controller.dialogs")
    def test_start_process_bloqueado_si_hay_proceso_activo(self, mock_dialogs):
        self.controller._workflow_active = True
        self.controller.execute_workflow = MagicMock()

        self.controller.start_process()

        mock_dialogs.show_warning.assert_called_once()
        self.controller.execute_workflow.assert_not_called()

    @patch("src.ui.controllers.workflow_controller.dialogs")
    def test_retorno_temprano_no_consume_reintento(self, mock_dialogs):
        """El chequeo del límite no debe gastar intentos en retornos tempranos."""
        self.controller._retry_count = 0
        self.controller._workflow_active = True
        self.controller.retry_batch([{"email": "a@x.com"}])
        self.assertEqual(self.controller._retry_count, 0)


if __name__ == "__main__":
    unittest.main()
