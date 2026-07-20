import os
import re
import smtplib
import tempfile
import time
import threading
import hashlib
import hmac
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
from src.core.data_manager import DataManager
from src.core.pdf_crypto import PDFCrypto
from src.core.email_service import EmailService
from src.config.config_manager import ConfigManager
from src.utils.logger import logger, mask_email, mask_filename
from src.utils.email_validator import validate_email

class WorkflowOrchestrator:
    """Orquestador desacoplado de lógica de negocio y concurrencia.
    
    Aplica el principio de Responsabilidad Única (SRP) de SOLID, separando por completo
    el procesamiento masivo de la capa de interfaz de usuario de CustomTkinter.
    """
    
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
            send_delay = config.get("send_delay", 2)
            
            errores = []
            records_fallidos = []
            email_corrections = {}
            pdf_corrections = {}
            
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
                batch_record["raw_records_fallidos"] = records_fallidos
                batch_record["raw_email_corrections"] = email_corrections
                batch_record["raw_pdf_corrections"] = pdf_corrections
                if on_complete:
                    on_complete(errores, total, records_fallidos, email_corrections, pdf_corrections)
                return
            
            # === FASE 2: Envío de correos válidos en Paralelo ===
            exitosos_total, fallidos_total = self._dispatch_workers(
                records_validos, pdf_dir, hmac_key, subject_template,
                batch_record, errores, records_fallidos, email_corrections,
                len(records) - len(records_validos),
                on_progress, on_stats_update, on_log, send_delay,
                pdf_corrections
            )

            # Consolidar totales del lote con los contadores reales de los workers
            # (única fuente de verdad: "total - len(errores)" divergía del monitor
            # en vivo cuando un hilo terminaba de forma anómala).
            batch_record["exitosos"] = exitosos_total
            batch_record["fallidos"] = fallidos_total
            batch_record["raw_records_fallidos"] = records_fallidos
            batch_record["raw_email_corrections"] = email_corrections
            batch_record["raw_pdf_corrections"] = pdf_corrections
            
            if on_progress:
                on_progress("¡Proceso masivo completado!", 1.0)
            if on_complete:
                on_complete(errores, total, records_fallidos, email_corrections, pdf_corrections)
                
        except Exception as e:
            logger.critical(f"Fallo fatal en el orquestador: {str(e)}")
            if on_log:
                on_log(f"✗ FALLO CRÍTICO: {str(e)}")
            if on_progress:
                on_progress("Error fatal en procesamiento.", 1.0)
            if on_complete:
                on_complete([f"Error fatal: {str(e)}"], 0, [], {}, {})

    def _hash_pii(self, value: str, hmac_key: bytes) -> str:
        """Helper para hash seguro HMAC-SHA256 de PII."""
        if not value or not hmac_key:
            return ""
        return hmac.new(hmac_key, value.encode(), hashlib.sha256).hexdigest()

    def _register_envio(self, batch_record, email, cedula, id_archivo, id_servicio, hmac_key, estado, detalles):
        """Registra un envío individual en el historial efímero del lote (enmascarado y con hash)."""
        batch_record["envios"].append({
            "email": mask_email(email) if email else "Desconocido",
            "email_hash": self._hash_pii(email.strip().lower() if email else "", hmac_key),
            "id_archivo": os.path.basename(id_archivo) if id_archivo else "Desconocido",
            "id_servicio": id_servicio,
            "cedula": f"***{cedula[-3:]}" if (cedula and len(cedula) >= 3) else "***",
            "cedula_hash": self._hash_pii(cedula.strip() if cedula else "", hmac_key),
            "estado": estado,
            "detalles": detalles
        })

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
                # INTEGRIDAD (A-04): registrar la omisión en errores y records_fallidos;
                # de lo contrario "exitosos = total - len(errores)" la cuenta como éxito
                # y la fila queda irrecuperable para el reintento.
                errores.append("Fila sin correo electrónico: registro omitido")
                records_fallidos.append(record)
                if on_stats_update:
                    on_stats_update(failed=valid_failed_count)
                if on_log:
                    on_log("⚠ OMITIDO: Fila sin correo electrónico.")
                self._register_envio(
                    batch_record, email, cedula, id_archivo, id_servicio, hmac_key,
                    "error", "Fila sin correo electrónico"
                )
                continue
            
            validation = validate_email(email)
            if not validation.is_valid:
                valid_failed_count += 1
                if on_stats_update:
                    on_stats_update(failed=valid_failed_count)
                
                # Saneamiento PII: Enmascarar sugerencia en errores públicos.
                # SEGURIDAD (C-01): la clave del dict es el email REAL normalizado, nunca la
                # máscara: mask_email no es inyectiva y una colisión aplicaría la corrección
                # de una persona al registro de otra (envío cruzado de documentos).
                msg = f"{mask_email(email)}: {validation.message}"
                if validation.suggestion:
                    msg += f" (Sugerencia: {mask_email(validation.suggestion)})"
                    email_corrections[email.strip().lower()] = validation.suggestion
                errores.append(msg)
                records_fallidos.append(record)
                logger.warning(f"Email rechazado pre-envío: {validation.message}")
                if on_log:
                    on_log(f"✗ RECHAZADO: {mask_email(email)} ({validation.message})")
                
                # Registrar usando el helper unificado
                self._register_envio(
                    batch_record, email, cedula, id_archivo, id_servicio, hmac_key,
                    "error", f"Fallo de validación: {validation.message}"
                )
            else:
                records_validos.append(record)
                
        return records_validos

    def _dispatch_workers(self, records_validos, pdf_dir, hmac_key, subject_template,
                          batch_record, errores, records_fallidos, email_corrections,
                          valid_failed_count, on_progress, on_stats_update, on_log, send_delay=2,
                          pdf_corrections=None):
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
        
        # Throttling global compartido (M-01): un solo marcapasos para todos los hilos,
        # de lo contrario el retardo configurado se multiplica por el número de workers.
        throttle = {"lock": threading.Lock(), "next_slot": [0.0]}

        # Lanzamiento de tareas concurrentes
        with ThreadPoolExecutor(max_workers=num_workers) as executor:
            futures = [
                executor.submit(
                    self._process_chunk_worker, chunk, w_id, pdf_dir, hmac_key,
                    subject_template, batch_record, errores, records_fallidos,
                    on_progress, on_stats_update, on_log, lock,
                    completed_count, success_count, failed_count, total_validos, send_delay,
                    pdf_corrections, throttle
                )
                for w_id, chunk in enumerate(chunks)
            ]

        # RESILIENCIA (A-03): consultar los futures como último recurso. El worker ya
        # registra sus registros restantes como fallidos si revienta; este bloque solo
        # cubriría una excepción fuera de ese manejo.
        for w_id, future in enumerate(futures):
            exc = future.exception()
            if exc:
                logger.critical(f"El hilo de envío {w_id} terminó con excepción no controlada: {exc}")
                with lock:
                    errores.append(f"Hilo de envío {w_id}: fallo interno no controlado ({self._sanitize_error(exc)})")
                if on_log:
                    on_log(f"✗ FALLO INTERNO: El hilo {w_id} se detuvo inesperadamente. Revise el reporte.")

        return success_count[0], failed_count[0]

    def _register_chunk_failures(self, pending_records, err_msg, worker_id, batch_record,
                                 errores, records_fallidos, hmac_key, lock,
                                 completed_count, failed_count, total_validos,
                                 on_stats_update, on_log, on_progress):
        """Registra como fallidos reintentables todos los registros pendientes de un chunk.

        INTEGRIDAD (A-03 reforzado): si un hilo muere a mitad de su chunk, cada registro
        no procesado debe quedar en errores/records_fallidos/envios; de lo contrario se
        contarían como éxito y serían irrecuperables para el reintento.
        """
        with lock:
            for rec in pending_records:
                rec_email = rec.get('email', '')
                errores.append(f"{mask_email(rec_email)}: {err_msg}")
                records_fallidos.append(rec)
                completed_count[0] += 1
                failed_count[0] += 1
                if on_stats_update:
                    on_stats_update(failed=failed_count[0])
                if on_log:
                    on_log(f"✗ ERROR HILO {worker_id}: {mask_email(rec_email)} ({err_msg})")
                count = completed_count[0]
                if on_progress:
                    on_progress(f"Procesando {count} de {total_validos}: {mask_email(rec_email)} (Fallo)", count / total_validos)
                self._register_envio(
                    batch_record, rec_email, rec.get("cedula", ""),
                    rec.get("id_archivo", ""), rec.get("id_servicio", ""),
                    hmac_key, "error", err_msg
                )

    def _sanitize_error(self, exception: Exception) -> str:
        """Sanitiza mensajes de error de SMTP/Red para evitar fugas de información interna (como IPs o hosts)."""
        error_msg = str(exception)
        error_msg_lower = error_msg.lower()
        if "authentication unsuccessful" in error_msg_lower or "535" in error_msg_lower:
            return "Error de autenticación SMTP. Verifique sus credenciales."
        if "connection refused" in error_msg_lower or "timed out" in error_msg_lower or "timeout" in error_msg_lower:
            return "Error de conexión. No se pudo establecer contacto con el servidor SMTP."
        if "starttls" in error_msg_lower:
            return "Conexión SMTP abortada por falta de soporte seguro (STARTTLS) en el servidor."
        if "not found" in error_msg_lower or "no se encontró" in error_msg_lower:
            return "El archivo PDF adjunto no fue encontrado."
        if "smtp" in error_msg_lower:
            return "Error en el servidor de correo SMTP al procesar la solicitud."
            
        # Si es un error general, omitimos detalles de red/servidor del string
        return "Error inesperado al procesar o enviar el correo."

    def _process_chunk_worker(self, chunk_records, worker_id, pdf_dir, hmac_key,
                              subject_template, batch_record, errores, records_fallidos,
                              on_progress, on_stats_update, on_log, lock,
                              completed_count, success_count, failed_count, total_validos, send_delay=2,
                              pdf_corrections=None, throttle=None):
        """Tarea concurrente individual de cada hilo para procesar su respectivo chunk."""
        email_service = EmailService()
        try:
            email_service.connect()
        except Exception as e:
            logger.error(f"Hilo {worker_id} no pudo conectar a SMTP: {str(e)}")
            self._register_chunk_failures(
                chunk_records, self._sanitize_error(e), worker_id, batch_record,
                errores, records_fallidos, hmac_key, lock,
                completed_count, failed_count, total_validos,
                on_stats_update, on_log, on_progress
            )
            return

        try:
            # Cargar configuraciones de contraseña PDF una vez por worker
            config = ConfigManager.get_config()
            pwd_prefix = config.get("pdf_password_prefix", "")
            pwd_suffix = config.get("pdf_password_suffix", "")

            idx = 0
            try:
                for idx, record in enumerate(chunk_records):
                    self._process_single_record(
                        record, worker_id, email_service, pdf_dir, hmac_key,
                        subject_template, batch_record, errores, records_fallidos,
                        on_progress, on_stats_update, on_log, lock,
                        completed_count, success_count, failed_count, total_validos, send_delay,
                        pdf_corrections, pwd_prefix, pwd_suffix, throttle
                    )
            except Exception as e:
                # INTEGRIDAD (A-03 reforzado): si el hilo revienta a mitad del chunk,
                # el registro en curso y los restantes se registran como fallidos
                # reintentables en vez de perderse contados como éxito.
                logger.critical(f"Hilo {worker_id}: excepción no controlada a mitad de chunk: {str(e)}")
                self._register_chunk_failures(
                    chunk_records[idx:], self._sanitize_error(e), worker_id, batch_record,
                    errores, records_fallidos, hmac_key, lock,
                    completed_count, failed_count, total_validos,
                    on_stats_update, on_log, on_progress
                )
        finally:
            # RESILIENCIA (A-03): quit() puede lanzar SMTPServerDisconnected si el servidor
            # ya cerró; no debe matar el hilo ni ocultar el resultado del chunk.
            try:
                email_service.disconnect()
            except Exception as e:
                logger.warning(f"Cierre de conexión SMTP del hilo {worker_id} falló (ignorado): {e}")

    def _global_throttle_wait(self, throttle, send_delay):
        """Marcapasos global (M-01): reserva un turno de envío espaciado send_delay segundos
        entre TODOS los hilos, para que el retardo configurado sea la tasa real del lote."""
        if not throttle or send_delay <= 0:
            return
        with throttle["lock"]:
            now = time.monotonic()
            wait = max(0.0, throttle["next_slot"][0] - now)
            throttle["next_slot"][0] = max(throttle["next_slot"][0], now) + send_delay
        if wait > 0:
            time.sleep(wait)

    def _process_single_record(self, record, worker_id, email_service, pdf_dir, hmac_key,
                               subject_template, batch_record, errores, records_fallidos,
                               on_progress, on_stats_update, on_log, lock,
                               completed_count, success_count, failed_count, total_validos, send_delay,
                               pdf_corrections, pwd_prefix, pwd_suffix, throttle=None):
        """Procesa y envía un único registro del lote de envíos."""
        email = str(record.get("email", "")).strip()
        id_archivo = str(record.get("id_archivo", "")).strip()
        id_servicio = str(record.get("id_servicio", "")).strip()
        cedula = str(record.get("cedula", "")).strip()
        
        if not email or not id_archivo or not cedula:
            with lock:
                # INTEGRIDAD (A-04): la omisión debe reflejarse en errores/records_fallidos
                errores.append(
                    f"{mask_email(email) if email else 'Fila sin correo'}: "
                    f"Datos obligatorios incompletos en fila CSV (email, id_archivo o cedula)"
                )
                records_fallidos.append(record)
                completed_count[0] += 1
                failed_count[0] += 1
                if on_stats_update:
                    on_stats_update(failed=failed_count[0])
                if on_log:
                    on_log("✗ OMITIDO: Faltan datos en el registro (email, id_archivo o cedula vacíos).")
                count = completed_count[0]
                progress = count / total_validos
                if on_progress:
                    on_progress(f"Procesando {count} de {total_validos}: Omitido (Datos incompletos)", progress)
                
                self._register_envio(
                    batch_record, email, cedula, id_archivo, id_servicio, hmac_key,
                    "error", "Datos obligatorios incompletos en fila CSV"
                )
            return

        # Resolver la ruta física de entrada para el PDF
        input_pdf, id_archivo_sanitized, resolve_err = self._resolve_pdf_path(id_archivo, pdf_dir)
        if resolve_err:
            with lock:
                errores.append(f"{mask_email(email)}: {resolve_err}")
                records_fallidos.append(record)
                completed_count[0] += 1
                failed_count[0] += 1
                if on_stats_update:
                    on_stats_update(failed=failed_count[0])
                if on_log:
                    on_log(f"✗ SEGURIDAD: {resolve_err} para {mask_email(email)}")
                count = completed_count[0]
                progress = count / total_validos
                if on_progress:
                    on_progress(f"Procesando {count} de {total_validos}: {mask_email(email)} (Error)", progress)
                
                self._register_envio(
                    batch_record, email, cedula, id_archivo, id_servicio, hmac_key,
                    "error", resolve_err
                )
            return

        # Verificar si el archivo PDF existe físicamente
        if not os.path.exists(input_pdf):
            similar_pdf = self._find_similar_pdf(pdf_dir, os.path.basename(id_archivo.replace('\\', '/')))
            
            with lock:
                if similar_pdf:
                    err_msg = f"PDF no encontrado ({id_archivo_sanitized}) (Sugerencia: {similar_pdf})"
                else:
                    err_msg = f"PDF no encontrado ({id_archivo_sanitized})"
                    
                logger.error(f"Falta el archivo PDF: {mask_filename(input_pdf)} (Destino: {mask_email(email)})")
                errores.append(f"{mask_email(email)}: {err_msg}")
                records_fallidos.append(record)
                completed_count[0] += 1
                failed_count[0] += 1
                if on_stats_update:
                    on_stats_update(failed=failed_count[0])
                if on_log:
                    if similar_pdf:
                        on_log(f"✗ ERROR: PDF no encontrado para {mask_email(email)} (Sugerencia: {similar_pdf})")
                    else:
                        on_log(f"✗ ERROR: PDF no encontrado para {mask_email(email)}")
                count = completed_count[0]
                progress = count / total_validos
                if on_progress:
                    on_progress(f"Procesando {count} de {total_validos}: {mask_email(email)} (Omitido)", progress)
                
                self._register_envio(
                    batch_record, email, cedula, id_archivo_sanitized, id_servicio, hmac_key,
                    "error", err_msg
                )
            return

        # Crear directorio temporal único e independiente
        temp_dir = tempfile.mkdtemp(prefix="sems_batch_")
        fd, temp_pdf = tempfile.mkstemp(suffix=".pdf", prefix=f"sems_{worker_id}_", dir=temp_dir)
        os.close(fd)
        
        try:
            # Construir la contraseña fortalecida
            pdf_password = f"{pwd_prefix}{cedula}{pwd_suffix}"

            # Throttling global (M-01): reservar turno de envío antes de transmitir
            self._global_throttle_wait(throttle, send_delay)

            # Cifrado y envío
            try:
                self._encrypt_and_send(
                    input_pdf, temp_pdf, pdf_password, email, id_servicio, id_archivo_sanitized,
                    subject_template, email_service, batch_record, hmac_key, record, lock,
                    success_count, failed_count, errores, records_fallidos, on_stats_update, on_log
                )
            except (smtplib.SMTPServerDisconnected, smtplib.SMTPSenderRefused):
                # RESILIENCIA (A-05): la conexión persistente murió (habitual bajo carga con
                # Gmail). Reconectar una vez evita que el resto del chunk falle en cascada.
                logger.warning(f"Hilo {worker_id}: conexión SMTP perdida; reconectando para reintento local...")
                try:
                    email_service.disconnect()
                except Exception:
                    pass
                email_service.connect()
                self._encrypt_and_send(
                    input_pdf, temp_pdf, pdf_password, email, id_servicio, id_archivo_sanitized,
                    subject_template, email_service, batch_record, hmac_key, record, lock,
                    success_count, failed_count, errores, records_fallidos, on_stats_update, on_log
                )
        except Exception as e:
            logger.error(f"Fallo de procesamiento con {mask_email(email)}: {str(e)}")
            err_msg = self._sanitize_error(e)
            with lock:
                errores.append(f"{mask_email(email)}: {err_msg}")
                records_fallidos.append(record)
                failed_count[0] += 1
                if on_stats_update:
                    on_stats_update(failed=failed_count[0])
                if on_log:
                    on_log(f"✗ ERROR: {mask_email(email)} - {err_msg}")
                
                self._register_envio(
                    batch_record, email, cedula, id_archivo_sanitized, id_servicio, hmac_key,
                    "error", err_msg
                )
        finally:
            # Borrado seguro síncrono del archivo PDF temporal
            if os.path.exists(temp_pdf):
                PDFCrypto.secure_cleanup(temp_pdf)
            # Limpieza del directorio temporal contenedor vacío
            if os.path.exists(temp_dir):
                try:
                    os.rmdir(temp_dir)
                except Exception as ex:
                    logger.warning(f"No se pudo eliminar directorio temporal {temp_dir}: {str(ex)}")
            # Nota (M-01): el throttling ahora es global y se aplica ANTES del envío
            # (_global_throttle_wait); el sleep por worker duplicaba la tasa configurada.
        
        with lock:
            completed_count[0] += 1
            count = completed_count[0]
            progress = count / total_validos
            if on_progress:
                on_progress(f"Procesando {count} de {total_validos}: {mask_email(email)}", progress)

    def _resolve_pdf_path(self, id_archivo: str, pdf_dir: str):
        """Sanitiza y verifica el archivo PDF de entrada contra ataques de Path Traversal.
        
        Retorna (ruta_completa, archivo_sanitizado, error_msg).
        """
        # Normalizar separadores
        id_archivo_clean = id_archivo.replace('\\', '/')
        id_archivo_base = os.path.basename(id_archivo_clean)
        id_archivo_sanitized = re.sub(r'[^\w.\- ]', '_', id_archivo_base)
        if not id_archivo_sanitized.lower().endswith(".pdf"):
            id_archivo_sanitized += ".pdf"
            
        id_archivo_os = id_archivo.replace('\\', os.sep).replace('/', os.sep)
        input_pdf = os.path.join(pdf_dir, id_archivo_os)
        
        # Validar Path Traversal
        real_input = os.path.normcase(os.path.realpath(input_pdf))
        real_dir = os.path.normcase(os.path.realpath(pdf_dir))
        if not real_input.startswith(real_dir + os.sep) and real_input != real_dir:
            logger.error(f"Intento de path traversal detectado: {mask_filename(id_archivo)}")
            return None, id_archivo_sanitized, f"Ruta de archivo sospechosa activa bloqueada ({id_archivo})"
            
        # Si existe físicamente con su ruta original, resolver a esa
        original_pdf_path = os.path.realpath(os.path.join(pdf_dir, id_archivo_os))
        if os.path.exists(original_pdf_path) and os.path.isfile(original_pdf_path):
            return original_pdf_path, id_archivo_sanitized, None
            
        # De lo contrario usar el nombre sanitizado
        return os.path.join(pdf_dir, id_archivo_sanitized), id_archivo_sanitized, None

    def _encrypt_and_send(self, input_pdf, temp_pdf, pdf_password, email, id_servicio, id_archivo_sanitized,
                           subject_template, email_service, batch_record, hmac_key, record, lock,
                           success_count, failed_count, errores, records_fallidos, on_stats_update, on_log):
        """Aplica cifrado y envía el correo usando el servicio SMTP."""
        # Cifrado AES-256
        PDFCrypto.encrypt_pdf(input_pdf, temp_pdf, pdf_password)
        
        # Formatear asunto dinámico
        if "{id_servicio}" in subject_template:
            subject = subject_template.replace("{id_servicio}", id_servicio)
        else:
            subject = f"{subject_template.strip()} - {id_servicio}"

        # RESILIENCIA (A-05): Message-ID determinista por registro y día. Si un timeout
        # ambiguo obliga a reintentar un envío que sí llegó, el receptor puede deduplicar
        # y el historial permite auditar el duplicado.
        idempotency_key = None
        if hmac_key:
            raw = f"{email}|{id_archivo_sanitized}|{record.get('cedula', '')}|{datetime.now().strftime('%Y%m%d')}"
            idempotency_key = self._hash_pii(raw, hmac_key)[:24]

        # Envío SMTP seguro
        email_service.send_email_with_attachment(
            email, subject, temp_pdf,
            filename_override=id_archivo_sanitized,
            idempotency_key=idempotency_key
        )
        
        with lock:
            success_count[0] += 1
            if on_stats_update:
                on_stats_update(success=success_count[0])
            if on_log:
                on_log(f"✓ ENVIADO: {mask_email(email)} - PDF Cifrado")
            
            self._register_envio(
                batch_record, email, record.get("cedula", ""), id_archivo_sanitized, id_servicio,
                hmac_key, "exito", None
            )

    def _find_similar_pdf(self, pdf_dir: str, target_filename: str) -> str:
        """Busca en el directorio de PDFs si existe algún archivo similar al buscado.
        
        Soporta:
        1. Coincidencia exacta de nombre original (por si la sanitización lo cambió).
        2. Coincidencia sin distinguir mayúsculas/minúsculas (case-insensitive).
        3. Archivos sin extensión en el CSV pero con extensión en disco.
        4. Coincidencia por similitud de caracteres (Levenshtein/SequenceMatcher).
        """
        if not pdf_dir or not os.path.isdir(pdf_dir):
            return None
            
        try:
            files = os.listdir(pdf_dir)
        except Exception:
            return None
            
        pdf_files = [f for f in files if f.lower().endswith('.pdf')]
        if not pdf_files:
            return None
            
        # 1. Coincidencia exacta o case-insensitive
        target_clean = target_filename.replace('\\', '/').split('/')[-1]
        for f in files:
            if f.lower() == target_clean.lower():
                return f
                
        # 2. Si no tiene extensión .pdf, probar añadiéndola
        target_name = target_clean
        if not target_name.lower().endswith('.pdf'):
            target_name_with_ext = target_name + ".pdf"
            for f in pdf_files:
                if f.lower() == target_name_with_ext.lower():
                    return f
                    
        # 3. Comparación por similitud de caracteres (SequenceMatcher)
        import difflib
        best_match = None
        best_ratio = 0.0
        
        target_name_lower = target_name.lower()
        if target_name_lower.endswith('.pdf'):
            target_base = target_name_lower[:-4]
        else:
            target_base = target_name_lower
            
        for f in pdf_files:
            f_base = f[:-4].lower()
            ratio = difflib.SequenceMatcher(None, target_base, f_base).ratio()
            if ratio > best_ratio:
                best_ratio = ratio
                best_match = f
                
        # Umbral del 75% de similitud para considerarlo una sugerencia válida
        if best_ratio >= 0.75:
            return best_match
            
        return None
