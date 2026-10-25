"""Enmascarado de datos personales en registros (hallazgo 6 y menor de
mask_email de la auditoría funcional)."""
import unittest

from src.utils.logger import mask_email, mask_filename


class TestMaskFilename(unittest.TestCase):
    def test_conserva_extension_y_oculta_el_nombre(self):
        self.assertEqual(mask_filename("juan_perez_123.pdf"), "ju***23.pdf")

    def test_usa_solo_el_nombre_base_de_una_ruta(self):
        enmascarado = mask_filename(r"C:\Pacientes\juan_perez_123.pdf")
        self.assertEqual(enmascarado, "ju***23.pdf")
        self.assertNotIn("Pacientes", enmascarado)

    def test_nombre_corto(self):
        self.assertEqual(mask_filename("abc.pdf"), "a***.pdf")

    def test_sin_extension(self):
        self.assertEqual(mask_filename("informe_medico"), "in***co")

    def test_vacio_se_devuelve_igual(self):
        self.assertEqual(mask_filename(""), "")
        self.assertIsNone(mask_filename(None))


class TestMaskEmail(unittest.TestCase):
    def test_correo_valido(self):
        self.assertEqual(mask_email("juan.perez@gmail.com"), "j***z@gmail.com")

    def test_texto_sin_arroba_tambien_se_enmascara(self):
        """Antes se devolvía intacto y el texto tecleado llegaba completo al registro."""
        self.assertEqual(mask_email("juanperez"), "j***z")
        self.assertEqual(mask_email("ab"), "a***")

    def test_vacio_se_devuelve_igual(self):
        self.assertEqual(mask_email(""), "")
        self.assertIsNone(mask_email(None))


if __name__ == "__main__":
    unittest.main()
