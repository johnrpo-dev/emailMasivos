import pandas as pd
from typing import List, Dict, Any
from src.utils.logger import logger
import os

class DataManager:
    """Clase para gestionar la lectura y validación de los datos del CSV."""
    
    REQUIRED_COLUMNS = ["email", "id_archivo", "id_servicio", "cedula"]
    MAX_FILE_SIZE_MB = 50   # Límite de tamaño del archivo CSV
    MAX_ROWS = 10000        # Límite de filas para prevenir DoS por archivos enormes
    
    @staticmethod
    def load_csv(file_path: str) -> List[Dict[str, Any]]:
        """
        Carga el archivo CSV y retorna una lista de diccionarios.
        Valida que existan las columnas requeridas.
        
        Seguridad: Limita tamaño de archivo y número de filas para prevenir
        agotamiento de memoria (DoS local).
        """
        try:
            # Validar tamaño del archivo antes de cargarlo en memoria
            file_size = os.path.getsize(file_path)
            max_bytes = DataManager.MAX_FILE_SIZE_MB * 1024 * 1024
            if file_size > max_bytes:
                raise ValueError(f"El archivo CSV excede el límite de {DataManager.MAX_FILE_SIZE_MB}MB ({file_size / (1024*1024):.1f}MB detectados)")
            
            df = pd.read_csv(file_path, dtype=str, nrows=DataManager.MAX_ROWS)
            
            # Limpiar nombres de columnas (espacios extras)
            df.columns = df.columns.str.strip()
            
            # Verificar columnas requeridas
            missing_cols = [col for col in DataManager.REQUIRED_COLUMNS if col not in df.columns]
            if missing_cols:
                raise ValueError(f"El archivo CSV no contiene las columnas requeridas: {', '.join(missing_cols)}")
            
            # Rellenar nulos con string vacío para evitar errores posteriores
            df = df.fillna("")
            
            # Convertir a lista de diccionarios
            records = df.to_dict('records')
            logger.info(f"CSV cargado exitosamente. {len(records)} registros encontrados.")
            return records
            
        except Exception as e:
            logger.error(f"Error al cargar el CSV: {str(e)}")
            raise e
