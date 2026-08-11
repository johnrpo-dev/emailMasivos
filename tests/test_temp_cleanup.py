"""Pruebas de limpieza del directorio temporal por registro.

El PDF cifrado del paciente se escribe en un directorio temporal propio; ese
directorio no debe sobrevivir al envío ni siquiera cuando el borrado seguro del
archivo falla (os.rmdir aborta con directorios no vacíos y el documento quedaría
en %TEMP%).
"""
import unittest
from unittest.mock import patch, MagicMock
import os
import shutil
import tempfile
import threading

from src.core.workflow_orchestrator import WorkflowOrchestrator


class TestLimpiezaDirectorioTemporal(unittest.TestCase):

    def setUp(self):
        self.orchestrator = WorkflowOrchestrator()
        self.hmac_key = b"clave_de_prueba_hmac_32_bytes___"
        self.lock = threading.Lock()
        self.batch_record = {"envios": []}
        self.errores = []
        self.records_fallidos = []
        self.completed_count = [0]
        self.success_count = [0]
        self.failed_count = [0]
        self.temp_dirs_creados = []

        # Directorio de PDFs de entrada con un archivo real
        self.pdf_dir = tempfile.mkdtemp(prefix="sems_test_input_")
        self.addCleanup(shutil.rmtree, self.pdf_dir, True)
        with open(os.path.join(self.pdf_dir, "doc.pdf"), "wb") as f:
            f.write(b"%PDF-1.4 contenido de prueba")

        self.record = {
            "email": "paciente@gmail.com",
            "id_archivo": "doc.pdf",
            "id_servicio": "LAB-001",
            "cedula": "12345678",
        }

    def _ejecutar_envio(self, secure_cleanup_side_effect):
        """Ejecuta un envío completo capturando el directorio temporal creado."""
        real_mkdtemp = tempfile.mkdtemp

        def spy_mkdtemp(*args, **kwargs):
            ruta = real_mkdtemp(*args, **kwargs)
            if kwargs.get("prefix", "").startswith("sems_batch_"):
                self.temp_dirs_creados.append(ruta)
            return ruta

        with patch("tempfile.mkdtemp", side_effect=spy_mkdtemp), \
             patch("src.core.workflow_orchestrator.PDFCrypto") as mock_crypto:
            # El cifrado deja un archivo real en el temporal (el residuo potencial)
            def fake_encrypt(input_path, output_path, password):
                with open(output_path, "wb") as f:
                    f.write(b"PDF-CIFRADO-AES256")
                return output_path

            mock_crypto.encrypt_pdf.side_effect = fake_encrypt
            mock_crypto.secure_cleanup.side_effect = secure_cleanup_side_effect

            self.orchestrator._process_single_record(
                record=self.record,
                worker_id=0,
                email_service=MagicMock(),
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
                pdf_corrections={},
                pwd_prefix="",
                pwd_suffix="",
                throttle=None,
            )

        self.assertEqual(len(self.temp_dirs_creados), 1, "Se esperaba un único directorio temporal")
        return self.temp_dirs_creados[0]

    def test_caso_normal_elimina_directorio(self):
        """Con el borrado seguro funcionando, no queda ni archivo ni directorio."""
        temp_dir = self._ejecutar_envio(lambda ruta: os.remove(ruta))

        self.assertFalse(os.path.exists(temp_dir),
                         "El directorio temporal debió eliminarse tras el envío")
        self.assertEqual(self.success_count[0], 1)

    def test_residuo_no_sobrevive_si_falla_el_borrado_seguro(self):
        """Si el borrado seguro no puede eliminar el PDF cifrado, el directorio
        NO debe quedar en %TEMP% con el documento del paciente dentro."""
        temp_dir = self._ejecutar_envio(lambda ruta: None)  # no elimina nada

        self.assertFalse(os.path.exists(temp_dir),
                         "El temporal con el PDF cifrado quedó en %TEMP% (fuga de datos)")


if __name__ == "__main__":
    unittest.main()
