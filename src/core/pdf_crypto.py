import pikepdf
import os
import secrets
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
            
            # Owner password aleatoria (el usuario final nunca la ve)
            owner_pw = secrets.token_hex(16)
            
            with pikepdf.open(input_path) as pdf:
                # Utilizamos cifrado AES-256 (PDF 2.0 / R6)
                enc = pikepdf.Encryption(
                    owner=owner_pw,
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
        """Elimina el archivo temporal de forma segura (overwrite + delete)."""
        try:
            if os.path.exists(file_path):
                # Sobrescribir con datos aleatorios antes de eliminar (anti-forense)
                with open(file_path, "ba+") as f:
                    length = f.tell()
                    f.seek(0)
                    f.write(os.urandom(length))
                os.remove(file_path)
                logger.info(f"Archivo temporal eliminado de forma segura: {file_path}")
        except Exception as e:
            logger.warning(f"No se pudo eliminar el archivo temporal {file_path}: {str(e)}")
