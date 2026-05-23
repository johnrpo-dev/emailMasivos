import os
import re
import tempfile
import threading
import hashlib
import hmac
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
from src.core.data_manager import DataManager
from src.core.pdf_crypto import PDFCrypto
from src.core.email_service import EmailService
from src.config.config_manager import ConfigManager
from src.utils.logger import logger, mask_email
from src.utils.email_validator import validate_email

class WorkflowOrchestrator:
    """Orquestador desacoplado de lógica de negocio y concurrencia.
    
    Aplica el principio de Responsabilidad Única (SRP) de SOLID, separando por completo
    el procesamiento masivo de la capa de interfaz de usuario de CustomTkinter.
    """
    
    def __init__(self):
        self._retry_count = 0
        self.MAX_RETRIES = 2

    def start(self, csv_path: str, pdf_dir: str,
              hmac_key: bytes = None,
              on_batch_added=None,
              on_log=None,
              on_progress=None,
              on_stats_update=None,
              on_complete=None,
              records_to_process=None) -> threading.Thread:
        """Inicia el procesamiento del flujo de envíos masivos en un hilo secundario."""
        thread = threading.Thread(
            target=self._run_workflow,
            args=(csv_path, pdf_dir),
            kwargs={
                "hmac_key": hmac_key,
                "on_batch_added": on_batch_added,
                "on_log": on_log,
                "on_progress": on_progress,
                "on_stats_update": on_stats_update,
                "on_complete": on_complete,
                "records_to_process": records_to_process
            },
            daemon=True
        )
        thread.start()
        return thread

    def _run_workflow(self, csv_path: str, pdf_dir: str,
                      hmac_key: bytes = None,
                      on_batch_added=None,
                      on_log=None,
                      on_progress=None,
                      on_stats_update=None,
                      on_complete=None,
                      records_to_process=None):
        """Método de ejecución principal decomopuesto para cumplir con SRP."""
        try:
            # 1. Cargar registros (de CSV o de un reintento previo)
            if records_to_process is None:
                records = DataManager.load_csv(csv_path)
            else:
                records = records_to_process
            
            total = len(records)
            if on_stats_update:
                on_stats_update(total=total, success=0, failed=0)
            if on_log:
                on_log(f"Cargados {total} registros para procesar.")
            
            # 2. Registrar el Lote de envíos en RAM (formato efímero y enmascarado)
            csv_name = os.path.basename(csv_path) if records_to_process is None else f"Reintento: {os.path.basename(csv_path)}"
            batch_record = {
                "fecha": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "total_registros": total,
                "exitosos": 0,
                "fallidos": 0,
                "csv_nombre": csv_name,
                "envios": []
            }
            if on_batch_added:
                on_batch_added(batch_record)
            
            # Obtener subject dinámico de la configuración actual antes de enviar
            config = ConfigManager.get_config()
            subject_template = config.get("email_subject", "Documento de {id_servicio}")
            
            errores = []
            records_fallidos = []
            email_corrections = {}
            
            # === FASE 1: Validación previa de emails (Sin conectar a SMTP aún) ===
            records_validos = self._pre_validate_emails(
                records, hmac_key, batch_record, errores, 
                records_fallidos, email_corrections, 
                on_stats_update, on_log, on_progress
            )
            
            # Si ningún correo es válido, se aborta y se notifica el fin del lote
            if not records_validos:
                if on_progress:
                    on_progress("Validación completada. Sin correos válidos.", 1.0)
                if on_log:
                    on_log("✗ PROCESO COMPLETADO: 0 correos válidos procesados.")
                batch_record["exitosos"] = 0
                batch_record["fallidos"] = len(errores)
                if on_complete:
                    on_complete(errores, total, records_fallidos, email_corrections)
                return
            
            # === FASE 2: Envío de correos válidos en Paralelo ===
            self._dispatch_workers(
                records_validos, pdf_dir, hmac_key, subject_template, 
                batch_record, errores, records_fallidos, email_corrections,
                len(records) - len(records_validos),
                on_progress, on_stats_update, on_log
            )
            
            # Consolidar totales del lote procesado
            exitosos_total = total - len(errores)
            batch_record["exitosos"] = exitosos_total
            batch_record["fallidos"] = len(errores)
            
            if on_progress:
                on_progress("¡Proceso masivo completado!", 1.0)
            if on_complete:
                on_complete(errores, total, records_fallidos, email_corrections)
                
        except Exception as e:
            logger.critical(f"Fallo fatal en el orquestador: {str(e)}")
            if on_log:
                on_log(f"✗ FALLO CRÍTICO: {str(e)}")
            if on_progress:
                on_progress("Error fatal en procesamiento.", 1.0)
            if on_complete:
                on_complete([f"Error fatal: {str(e)}"], 0, [], {})

    def _hash_pii(self, value: str, hmac_key: bytes) -> str:
        """Helper para hash seguro HMAC-SHA256 de PII."""
        if not value or not hmac_key:
            return ""
        return hmac.new(hmac_key, value.encode(), hashlib.sha256).hexdigest()

    def _pre_validate_emails(self, records, hmac_key, batch_record, errores, 
                             records_fallidos, email_corrections, 
                             on_stats_update, on_log, on_progress):
        """Fase 1: Pre-validación sintáctica, de typos y de servidores MX."""
        if on_progress:
            on_progress("Validando correos electrónicos...", 0.0)
        if on_log:
            on_log("Iniciando validación de destinatarios...")
            
        records_validos = []
        valid_failed_count = 0
        
        for record in records:
            email = str(record.get("email", "")).strip()
            id_archivo = str(record.get("id_archivo", "")).strip()
            id_servicio = str(record.get("id_servicio", "")).strip()
            cedula = str(record.get("cedula", "")).strip()
            
            if not email:
                valid_failed_count += 1
                if on_stats_update:
                    on_stats_update(failed=valid_failed_count)
                if on_log:
                    on_log("⚠ OMITIDO: Fila sin correo electrónico.")
                continue
            
            validation = validate_email(email)
            if not validation.is_valid:
                valid_failed_count += 1
                if on_stats_update:
                    on_stats_update(failed=valid_failed_count)
                
                msg = f"{email}: {validation.message}"
                if validation.suggestion:
                    msg += f" (Sugerencia: {validation.suggestion})"
                    email_corrections[email] = validation.suggestion
                errores.append(msg)
                records_fallidos.append(record)
                logger.warning(f"Email rechazado pre-envío: {validation.message}")
                if on_log:
                    on_log(f"✗ RECHAZADO: {mask_email(email)} ({validation.message})")
                
                # Registrar en historial efímero enmascarado
                batch_record["envios"].append({
                    "email": mask_email(email),
                    "email_hash": self._hash_pii(email.strip().lower(), hmac_key),
                    "id_archivo": id_archivo,
                    "id_servicio": id_servicio,
                    "cedula": f"***{cedula[-3:]}" if len(cedula) >= 3 else "***",
                    "cedula_hash": self._hash_pii(cedula.strip(), hmac_key),
                    "estado": "error",
                    "detalles": f"Fallo de validación: {validation.message}"
                })
            else:
                records_validos.append(record)
                
        return records_validos

    def _dispatch_workers(self, records_validos, pdf_dir, hmac_key, subject_template,
                          batch_record, errores, records_fallidos, email_corrections,
                          valid_failed_count, on_progress, on_stats_update, on_log):
        """Fase 2: Dispatching concurrent workers in dynamic chunks."""
        if on_progress:
            on_progress("Iniciando envío masivo en paralelo...", 0.0)
        if on_log:
            on_log(f"Iniciando envío masivo para {len(records_validos)} destinatarios válidos...")
            
        total_validos = len(records_validos)
        completed_count = [0]
        success_count = [0]
        failed_count = [valid_failed_count]
        lock = threading.Lock()
        
        # Determinar hilos de trabajadores SMTP (máximo 4)
        num_workers = min(4, total_validos)
        if on_log:
            on_log(f"Distribuyendo carga en {num_workers} hilos de ejecución SMTP...")
        
        # Dividir los registros en trozos balanceados
        chunks = [records_validos[i::num_workers] for i in range(num_workers)]
        
        # Lanzamiento de tareas concurrentes
        with ThreadPoolExecutor(max_workers=num_workers) as executor:
            for w_id, chunk in enumerate(chunks):
                executor.submit(
                    self._process_chunk_worker, chunk, w_id, pdf_dir, hmac_key, 
                    subject_template, batch_record, errores, records_fallidos,
                    on_progress, on_stats_update, on_log, lock,
                    completed_count, success_count, failed_count, total_validos
                )

    def _process_chunk_worker(self, chunk_records, worker_id, pdf_dir, hmac_key, 
                              subject_template, batch_record, errores, records_fallidos,
                              on_progress, on_stats_update, on_log, lock,
                              completed_count, success_count, failed_count, total_validos):
        """Tarea concurrente individual de cada hilo para procesar su respectivo chunk."""
        email_service = EmailService()
        try:
            email_service.connect()
        except Exception as e:
            logger.error(f"Hilo {worker_id} no pudo conectar a SMTP: {str(e)}")
            with lock:
                for rec in chunk_records:
                    err_msg = f"Error de conexión SMTP ({str(e)})"
                    errores.append(f"{rec.get('email')}: {err_msg}")
                    records_fallidos.append(rec)
                    completed_count[0] += 1
                    failed_count[0] += 1
                    if on_stats_update:
                        on_stats_update(failed=failed_count[0])
                    if on_log:
                        on_log(f"✗ ERROR HILO {worker_id}: {mask_email(rec.get('email'))} (Fallo conexión SMTP)")
                    
                    count = completed_count[0]
                    progress = count / total_validos
                    if on_progress:
                        on_progress(f"Procesando {count} de {total_validos}...", progress)
                    
                    # Registrar error en historial efímero
                    rec_email = str(rec.get("email", "")).strip()
                    rec_file = str(rec.get("id_archivo", "")).strip()
                    rec_srv = str(rec.get("id_servicio", "")).strip()
                    rec_ced = str(rec.get("cedula", "")).strip()
                    batch_record["envios"].append({
                        "email": mask_email(rec_email),
                        "email_hash": self._hash_pii(rec_email.strip().lower(), hmac_key),
                        "id_archivo": os.path.basename(rec_file),
                        "id_servicio": rec_srv,
                        "cedula": f"***{rec_ced[-3:]}" if len(rec_ced) >= 3 else "***",
                        "cedula_hash": self._hash_pii(rec_ced.strip(), hmac_key),
                        "estado": "error",
                        "detalles": err_msg
                    })
            return
        
        try:
            for record in chunk_records:
                email = str(record.get("email", "")).strip()
                id_archivo = str(record.get("id_archivo", "")).strip()
                id_servicio = str(record.get("id_servicio", "")).strip()
                cedula = str(record.get("cedula", "")).strip()
                
                if not email or not id_archivo or not cedula:
                    with lock:
                        completed_count[0] += 1
                        failed_count[0] += 1
                        if on_stats_update:
                            on_stats_update(failed=failed_count[0])
                        if on_log:
                            on_log("✗ OMITIDO: Faltan datos en el registro (email, id_archivo o cedula vacíos).")
                        count = completed_count[0]
                        progress = count / total_validos
                        if on_progress:
                            on_progress(f"Procesando {count} de {total_validos}...", progress)
                        
                        batch_record["envios"].append({
                            "email": mask_email(email) if email else "Desconocido",
                            "email_hash": self._hash_pii(email.strip().lower() if email else "", hmac_key),
                            "id_archivo": os.path.basename(id_archivo) if id_archivo else "Desconocido",
                            "id_servicio": id_servicio,
                            "cedula": f"***{cedula[-3:]}" if len(cedula) >= 3 else "***",
                            "cedula_hash": self._hash_pii(cedula.strip(), hmac_key),
                            "estado": "error",
                            "detalles": "Datos obligatorios incompletos en fila CSV"
                        })
                    continue
                
                # Seguridad: Sanitizar id_archivo contra ataques de path traversal
                id_archivo = os.path.basename(id_archivo)
                id_archivo = re.sub(r'[^\w.\-]', '_', id_archivo)
                if not id_archivo.lower().endswith(".pdf"):
                    id_archivo += ".pdf"
                
                input_pdf = os.path.join(pdf_dir, id_archivo)
                
                # Seguridad: Validar que la ruta resultante está estrictamente dentro del directorio esperado
                real_input = os.path.realpath(input_pdf)
                real_dir = os.path.realpath(pdf_dir)
                if not real_input.startswith(real_dir + os.sep) and real_input != real_dir:
                    logger.error(f"Intento de path traversal detectado: {id_archivo}")
                    with lock:
                        err_msg = f"Ruta de archivo sospechosa activa bloqueada ({id_archivo})"
                        errores.append(f"{email}: {err_msg}")
                        records_fallidos.append(record)
                        completed_count[0] += 1
                        failed_count[0] += 1
                        if on_stats_update:
                            on_stats_update(failed=failed_count[0])
                        if on_log:
                            on_log(f"✗ SEGURIDAD: Path traversal bloqueado para {mask_email(email)}")
                        batch_record["envios"].append({
                            "email": mask_email(email),
                            "email_hash": self._hash_pii(email.strip().lower(), hmac_key),
                            "id_archivo": id_archivo,
                            "id_servicio": id_servicio,
                            "cedula": f"***{cedula[-3:]}" if len(cedula) >= 3 else "***",
                            "cedula_hash": self._hash_pii(cedula.strip(), hmac_key),
                            "estado": "error",
                            "detalles": err_msg
                        })
                    continue
                
                if not os.path.exists(input_pdf):
                    logger.error(f"Falta el archivo PDF: {os.path.basename(input_pdf)} (Destino: {mask_email(email)})")
                    with lock:
                        err_msg = f"PDF no encontrado ({id_archivo})"
                        errores.append(f"{email}: {err_msg}")
                        records_fallidos.append(record)
                        completed_count[0] += 1
                        failed_count[0] += 1
                        if on_stats_update:
                            on_stats_update(failed=failed_count[0])
                        if on_log:
                            on_log(f"✗ ERROR: PDF no encontrado para {mask_email(email)}")
                        count = completed_count[0]
                        progress = count / total_validos
                        if on_progress:
                            on_progress(f"Procesando {count} de {total_validos}: {email} (Omitido)", progress)
                        
                        batch_record["envios"].append({
                            "email": mask_email(email),
                            "email_hash": self._hash_pii(email.strip().lower(), hmac_key),
                            "id_archivo": id_archivo,
                            "id_servicio": id_servicio,
                            "cedula": f"***{cedula[-3:]}" if len(cedula) >= 3 else "***",
                            "cedula_hash": self._hash_pii(cedula.strip(), hmac_key),
                            "estado": "error",
                            "detalles": err_msg
                        })
                    continue
                
                # Crear ruta de archivo temporal segura (previene colisiones de procesos)
                fd, temp_pdf = tempfile.mkstemp(suffix=".pdf", prefix=f"sems_{worker_id}_", dir=tempfile.gettempdir())
                os.close(fd)
                
                try:
                    # Cifrado AES-256
                    PDFCrypto.encrypt_pdf(input_pdf, temp_pdf, cedula)
                    
                    # Formatear asunto dinámico
                    subject = subject_template.replace("{id_servicio}", id_servicio)
                    
                    # Envío SMTP seguro
                    email_service.send_email_with_attachment(email, subject, temp_pdf, filename_override=id_archivo)
                    logger.info(f"Éxito en envío: {mask_email(email)}")
                    
                    with lock:
                        success_count[0] += 1
                        if on_stats_update:
                            on_stats_update(success=success_count[0])
                        if on_log:
                            on_log(f"✓ ENVIADO: {mask_email(email)} - PDF Cifrado")
                        
                        batch_record["envios"].append({
                            "email": mask_email(email),
                            "email_hash": self._hash_pii(email.strip().lower(), hmac_key),
                            "id_archivo": id_archivo,
                            "id_servicio": id_servicio,
                            "cedula": f"***{cedula[-3:]}" if len(cedula) >= 3 else "***",
                            "cedula_hash": self._hash_pii(cedula.strip(), hmac_key),
                            "estado": "exito",
                            "detalles": None
                        })
                except Exception as e:
                    logger.error(f"Fallo de envío con {mask_email(email)}: {str(e)}")
                    with lock:
                        err_msg = str(e)
                        errores.append(f"{email}: Error ({err_msg})")
                        records_fallidos.append(record)
                        failed_count[0] += 1
                        if on_stats_update:
                            on_stats_update(failed=failed_count[0])
                        if on_log:
                            on_log(f"✗ ERROR: {mask_email(email)} - {err_msg}")
                        
                        batch_record["envios"].append({
                            "email": mask_email(email),
                            "email_hash": self._hash_pii(email.strip().lower(), hmac_key),
                            "id_archivo": id_archivo,
                            "id_servicio": id_servicio,
                            "cedula": f"***{cedula[-3:]}" if len(cedula) >= 3 else "***",
                            "cedula_hash": self._hash_pii(cedula.strip(), hmac_key),
                            "estado": "error",
                            "detalles": err_msg
                        })
                finally:
                    # Borrado seguro síncrono (previene archivos huérfanos al cerrar la app)
                    if os.path.exists(temp_pdf):
                        PDFCrypto.secure_cleanup(temp_pdf)
                
                with lock:
                    completed_count[0] += 1
                    count = completed_count[0]
                    progress = count / total_validos
                    if on_progress:
                        on_progress(f"Procesando {count} de {total_validos}: {email}", progress)
        finally:
            email_service.disconnect()
