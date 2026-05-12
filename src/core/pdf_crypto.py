import pikepdf
import os
from src.utils.logger import logger

class PDFCrypto:
    """Clase para manejar el cifrado de archivos PDF de forma segura."""
    
    @staticmethod
    def encrypt_pdf(input_path: str, output_path: str, password: str) -> str:
        """
        Aplica cifrado AES-256 al PDF utilizando la contraseña proporcionada.
        Retorna la ruta del archivo temporal cifrado.
        """
        try:
            if not os.path.exists(input_path):
                raise FileNotFoundError(f"El archivo PDF no existe: {input_path}")
            
            with pikepdf.open(input_path) as pdf:
                # Utilizamos cifrado AES-256 (PDF 2.0 / R6)
                enc = pikepdf.Encryption(
                    owner=password,
                    user=password,
                    allow=pikepdf.Permissions(extract=False, print_lowres=True, print_highres=True)
                )
                pdf.save(output_path, encryption=enc)
                
            logger.info(f"PDF cifrado exitosamente: {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"Error al cifrar el PDF {input_path}: {str(e)}")
            raise e
            
    @staticmethod
    def secure_cleanup(file_path: str):
        """Elimina el archivo temporal generado."""
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                logger.info(f"Archivo temporal eliminado: {file_path}")
        except Exception as e:
            logger.warning(f"No se pudo eliminar el archivo temporal {file_path}: {str(e)}")
