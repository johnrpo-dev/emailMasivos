# pyrefly: ignore [missing-import]
import os
from src.ui import dialogs
from src.core.workflow_orchestrator import WorkflowOrchestrator
from src.ui.modals.results_modal import ResultsModal
from src.core.license_manager import LicenseManager
from src.utils.logger import logger, mask_email, mask_filename

class WorkflowController:
    """Controlador encargado de coordinar la ejecución del flujo de envío masivo y lógica de reintentos."""
    def __init__(self, app):
        self.app = app
        self._retry_count = 0
        self.MAX_RETRIES = 10
        # Candado de exclusión: evita lanzar dos workflows concurrentes (envíos
        # duplicados) desde Iniciar Proceso o los botones de reintento de los modales.
        self._workflow_active = False

    def is_busy(self) -> bool:
        """Indica si hay un workflow de envío en ejecución."""
        return self._workflow_active

    def _warn_busy(self):
        dialogs.show_warning(
            self.app, "Proceso en curso",
            "Ya hay un envío en ejecución. Espere a que termine antes de iniciar o reintentar otro."
        )

    def start_process(self):
        """Prepara e inicia la orquestación del proceso en segundo plano."""
        if self._workflow_active:
            self._warn_busy()
            return
        self._retry_count = 0
        if not self.app.csv_path.get() or not self.app.pdf_dir.get():
            dialogs.show_warning(self.app, "Atención", "Selecciona el CSV y la carpeta de PDFs.")
            return

        from src.config.config_manager import ConfigManager
        config = ConfigManager.get_config()
        if not config.get("smtp_user") or not config.get("smtp_password"):
            dialogs.show_warning(self.app, "Atención", "Ve a la pestaña de Configuración e ingresa tus credenciales SMTP primero.")
            return

        self._workflow_active = True
        self.app.home_panel.set_busy(True)
        self.app.home_panel.progress_bar.set(0)
        self.app.home_panel.lbl_status.configure(text="Procesando...")
        
        self.execute_workflow()

    def execute_workflow(self, records_to_process=None):
        orchestrator = WorkflowOrchestrator()
        
        def on_batch_added(batch_record):
            def _add():
                batch_record["id"] = len(self.app.session_batches) + 1
                self.app.session_batches.append(batch_record)
            self.app.after(0, _add)

        # CONCURRENCIA (A-02): Tkinter no es thread-safe. TODO callback invocado desde los
        # hilos worker debe marshalearse al hilo principal con app.after().
        def on_log(text):
            self.app.after(0, lambda t=text: self.app.home_panel.add_console_log(t))

        def on_progress(text, progress=None):
            self.app.after(0, lambda: self.app.home_panel.update_ui_status(text, progress))

        def on_stats_update(total=None, success=None, failed=None):
            self.app.after(0, lambda t=total, s=success, f=failed:
                           self.app.home_panel.update_monitor_stats(total=t, success=s, failed=f))

        def on_complete(errores, total, records_fallidos, email_corrections, pdf_corrections=None):
            def _complete():
                try:
                    LicenseManager.update_last_run()

                    # Depurar de los lotes anteriores en RAM los registros que este
                    # lote acaba de entregar con éxito, para que "Reintentar" desde
                    # el historial no duplique correos ya enviados.
                    self._purge_recovered_failures()

                    exitosos_total = max(0, total - len(errores))
                    self.app.home_panel.update_ui_status("¡Proceso masivo completado!", 1.0)
                    self.app.home_panel.add_console_log(f"✓ COMPLETADO: {exitosos_total} exitosos, {len(errores)} fallidos.")
                    
                    if self.app.state() == "iconic":
                        self.app.show_desktop_notification(
                            "Envío Masivo Terminado",
                            f"El proceso ha finalizado. Éxitos: {exitosos_total}, Errores: {len(errores)}"
                        )
                    
                    if errores:
                        self.show_results_modal(errores, total, records_fallidos, email_corrections, pdf_corrections)
                    elif total > 0:
                        dialogs.show_success(self.app, "Completado", "El proceso ha finalizado con éxito sin errores.")
                    else:
                        dialogs.show_warning(self.app, "Sin registros", "El archivo CSV no contiene registros para procesar.")
                finally:
                    self._workflow_active = False
                    self.app.home_panel.set_busy(False)
            self.app.after(0, _complete)

        orchestrator.start(
            csv_path=self.app.csv_path.get(),
            pdf_dir=self.app.pdf_dir.get(),
            hmac_key=self.app._hmac_key,
            on_batch_added=on_batch_added,
            on_log=on_log,
            on_progress=on_progress,
            on_stats_update=on_stats_update,
            on_complete=on_complete,
            records_to_process=records_to_process
        )

    def _purge_recovered_failures(self):
        """Elimina de los lotes en RAM los registros fallidos crudos que ya fueron
        entregados con éxito en un lote posterior.

        Sin esta depuración, el modal de detalle de un lote antiguo seguiría
        ofreciendo "Reintentar/Corregir" sobre destinatarios que ya recibieron su
        correo tras una corrección, duplicando envíos. El cruce usa el HMAC de la
        cédula (los envíos del historial están enmascarados) más el id_servicio.
        """
        sent_keys = set()
        for lote in self.app.session_batches:
            for ev in list(lote.get("envios", [])):
                if ev.get("estado") == "exito":
                    key = (ev.get("cedula_hash", ""), str(ev.get("id_servicio", "")).strip().lower())
                    sent_keys.add(key)
        if not sent_keys:
            return

        for lote in self.app.session_batches:
            raw = lote.get("raw_records_fallidos")
            if not raw:
                continue

            # SEGURIDAD (M-04, mismo caveat que la sincronización con CSV): si dos
            # registros fallidos distintos comparten (cedula, id_servicio), el éxito
            # de uno NO debe suprimir el reintento del otro. Las claves duplicadas
            # dentro del lote quedan excluidas de la purga.
            keys = []
            key_counts = {}
            for record in raw:
                cedula = str(record.get("cedula", "")).strip()
                servicio = str(record.get("id_servicio", "")).strip().lower()
                key = (self.app.compute_search_hash(cedula), servicio)
                keys.append(key)
                key_counts[key] = key_counts.get(key, 0) + 1

            remaining = []
            recovered_keys = set()
            for record, key in zip(raw, keys):
                if key in sent_keys and key_counts[key] == 1:
                    recovered_keys.add(key)
                else:
                    remaining.append(record)

            if not recovered_keys:
                continue

            lote["raw_records_fallidos"] = remaining

            # Consistencia del historial: el envío recuperado deja de figurar como
            # "Fallido" permanente y se marca con su estado real.
            for ev in lote.get("envios", []):
                if ev.get("estado") != "error":
                    continue
                ev_key = (ev.get("cedula_hash", ""), str(ev.get("id_servicio", "")).strip().lower())
                if ev_key in recovered_keys:
                    ev["estado"] = "recuperado"
                    base = ev.get("detalles") or ""
                    nota = "Entregado con éxito en un reintento posterior"
                    ev["detalles"] = f"{base} — {nota}" if base else nota
            lote["recuperados"] = lote.get("recuperados", 0) + len(recovered_keys)

            # Podar las correcciones ya aplicadas: sin esto el modal del lote seguiría
            # ofreciendo "Corregir y Reintentar" sobre correcciones sin destinatario.
            remaining_emails = {str(r.get("email", "")).strip().lower() for r in remaining}
            remaining_archivos = {str(r.get("id_archivo", "")).strip() for r in remaining}
            ec = lote.get("raw_email_corrections") or {}
            lote["raw_email_corrections"] = {k: v for k, v in ec.items() if k in remaining_emails}
            pc = lote.get("raw_pdf_corrections") or {}
            lote["raw_pdf_corrections"] = {k: v for k, v in pc.items() if k in remaining_archivos}

            logger.info(f"Historial: {len(recovered_keys)} registro(s) recuperados depurados del lote '{lote.get('csv_nombre', '')}'.")

    def _sync_records_with_current_csv(self, records_to_sync):
        """Recarga el archivo CSV en caliente y actualiza los campos de los registros
        en memoria (como nombres de PDF o correos) si el usuario los corrigió manualmente en el archivo.
        """
        if not records_to_sync:
            return
            
        csv_path = self.app.csv_path.get()
        if not csv_path or not os.path.exists(csv_path):
            return
            
        try:
            from src.core.data_manager import DataManager
            current_csv_records = DataManager.load_csv(csv_path)
            
            # Construir un mapa por clave única compuesta (cedula, id_servicio).
            # SEGURIDAD (M-04): si la clave está duplicada en el CSV, "el último gana"
            # podría reasignar el email/PDF de una fila a otra persona. Las claves
            # duplicadas se excluyen de la sincronización.
            csv_map = {}
            duplicated_keys = set()
            for r in current_csv_records:
                ced = str(r.get("cedula", "")).strip().lower()
                srv = str(r.get("id_servicio", "")).strip().lower()
                key = (ced, srv)
                if key in csv_map:
                    duplicated_keys.add(key)
                else:
                    csv_map[key] = r
            if duplicated_keys:
                logger.warning(f"Sincronización: {len(duplicated_keys)} clave(s) (cedula, id_servicio) duplicadas en el CSV; esas filas no se sincronizarán.")

            # Actualizar campos de los registros pasados en memoria
            for record in records_to_sync:
                ced = str(record.get("cedula", "")).strip().lower()
                srv = str(record.get("id_servicio", "")).strip().lower()

                if (ced, srv) in csv_map and (ced, srv) not in duplicated_keys:
                    updated_r = csv_map[(ced, srv)]
                    
                    # Si el usuario modificó datos en el CSV, los sincronizamos en caliente
                    if "id_archivo" in updated_r:
                        record["id_archivo"] = updated_r["id_archivo"]
                    if "email" in updated_r:
                        record["email"] = updated_r["email"]
                    if "cedula" in updated_r:
                        record["cedula"] = updated_r["cedula"]
                        
            logger.info("Sincronización en caliente con el archivo CSV completada con éxito.")
        except Exception as e:
            logger.error(f"No se pudo sincronizar los registros con el CSV: {str(e)}")

    def retry_batch(self, records_fallidos, email_corrections=None, pdf_corrections=None, apply_corrections=False):
        """Reintenta el envío de un lote de registros fallidos (con opción de aplicar correcciones automáticas)."""
        if not records_fallidos:
            return

        if self._workflow_active:
            self._warn_busy()
            return

        # Verificar el límite sin consumir el intento todavía: los retornos
        # tempranos (p. ej. "no hay correcciones") no deben gastar reintentos.
        if self._retry_count + 1 > self.MAX_RETRIES:
            dialogs.show_warning(
                self.app,
                "Límite Alcanzado",
                f"Se han alcanzado {self.MAX_RETRIES} reintentos máximos por seguridad.\n"
                f"Verifique manualmente los correos restantes antes de reiniciar."
            )
            return

        # Sincronizar registros fallidos con posibles correcciones en el CSV antes de reintentar
        self._sync_records_with_current_csv(records_fallidos)
        
        if apply_corrections:
            if email_corrections is None: email_corrections = {}
            if pdf_corrections is None: pdf_corrections = {}
            
            corrected_records = []
            remaining_records = []
            
            for record in records_fallidos:
                email_original = str(record.get("email", "")).strip()
                # SEGURIDAD (C-01): búsqueda por email real normalizado (la máscara colisiona)
                email_key = email_original.lower()
                id_archivo_original = str(record.get("id_archivo", "")).strip()

                corrected = dict(record)
                is_corrected = False

                if email_key in email_corrections:
                    corrected["email"] = email_corrections[email_key]
                    logger.info(f"Email corregido: {mask_email(email_original)} -> {mask_email(email_corrections[email_key])}")
                    is_corrected = True
                    
                if id_archivo_original in pdf_corrections:
                    corrected["id_archivo"] = pdf_corrections[id_archivo_original]
                    logger.info(f"PDF corregido: {mask_filename(id_archivo_original)} -> {mask_filename(pdf_corrections[id_archivo_original])}")
                    is_corrected = True
                    
                if is_corrected:
                    corrected_records.append(corrected)
                else:
                    remaining_records.append(record)
                    
            if not corrected_records:
                dialogs.show_info(self.app, "Info", "No hay correcciones para aplicar.")
                return
                
            records_to_run = corrected_records + remaining_records
        else:
            records_to_run = records_fallidos

        self._retry_count += 1
        self._workflow_active = True
        self.app.home_panel.set_busy(True)
        self.app.home_panel.progress_bar.set(0)
        self.app.home_panel.lbl_status.configure(
            text=f"Reintentando {len(records_to_run)} envios fallidos... (Intento {self._retry_count}/{self.MAX_RETRIES})"
        )
        
        self.app.show_home()
        self.execute_workflow(records_to_run)

    def show_results_modal(self, errores, total, records_fallidos, email_corrections=None, pdf_corrections=None):
        if email_corrections is None:
            email_corrections = {}
        if pdf_corrections is None:
            pdf_corrections = {}
            
        def on_retry():
            self.retry_batch(records_fallidos, email_corrections, pdf_corrections, apply_corrections=False)

        def on_correct_and_retry():
            self.retry_batch(records_fallidos, email_corrections, pdf_corrections, apply_corrections=True)

        ResultsModal(
            self.app, errores, total, records_fallidos, email_corrections,
            on_retry=on_retry, on_correct_and_retry=on_correct_and_retry,
            pdf_corrections=pdf_corrections
        )
