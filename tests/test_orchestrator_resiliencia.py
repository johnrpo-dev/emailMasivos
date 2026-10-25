"""Resiliencia del orquestador ante fallos de hilos y fuente única de contadores
(hallazgos B y 2 de la auditoría funcional), y enmascarado de nombres de PDF en
el registro persistente (hallazgo 6)."""
import shutil
import tempfile
import threading
import unittest
from unittest.mock import patch, MagicMock

from src.core.workflow_orchestrator import WorkflowOrchestrator


def _registro(i):
    return {
        "email": f"paciente{i}@gmail.com",
        "id_archivo": f"resultado_{i}.pdf",
        "id_servicio": f"LAB-{i}",
        "cedula": f"1000000{i}",
    }


class _BaseOrquestador(unittest.TestCase):
    def setUp(self):
        self.orch = WorkflowOrchestrator()
        self.hmac_key = b"clave_de_prueba_hmac_32_bytes___"
        self.pdf_dir = tempfile.mkdtemp(prefix="sems_test_pdfs_")
        self.addCleanup(shutil.rmtree, self.pdf_dir, True)
        self.batch_record = {"envios": []}
        self.errores = []
        self.records_fallidos = []
        self.completed_count = [0]
        self.success_count = [0]
        self.failed_count = [0]
        self.lock = threading.Lock()

    def _procesar_lote(self, registros):
        self.orch._process_chunk_worker(
            chunk_records=registros, worker_id=0, pdf_dir=self.pdf_dir,
            hmac_key=self.hmac_key, subject_template="Resultado {id_servicio}",
            batch_record=self.batch_record, errores=self.errores,
            records_fallidos=self.records_fallidos, on_progress=None,
            on_stats_update=None, on_log=None, lock=self.lock,
            completed_count=self.completed_count, success_count=self.success_count,
            failed_count=self.failed_count, total_validos=len(registros), send_delay=0,
        )


class TestHiloCaido(_BaseOrquestador):
    """Hallazgo B: los registros de un hilo que falla quedan como fallidos
    reintentables, nunca contados como enviados."""

    @patch("src.core.workflow_orchestrator.EmailService")
    def test_sin_conexion_smtp_todos_quedan_fallidos(self, mock_servicio):
        mock_servicio.return_value.connect.side_effect = ConnectionError("smtp caido")
        registros = [_registro(i) for i in range(3)]

        self._procesar_lote(registros)

        self.assertEqual(self.records_fallidos, registros)
        self.assertEqual(len(self.errores), 3)
        self.assertEqual(self.failed_count[0], 3)
        self.assertEqual(self.completed_count[0], 3)
        self.assertEqual(self.success_count[0], 0)
        self.assertEqual([e["estado"] for e in self.batch_record["envios"]], ["error"] * 3)

    @patch("src.core.workflow_orchestrator.ConfigManager")
    @patch("src.core.workflow_orchestrator.EmailService")
    def test_fallo_a_mitad_del_lote_registra_el_actual_y_los_restantes(self, _servicio, mock_config):
        mock_config.get_config.return_value = {}
        registros = [_registro(i) for i in range(3)]

        # El primer registro se procesa bien; el segundo revienta el hilo
        with patch.object(self.orch, "_process_single_record",
                          side_effect=[None, RuntimeError("fallo inesperado")]):
            self._procesar_lote(registros)

        self.assertEqual(self.records_fallidos, registros[1:])
        self.assertEqual(len(self.errores), 2)
        self.assertEqual(self.failed_count[0], 2)
        self.assertNotIn(registros[0], self.records_fallidos)


class TestContadoresDelLote(_BaseOrquestador):
    """Hallazgo 2: el lote toma éxitos y fallos de los contadores reales de los
    hilos, no de 'total - errores', que divergía del monitor en vivo."""

    @patch("src.core.workflow_orchestrator.ConfigManager")
    def test_el_lote_usa_los_contadores_reales(self, mock_config):
        mock_config.get_config.return_value = {"email_subject": "Resultado", "send_delay": 0}
        registros = [_registro(i) for i in range(2)]
        capturado = {}

        def despacho_simulado(*args):
            errores = args[5]
            # Dos entradas de error que no corresponden una a una con registros:
            # con la fórmula anterior el lote habría reportado 0 éxitos.
            errores.extend(["error del hilo", "detalle adicional"])
            return 1, 1

        with patch.object(self.orch, "_dispatch_workers", side_effect=despacho_simulado):
            self.orch._run_workflow(
                "pacientes.csv", self.pdf_dir, hmac_key=self.hmac_key,
                on_batch_added=lambda lote: capturado.setdefault("lote", lote),
                records_to_process=registros,
            )

        self.assertEqual(capturado["lote"]["exitosos"], 1)
        self.assertEqual(capturado["lote"]["fallidos"], 1)


class TestEnmascaradoEnRegistro(_BaseOrquestador):
    """Hallazgo 6: el nombre del PDF, que suele llevar el nombre del paciente,
    no queda completo en el registro persistente."""

    @patch("src.core.workflow_orchestrator.logger")
    def test_pdf_faltante_se_registra_enmascarado(self, mock_logger):
        registro = _registro(1)
        registro["id_archivo"] = "juan_perez_resultado.pdf"

        self.orch._process_single_record(
            record=registro, worker_id=0, email_service=MagicMock(),
            pdf_dir=self.pdf_dir, hmac_key=self.hmac_key,
            subject_template="Resultado", batch_record=self.batch_record,
            errores=self.errores, records_fallidos=self.records_fallidos,
            on_progress=None, on_stats_update=None, on_log=None, lock=self.lock,
            completed_count=self.completed_count, success_count=self.success_count,
            failed_count=self.failed_count, total_validos=1, send_delay=0,
            pdf_corrections={}, pwd_prefix="", pwd_suffix="",
        )

        mensajes = " ".join(str(c.args[0]) for c in mock_logger.error.call_args_list)
        self.assertIn("ju***do.pdf", mensajes)
        self.assertNotIn("juan_perez", mensajes)


if __name__ == "__main__":
    unittest.main()
