# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Descripción del Proyecto

SEMS Pro (Sistema de Envíos Masivos Seguros) es una aplicación de escritorio solo para Windows (GUI en CustomTkinter) que cifra PDFs con AES-256 (vía pikepdf) usando la cédula de cada destinatario como contraseña, y los envía masivamente por SMTP con STARTTLS/SSL. Los comentarios, docstrings, mensajes de commit y textos de UI están en español — mantener esa convención.

## Comandos

```bash
pip install -r requirements.txt          # instalar dependencias
python src/main.py                       # ejecutar la aplicación gráfica
python -m unittest discover tests -v     # ejecutar todos los tests
python -m unittest tests.test_pdf_crypto -v   # ejecutar un solo módulo de tests
pyinstaller Envio_Masivo_Seguro.spec     # compilar .exe de Windows (salida en dist/)
iscc installer.iss                       # generar instalador Inno Setup (tras PyInstaller)
```

Scripts de licenciamiento (solo desarrollador):
- `python generar_licencia.py` — genera una licencia Base64 firmada (las llaves Ed25519 viven fuera del repo en `%APPDATA%/SEMS_Pro/keys/`; si se rotan las llaves, actualizar `PUBLIC_KEY_HEX` en `src/core/license_manager.py`)
- `python reset_licencia.py` — elimina la licencia local del Keyring para pruebas

Windows es requerido en tiempo de ejecución: las credenciales y licencias se almacenan en el Administrador de Credenciales de Windows vía `keyring`.

## Arquitectura

El punto de entrada `src/main.py` condiciona el arranque a la validez de la licencia (`LicenseManager.is_license_active()` → `ActivationModal` si no hay licencia), y luego lanza `src/ui/app.py:App`.

Separación estricta entre UI y lógica de negocio:

- **`src/core/`** — lógica de negocio sin dependencias de Tkinter:
  - `workflow_orchestrator.py` — ejecuta el flujo completo de envío masivo (cargar CSV → cifrar PDF → enviar correo → limpieza) en un hilo secundario; la UI le pasa callbacks (`on_log`, `on_progress`, `on_stats_update`, `on_complete`, ...) de modo que core nunca toca widgets. Soporta reintentos de registros fallidos pasándolos de vuelta vía `records_to_process`.
  - `data_manager.py` — carga y validación del CSV (columnas requeridas: `email`, `id_archivo`, `id_servicio`, `cedula`).
  - `pdf_crypto.py` — cifrado AES-256 (PDF 2.0/R6) con pikepdf; owner password aleatoria, user password = prefijo opcional + cédula + sufijo opcional.
  - `email_service.py` — SMTP con validación estricta de certificados TLS; soporta SSL implícito (465) y STARTTLS.
  - `license_manager.py` — verificación de firma Ed25519 de los tokens de licencia, chequeos de expiración y retroceso de reloj en UTC (aware), activación con rate-limiting (5 intentos, bloqueo de 5 minutos).
- **`src/ui/`** — capa CustomTkinter: `app.py` (ventana principal, navegación, estado de sesión), `views/` (home, config, history), `modals/` (activation, preview, results, lote), `controllers/workflow_controller.py` (puente UI ↔ orquestador, lleva los callbacks al hilo de Tk con `app.after`, maneja el flujo de reintentos).
- **`src/config/config_manager.py`** — configuración no sensible en `config.json`; credenciales SMTP solo en Keyring (servicio `SEMS_App`), nunca en el JSON.
- **`src/utils/`** — `logger.py` (incluye `mask_email` para enmascarar PII), `email_validator.py`.

## Convenciones de seguridad (auditadas; preservar al editar)

- Nunca registrar en logs correos completos, rutas absolutas, cédulas ni contraseñas — usar `mask_email` y `os.path.basename`.
- Los secretos (credenciales SMTP, datos de licencia) viven solo en Keyring y se consultan just-in-time; no persistirlos en disco ni mantenerlos en variables de larga vida.
- El historial de envíos es solo en RAM ("zero-footprint"): `App.session_batches` con una llave HMAC por sesión; no agregar persistencia en disco.
- Defensa anti-Path Traversal: los nombres de PDF del CSV se validan contra la ruta física real del directorio de PDFs — mantener estos chequeos al tocar manejo de archivos.
- Los PDFs temporales cifrados se escriben en un directorio temporal y se eliminan tras el envío.
