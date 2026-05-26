import unittest
from unittest.mock import patch, MagicMock
import os
import re
import threading
from src.core.workflow_orchestrator import WorkflowOrchestrator

class TestWorkflowOrchestrator(unittest.TestCase):
    """Pruebas unitarias para validar la sanitización de rutas y prevención de Path Traversal en WorkflowOrchestrator."""

    def setUp(self):
        self.orchestrator = WorkflowOrchestrator()
        self.hmac_key = b"test_secret_key_32_bytes_long_12345"
        self.pdf_dir = os.path.realpath(os.path.join(os.getcwd(), "data", "input"))
        
        # Estructura base para capturar el estado del procesamiento
        self.batch_record = {"envios": []}
        self.errores = []
        self.records_fallidos = []
        self.completed_count = [0]
        self.success_count = [0]
        self.failed_count = [0]
        self.lock = threading.Lock()

    @patch('src.core.workflow_orchestrator.EmailService')
    def test_filename_sanitization(self, mock_email_service_class):
        """Verifica que los nombres de archivo se carbonicen y limpien de caracteres no seguros."""
        # Mock del servicio de correo para evitar conexiones SMTP reales
        mock_service = MagicMock()
        mock_email_service_class.return_value = mock_service

        # Fila con nombre de archivo lleno de caracteres especiales
        dirty_filename = "doc<>|:?*#1.xyz"
        expected_sanitized = "doc_______1.xyz.pdf"
        
        record = {
            "email": "test@gmail.com",
            "id_archivo": dirty_filename,
            "id_servicio": "SER-001",
            "cedula": "123456"
        }

        # Mockear os.path.exists para que devuelva True para la ruta esperada de entrada
        expected_input_pdf = os.path.join(self.pdf_dir, expected_sanitized)
        
        # Mockear PDFCrypto.encrypt_pdf y os.path.exists
        with patch('os.path.exists', lambda path: os.path.realpath(path) == os.path.realpath(expected_input_pdf) or path.endswith("temp")):
            with patch('src.core.workflow_orchestrator.PDFCrypto') as mock_crypto:
                mock_crypto.encrypt_pdf.return_value = "fake_temp.pdf"
                
                # Ejecutar trabajador con el registro dirty
                self.orchestrator._process_chunk_worker(
                    chunk_records=[record],
                    worker_id=0,
                    pdf_dir=self.pdf_dir,
                    hmac_key=self.hmac_key,
                    subject_template="Servicio {id_servicio}",
                    batch_record=self.batch_record,
                    errores=self.errores,
                    records_fallidos=self.records_fallidos,
                    on_progress=None,
                    on_stats_update=None,
                    on_log=None,
                    lock=self.lock,
                    completed_count=self.completed_count,
                    success_count=self.success_count,
                    failed_count=self.failed_count,
                    total_validos=1,
                    send_delay=0
                )

        # Verificar que el servicio de correo fue invocado con el nombre sanitizado
        mock_service.send_email_with_attachment.assert_called_once()
        args, kwargs = mock_service.send_email_with_attachment.call_args
        self.assertEqual(kwargs.get('filename_override'), expected_sanitized)

    @patch('src.core.workflow_orchestrator.EmailService')
    def test_path_traversal_prevention(self, mock_email_service_class):
        """Verifica que intentos de inyección de rutas (Path Traversal) sean bloqueados y registrados."""
        # Evitar conexiones
        mock_service = MagicMock()
        mock_email_service_class.return_value = mock_service

        # Intentos de path traversal
        traversal_attempts = [
            "../../etc/passwd",
            "..\\..\\Windows\\System32\\cmd.exe",
            "subfolder/../../../sensitive_doc.pdf",
            "/absolute/private/path.pdf"
        ]

        for attempt in traversal_attempts:
            with self.subTest(attempt=attempt):
                record = {
                    "email": "victim@gmail.com",
                    "id_archivo": attempt,
                    "id_servicio": "SER-002",
                    "cedula": "789012"
                }

                # Reiniciar variables
                self.batch_record = {"envios": []}
                self.errores = []
                self.records_fallidos = []
                self.completed_count = [0]
                self.failed_count = [0]

                # Ejecutar trabajador con os.path.basename y re.sub mockeados para eludir las primeras defensas y probar el segundo filtro de seguridad de realpath (defensa en profundidad)
                with patch('os.path.basename', side_effect=lambda x: x):
                    with patch('re.sub', side_effect=lambda pattern, repl, string: string):
                        self.orchestrator._process_chunk_worker(
                            chunk_records=[record],
                            worker_id=0,
                            pdf_dir=self.pdf_dir,
                            hmac_key=self.hmac_key,
                            subject_template="Servicio {id_servicio}",
                            batch_record=self.batch_record,
                            errores=self.errores,
                            records_fallidos=self.records_fallidos,
                            on_progress=None,
                            on_stats_update=None,
                            on_log=None,
                            lock=self.lock,
                            completed_count=self.completed_count,
                            success_count=self.success_count,
                            failed_count=self.failed_count,
                            total_validos=1,
                            send_delay=0
                        )

                # Comprobar que fue bloqueado y registrado en la bitácora
                self.assertEqual(len(self.errores), 1)
                self.assertIn("Ruta de archivo sospechosa activa bloqueada", self.errores[0])
                self.assertEqual(len(self.records_fallidos), 1)
                
                # Comprobar que no se envió ningún correo
                mock_service.send_email_with_attachment.assert_not_called()
                
                # Comprobar que se marcó como error de seguridad en el historial efímero
                self.assertEqual(len(self.batch_record["envios"]), 1)
                self.assertEqual(self.batch_record["envios"][0]["estado"], "error")
                self.assertIn("sospechosa", self.batch_record["envios"][0]["detalles"])

if __name__ == '__main__':
    unittest.main()
