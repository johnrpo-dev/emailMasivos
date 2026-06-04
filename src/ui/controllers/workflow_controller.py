# pyrefly: ignore [missing-import]
import re
import sys
import os
from tkinter import messagebox
from src.core.workflow_orchestrator import WorkflowOrchestrator
from src.ui.modals.results_modal import ResultsModal
from src.core.license_manager import LicenseManager
from src.utils.logger import logger, mask_email

class WorkflowController:
    """Controlador encargado de coordinar la ejecución del flujo de envío masivo y lógica de reintentos."""
    def __init__(self, app):
        self.app = app
        self._retry_count = 0
        self.MAX_RETRIES = 10

    def start_process(self):
        """Prepara e inicia la orquestación del proceso en segundo plano."""
        self._retry_count = 0
        if not self.app.csv_path.get() or not self.app.pdf_dir.get():
            messagebox.showwarning("Atención", "Selecciona el CSV y la carpeta de PDFs.")
            return
            
        from src.config.config_manager import ConfigManager
        config = ConfigManager.get_config()
        if not config.get("smtp_user") or not config.get("smtp_password"):
            messagebox.showwarning("Atención", "Ve a la pestaña de Configuración e ingresa tus credenciales SMTP primero.")
            return
            
        self.app.home_panel.btn_start.configure(state="disabled", fg_color="#4b5563")
        self.app.home_panel.btn_preview.configure(state="disabled", fg_color="#4b5563")
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

        def on_log(text):
            self.app.home_panel.add_console_log(text)

        def on_progress(text, progress=None):
            self.app.after(0, lambda: self.app.home_panel.update_ui_status(text, progress))

        def on_stats_update(total=None, success=None, failed=None):
            self.app.home_panel.update_monitor_stats(total=total, success=success, failed=failed)

        def on_complete(errores, total, records_fallidos, email_corrections, pdf_corrections=None):
            def _complete():
                try:
                    LicenseManager.update_last_run()
                    
                    exitosos_total = total - len(errores)
                    self.app.home_panel.update_ui_status("¡Proceso masivo completado!", 1.0)
                    self.app.home_panel.add_console_log(f"✓ COMPLETADO: {exitosos_total} exitosos, {len(errores)} fallidos.")
                    
                    if self.app.state() == "iconic":
                        self.app.show_desktop_notification(
                            "Envío Masivo Terminado",
                            f"El proceso ha finalizado. Éxitos: {exitosos_total}, Errores: {len(errores)}"
                        )
                    
                    if errores:
                        self.show_results_modal(errores, total, records_fallidos, email_corrections, pdf_corrections)
                    else:
                        messagebox.showinfo("Completado", "El proceso ha finalizado con éxito sin errores.")
                finally:
                    self.app.home_panel.btn_start.configure(state="normal", fg_color=("#10b981", "#059669"))
                    self.app.home_panel.btn_preview.configure(state="normal", fg_color=("#3b82f6", "#2563eb"))
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
            
            # Construir un mapa por clave única compuesta (cedula, id_servicio)
            csv_map = {}
            for r in current_csv_records:
                ced = str(r.get("cedula", "")).strip().lower()
                srv = str(r.get("id_servicio", "")).strip().lower()
                csv_map[(ced, srv)] = r
                
            # Actualizar campos de los registros pasados en memoria
            for record in records_to_sync:
                ced = str(record.get("cedula", "")).strip().lower()
                srv = str(record.get("id_servicio", "")).strip().lower()
                
                if (ced, srv) in csv_map:
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
            
        self._retry_count += 1
        if self._retry_count > self.MAX_RETRIES:
            messagebox.showwarning(
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
                email_masked = mask_email(email_original)
                id_archivo_original = str(record.get("id_archivo", "")).strip()
                
                corrected = dict(record)
                is_corrected = False
                
                if email_masked in email_corrections:
                    corrected["email"] = email_corrections[email_masked]
                    logger.info(f"Email corregido: {email_masked} -> {mask_email(email_corrections[email_masked])}")
                    is_corrected = True
                    
                if id_archivo_original in pdf_corrections:
                    corrected["id_archivo"] = pdf_corrections[id_archivo_original]
                    logger.info(f"PDF corregido: {id_archivo_original} -> {pdf_corrections[id_archivo_original]}")
                    is_corrected = True
                    
                if is_corrected:
                    corrected_records.append(corrected)
                else:
                    remaining_records.append(record)
                    
            if not corrected_records:
                messagebox.showinfo("Info", "No hay correcciones para aplicar.")
                return
                
            records_to_run = corrected_records + remaining_records
        else:
            records_to_run = records_fallidos
            
        self.app.home_panel.btn_start.configure(state="disabled", fg_color="#4b5563")
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
