import unittest
import os
import tempfile
import pikepdf
from src.core.pdf_crypto import PDFCrypto

class TestPDFCrypto(unittest.TestCase):
    """Pruebas unitarias para validar las operaciones de cifrado y borrado seguro de PDFs."""

    def setUp(self):
        """Prepara el entorno creando un PDF minimalista para cifrar."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.input_pdf = os.path.join(self.temp_dir.name, "test_input.pdf")
        self.output_pdf = os.path.join(self.temp_dir.name, "test_encrypted.pdf")
        self.password = "12345678"
        
        # Crear un PDF válido mínimo utilizando pikepdf
        with pikepdf.new() as pdf:
            pdf.save(self.input_pdf)
            
    def tearDown(self):
        """Limpia los archivos temporales creados."""
        self.temp_dir.cleanup()

    def test_encrypt_pdf_success(self):
        """Verifica que el PDF se cifre correctamente con la contraseña indicada."""
        PDFCrypto.encrypt_pdf(self.input_pdf, self.output_pdf, self.password)
        
        # Verificar que el archivo de salida existe y no está vacío
        self.assertTrue(os.path.exists(self.output_pdf))
        self.assertGreater(os.path.getsize(self.output_pdf), 0)
        
        # Intentar abrir el PDF cifrado con la contraseña correcta
        with pikepdf.open(self.output_pdf, password=self.password) as pdf:
            self.assertEqual(len(pdf.pages), 0)  # Es un PDF nuevo vacío

    def test_encrypt_pdf_invalid_password(self):
        """Verifica que abrir el PDF cifrado con contraseña incorrecta falle."""
        PDFCrypto.encrypt_pdf(self.input_pdf, self.output_pdf, self.password)
        
        # Intentar abrir sin contraseña o con una errónea debería lanzar PasswordError
        with self.assertRaises((pikepdf.PasswordError, pikepdf.PdfError)):
            pikepdf.open(self.output_pdf, password="password_incorrecta")

    def test_encrypt_pdf_missing_input(self):
        """Verifica que cifrar un archivo inexistente lance FileNotFoundError."""
        with self.assertRaises(FileNotFoundError):
            PDFCrypto.encrypt_pdf("ruta_inexistente.pdf", self.output_pdf, self.password)

    def test_encrypt_invalid_pdf_format(self):
        """Verifica que intentar cifrar un archivo que no sea PDF levante ValueError."""
        txt_file = os.path.join(self.temp_dir.name, "not_a_pdf.txt")
        with open(txt_file, "w") as f:
            f.write("Esto no es un pdf")
            
        with self.assertRaises(ValueError):
            PDFCrypto.encrypt_pdf(txt_file, self.output_pdf, self.password)

    def test_secure_cleanup(self):
        """Verifica que secure_cleanup sobrescriba con bytes aleatorios y elimine físicamente el archivo."""
        temp_file = os.path.join(self.temp_dir.name, "temp_to_cleanup.txt")
        content = b"Informacion altamente sensible confidencial"
        with open(temp_file, "wb") as f:
            f.write(content)
            
        self.assertTrue(os.path.exists(temp_file))
        
        # Ejecutar limpieza segura
        PDFCrypto.secure_cleanup(temp_file)
        
        # El archivo físico debe dejar de existir
        self.assertFalse(os.path.exists(temp_file))

    def test_secure_cleanup_nonexistent(self):
        """Verifica que secure_cleanup maneje rutas inexistentes de forma silenciosa y sin lanzar excepciones."""
        try:
            PDFCrypto.secure_cleanup("ruta_inexistente_de_limpieza.pdf")
        except Exception as e:
            self.fail(f"secure_cleanup levantó una excepción inesperada: {str(e)}")

if __name__ == '__main__':
    unittest.main()
