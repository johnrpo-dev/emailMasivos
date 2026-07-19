import unittest
import os
import tempfile
from src.core.data_manager import DataManager


class TestDataManagerRowLimit(unittest.TestCase):
    """Pruebas del límite de filas del CSV: debe abortar, nunca truncar en silencio (C-02)."""

    def _write_csv(self, rows: int) -> str:
        fd, path = tempfile.mkstemp(suffix=".csv")
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write("email,id_archivo,id_servicio,cedula\n")
            for i in range(rows):
                f.write(f"user{i}@test.com,doc{i}.pdf,SRV-{i},100000{i}\n")
        return path

    def test_csv_dentro_del_limite_carga_completo(self):
        path = self._write_csv(50)
        try:
            records = DataManager.load_csv(path)
            self.assertEqual(len(records), 50)
        finally:
            os.remove(path)

    def test_csv_sobre_el_limite_aborta_sin_truncar(self):
        """Un CSV que excede MAX_ROWS debe lanzar ValueError, no procesar un subconjunto."""
        original = DataManager.MAX_ROWS
        DataManager.MAX_ROWS = 100  # límite reducido para agilizar la prueba
        path = self._write_csv(101)
        try:
            with self.assertRaises(ValueError) as ctx:
                DataManager.load_csv(path)
            self.assertIn("supera el límite", str(ctx.exception))
        finally:
            DataManager.MAX_ROWS = original
            os.remove(path)


if __name__ == '__main__':
    unittest.main()
