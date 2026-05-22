import sqlite3
import os
import threading
import hashlib
from datetime import datetime
from src.utils.logger import logger

class HistoryManager:
    """Clase para gestionar el almacenamiento persistente de envíos y lotes en SQLite.
    
    Seguridad:
    - Escrituras protegidas con threading.Lock para concurrencia segura.
    - WAL mode habilitado para máximo rendimiento con múltiples hilos.
    - PII protegida: emails enmascarados, cédulas hasheadas con SHA-256.
    """
    
    # Define DB_PATH robustly using the project root directory
    _ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    DB_PATH = os.path.join(_ROOT_DIR, "data", "history.db")
    _write_lock = threading.RLock()  # Serializar escrituras concurrentes de forma reentrante

    @staticmethod
    def _get_connection():
        # Asegurar que el directorio de datos existe
        os.makedirs(os.path.dirname(HistoryManager.DB_PATH), exist_ok=True)
        conn = sqlite3.connect(HistoryManager.DB_PATH, timeout=30)
        conn.row_factory = sqlite3.Row
        # WAL mode permite lecturas concurrentes y serializa escrituras sin bloqueo
        conn.execute("PRAGMA journal_mode=WAL")
        # Esperar hasta 5 segundos antes de lanzar 'database is locked'
        conn.execute("PRAGMA busy_timeout=5000")
        return conn

    @staticmethod
    def _mask_email_for_storage(email: str) -> str:
        """Enmascara un email antes de almacenarlo en la base de datos (protección PII)."""
        if not email or "@" not in email:
            return email
        name, domain = email.split("@", 1)
        if len(name) <= 2:
            return name[0] + "***@" + domain
        return name[0] + "***" + name[-1] + "@" + domain

    @staticmethod
    def _hash_cedula(cedula: str) -> str:
        """Hash SHA-256 truncado de la cédula. Nunca almacenar la cédula en texto plano,
        ya que es la misma contraseña utilizada para cifrar los PDFs."""
        if not cedula:
            return ""
        return hashlib.sha256(cedula.encode('utf-8')).hexdigest()[:16]

    @classmethod
    def initialize_db(cls):
        """Inicializa la base de datos y crea las tablas si no existen."""
        with cls._write_lock:
            try:
                conn = cls._get_connection()
                cursor = conn.cursor()
                
                # Tabla de Lotes (Cabecera de cada envío masivo)
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS lotes (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        fecha TEXT NOT NULL,
                        total_registros INTEGER NOT NULL,
                        exitosos INTEGER NOT NULL,
                        fallidos INTEGER NOT NULL,
                        csv_nombre TEXT
                    )
                """)
                
                # Tabla de Envíos Individuales
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS envios (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        lote_id INTEGER,
                        fecha TEXT NOT NULL,
                        email TEXT NOT NULL,
                        id_archivo TEXT NOT NULL,
                        id_servicio TEXT,
                        cedula TEXT,
                        estado TEXT NOT NULL, -- 'exito' o 'error'
                        detalles TEXT, -- Descripción detallada del error si aplica
                        FOREIGN KEY (lote_id) REFERENCES lotes(id) ON DELETE CASCADE
                    )
                """)
                
                conn.commit()
                conn.close()
                logger.info("Base de datos de historial inicializada correctamente.")
            except Exception as e:
                logger.error(f"Error al inicializar la base de datos de historial: {str(e)}")

    @classmethod
    def add_lote(cls, total_registros: int, exitosos: int, fallidos: int, csv_nombre: str) -> int:
        """Crea un nuevo registro de lote y retorna su id."""
        with cls._write_lock:
            try:
                cls.initialize_db()
                conn = cls._get_connection()
                cursor = conn.cursor()
                fecha_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                csv_basename = os.path.basename(csv_nombre) if csv_nombre else "Desconocido"
                
                cursor.execute("""
                    INSERT INTO lotes (fecha, total_registros, exitosos, fallidos, csv_nombre)
                    VALUES (?, ?, ?, ?, ?)
                """, (fecha_str, total_registros, exitosos, fallidos, csv_basename))
                
                lote_id = cursor.lastrowid
                conn.commit()
                conn.close()
                logger.info(f"Lote #{lote_id} creado en el historial ({total_registros} registros).")
                return lote_id
            except Exception as e:
                logger.error(f"Error al registrar lote en el historial: {str(e)}")
                return -1

    @classmethod
    def update_lote_stats(cls, lote_id: int, exitosos: int, fallidos: int):
        """Actualiza los contadores de éxito y fallo de un lote específico."""
        if lote_id == -1:
            return
        with cls._write_lock:
            try:
                conn = cls._get_connection()
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE lotes
                    SET exitosos = ?, fallidos = ?
                    WHERE id = ?
                """, (exitosos, fallidos, lote_id))
                conn.commit()
                conn.close()
                logger.info(f"Lote #{lote_id} actualizado con exitosos={exitosos}, fallidos={fallidos}.")
            except Exception as e:
                logger.error(f"Error al actualizar estadísticas del lote #{lote_id}: {str(e)}")

    @classmethod
    def add_envio(cls, lote_id: int, email: str, id_archivo: str, id_servicio: str, cedula: str, estado: str, detalles: str = None):
        """Registra el envío de un correo individual.
        
        Seguridad: El email se enmascara y la cédula se hashea antes de almacenarse.
        La cédula NUNCA se guarda en texto plano, ya que es la contraseña del PDF.
        """
        with cls._write_lock:
            try:
                conn = cls._get_connection()
                cursor = conn.cursor()
                fecha_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                
                # Si lote_id es -1 (error al crear lote), guardamos NULL
                l_id = None if lote_id == -1 else lote_id
                
                # Proteger PII antes de almacenar
                email_masked = cls._mask_email_for_storage(email)
                cedula_hash = cls._hash_cedula(cedula)
                
                cursor.execute("""
                    INSERT INTO envios (lote_id, fecha, email, id_archivo, id_servicio, cedula, estado, detalles)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (l_id, fecha_str, email_masked, id_archivo, id_servicio, cedula_hash, estado, detalles))
                
                conn.commit()
                conn.close()
            except Exception as e:
                logger.error(f"Error al registrar envío individual en el historial: {str(e)}")

    @classmethod
    def get_lotes(cls) -> list:
        """Obtiene la lista de todos los lotes en orden descendente."""
        try:
            cls.initialize_db()
            conn = cls._get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM lotes ORDER BY id DESC")
            rows = cursor.fetchall()
            lotes = [dict(row) for row in rows]
            conn.close()
            return lotes
        except Exception as e:
            logger.error(f"Error al obtener lotes del historial: {str(e)}")
            return []

    @classmethod
    def get_envios_by_lote(cls, lote_id: int) -> list:
        """Obtiene todos los registros de envío correspondientes a un lote."""
        try:
            cls.initialize_db()
            conn = cls._get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM envios WHERE lote_id = ? ORDER BY id ASC", (lote_id,))
            rows = cursor.fetchall()
            envios = [dict(row) for row in rows]
            conn.close()
            return envios
        except Exception as e:
            logger.error(f"Error al obtener envíos del lote #{lote_id}: {str(e)}")
            return []

    @classmethod
    def search_envios(cls, query: str) -> list:
        """Busca envíos en toda la base de datos que coincidan con el término de búsqueda."""
        try:
            cls.initialize_db()
            conn = cls._get_connection()
            cursor = conn.cursor()
            q = f"%{query}%"
            cursor.execute("""
                SELECT e.*, l.csv_nombre
                FROM envios e
                LEFT JOIN lotes l ON e.lote_id = l.id
                WHERE e.email LIKE ? OR e.id_archivo LIKE ? OR e.id_servicio LIKE ? OR e.cedula LIKE ?
                ORDER BY e.id DESC
                LIMIT 200
            """, (q, q, q, q))
            rows = cursor.fetchall()
            envios = [dict(row) for row in rows]
            conn.close()
            return envios
        except Exception as e:
            logger.error(f"Error al buscar en el historial: {str(e)}")
            return []
