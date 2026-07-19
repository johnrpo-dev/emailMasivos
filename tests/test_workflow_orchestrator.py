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

    @patch('src.core.workflow_orchestrator.EmailService')
    def test_fuzzy_pdf_matching(self, mock_email_service_class):
        """Verifica que si un archivo PDF no existe, se busque uno similar en disco y se sugiera."""
        mock_service = MagicMock()
        mock_email_service_class.return_value = mock_service

        # Fila con archivo PDF que tiene un error de tipeo menor
        record = {
            "email": "test@gmail.com",
            "id_archivo": "factura_123.pdf",
            "id_servicio": "SER-003",
            "cedula": "123456"
        }

        # Mockear os.listdir para simular que en el disco existe factura-123.pdf
        mock_files = ["factura-123.pdf", "factura_456.pdf"]
        
        pdf_corrections = {}

        with patch('os.path.isdir', return_value=True):
            with patch('os.listdir', return_value=mock_files):
                with patch('os.path.exists', return_value=False):
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
                        send_delay=0,
                        pdf_corrections=pdf_corrections
                    )

        # Comprobar que se sugirió el archivo similar en el mensaje de error
        self.assertEqual(len(self.errores), 1)
        self.assertIn("Sugerencia: factura-123.pdf", self.errores[0])
        # La sugerencia NO debe auto-aplicarse a pdf_corrections (riesgo de privacidad NEW-001)
        self.assertEqual(len(pdf_corrections), 0)
        self.assertEqual(len(self.records_fallidos), 1)

    def test_email_corrections_keyed_by_real_email(self):
        """C-01: las correcciones se indexan por email REAL. Dos correos distintos cuya
        máscara colisiona (j***z@gmial.com) deben producir dos entradas independientes."""
        records = [
            {"email": "juan.perez@gmial.com", "id_archivo": "a.pdf", "id_servicio": "S1", "cedula": "111111"},
            {"email": "jose.gomez@gmial.com", "id_archivo": "b.pdf", "id_servicio": "S2", "cedula": "222222"},
        ]
        email_corrections = {}
        validos = self.orchestrator._pre_validate_emails(
            records, self.hmac_key, self.batch_record, self.errores,
            self.records_fallidos, email_corrections, None, None, None
        )
        self.assertEqual(validos, [])
        self.assertEqual(len(email_corrections), 2)
        self.assertEqual(email_corrections.get("juan.perez@gmial.com"), "juan.perez@gmail.com")
        self.assertEqual(email_corrections.get("jose.gomez@gmial.com"), "jose.gomez@gmail.com")

    @patch('src.core.workflow_orchestrator.EmailService')
    def test_registro_incompleto_cuenta_como_fallo_reintentable(self, mock_email_service_class):
        """A-04: una fila con datos obligatorios vacíos debe entrar en errores y en
        records_fallidos (conteo honesto de éxitos + posibilidad de reintento)."""
        mock_email_service_class.return_value = MagicMock()
        record = {"email": "test@gmail.com", "id_archivo": "", "id_servicio": "S", "cedula": ""}
        self.orchestrator._process_chunk_worker(
            chunk_records=[record], worker_id=0, pdf_dir=self.pdf_dir, hmac_key=self.hmac_key,
            subject_template="S {id_servicio}", batch_record=self.batch_record,
            errores=self.errores, records_fallidos=self.records_fallidos,
            on_progress=None, on_stats_update=None, on_log=None, lock=self.lock,
            completed_count=self.completed_count, success_count=self.success_count,
            failed_count=self.failed_count, total_validos=1, send_delay=0
        )
        self.assertEqual(len(self.errores), 1)
        self.assertIn("incompletos", self.errores[0])
        self.assertEqual(len(self.records_fallidos), 1)
        self.assertEqual(self.failed_count[0], 1)


if __name__ == '__main__':
    unittest.main()
