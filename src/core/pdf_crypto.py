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
                raise FileNotFoundError(f"El archivo PDF no existe: {os.path.basename(input_path)}")
            
            with open(input_path, 'rb') as f:
                header = f.read(4)
            if header != b'%PDF':
                raise ValueError(f'El archivo no es un PDF válido: {os.path.basename(input_path)}')
            
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
                
            # Seguridad: No registrar rutas absolutas que puedan contener PII
            logger.info(f"PDF cifrado exitosamente: {os.path.basename(output_path)}")
            return output_path
            
        except Exception as e:
            logger.error(f"Error al cifrar PDF {os.path.basename(input_path)}: {str(e)}")
            raise
            
    @staticmethod
    def secure_cleanup(file_path: str):
        """Elimina el archivo temporal de forma segura (overwrite + delete).
        
        Aplica un try-finally robusto para asegurar que, incluso si la fase de
        sobreescritura anti-forense falla, el archivo físico sea removido.
        """
        if not file_path or not os.path.exists(file_path):
            return
            
        basename = os.path.basename(file_path)
        try:
            # 1. Fase de Sobreescritura anti-forense (Uso de modo de escritura binario "r+b")
            try:
                file_size = os.path.getsize(file_path)
                if file_size > 0:
                    with open(file_path, "r+b") as f:
                        f.seek(0)
                        f.write(os.urandom(file_size))
                        f.flush()
                        os.fsync(f.fileno())  # Forzar vaciado de buffers al disco físico
            except Exception as e:
                logger.warning(f"Fase de sobreescritura fallida para {basename}: {str(e)}")
                
        finally:
            # 2. Fase de Eliminación Física (Garantizada mediante bloque finally)
            try:
                os.remove(file_path)
                logger.info(f"Archivo temporal eliminado de forma segura: {basename}")
            except Exception as e:
                logger.error(f"Fallo crítico: No se pudo eliminar físicamente el temporal {basename}: {str(e)}")
